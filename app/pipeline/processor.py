"""PipelineProcessor orchestrating detection, tracking, recognition, state machine, and video annotation."""

import os
import time
from typing import Optional, Dict, Any, List, Set
import cv2
import numpy as np

from app.config.loader import AppConfig
from app.database.database import DatabaseManager
from app.database.repository import VisitorRepository
from app.detection.yolo_detector import YOLODetector
from app.events.event_logger import EventLogger
from app.events.event_manager import EventManager
from app.input.base import VideoSource
from app.input.file_source import FileVideoSource
from app.input.rtsp_source import RTSPVideoSource
from app.monitoring.metrics import PerformanceMonitor
from app.recognition.insightface_engine import InsightFaceEngine
from app.recognition.matcher import EmbeddingStore, SimilarityMatcher
from app.registration.auto_registration import AutoRegistrationEngine
from app.tracking.byte_tracker import ByteTrackerWrapper, TrackedTarget
from app.utils.image_utils import crop_face
from app.visitors.visitor_manager import VisitorManager


class PipelineProcessor:
    """End-to-end video processing pipeline for VISITR-AI."""

    def __init__(self, config: AppConfig):
        self.config = config

        # 1. Logging & Database
        self.event_logger = EventLogger(log_file_path=config.events.event_log)
        self.db_manager = DatabaseManager(db_url=config.database.url)
        self.db_manager.init_db()

        # 2. Event Manager
        self.event_manager = EventManager(
            entry_dir=config.events.entry_directory,
            exit_dir=config.events.exit_directory,
            event_logger=self.event_logger
        )

        # 3. Video Source
        if config.input.type == "rtsp":
            self.video_source: VideoSource = RTSPVideoSource(
                rtsp_url=config.input.source,
                event_logger=self.event_logger,
                reconnect_delay=config.input.rtsp_reconnect_delay,
                max_retries=config.input.rtsp_max_retries
            )
        else:
            self.video_source = FileVideoSource(file_path=config.input.source)

        # 4. Detector & Tracker
        self.detector = YOLODetector(
            model_path=config.detection.model,
            confidence=config.detection.confidence,
            iou=config.detection.iou,
            skip_frames=config.detection.skip_frames,
            event_logger=self.event_logger
        )

        self.tracker = ByteTrackerWrapper(
            max_age=config.tracking.max_age,
            track_thresh=config.tracking.track_thresh,
            event_logger=self.event_logger
        )

        # 5. Recognition & Gallery Store
        self.recognition_engine = InsightFaceEngine(
            model_name=config.recognition.model,
            event_logger=self.event_logger
        )
        self.embedding_store = EmbeddingStore()
        self.matcher = SimilarityMatcher(
            similarity_threshold=config.recognition.similarity_threshold,
            event_logger=self.event_logger
        )

        # Load existing DB embeddings into gallery store for persistent recognition across restarts
        with self.db_manager.get_session() as session:
            existing_records = VisitorRepository.get_all_embeddings(session)
            self.embedding_store.load_from_db(existing_records)
            print(f"[Pipeline] Loaded {len(existing_records)} face embeddings from database gallery.")

        # 6. Registration & Visitor State Manager
        self.registration_engine = AutoRegistrationEngine(
            recognition_engine=self.recognition_engine,
            embedding_store=self.embedding_store,
            min_face_size=config.recognition.min_face_size,
            buffer_frames=3,
            event_logger=self.event_logger
        )

        self.visitor_manager = VisitorManager(
            event_manager=self.event_manager,
            exit_timeout_frames=config.events.exit_timeout_frames,
            event_logger=self.event_logger
        )

        # 7. Metrics Instrumentation
        self.metrics = PerformanceMonitor()

        # Output Video Writer
        self.video_writer: Optional[cv2.VideoWriter] = None
        self._init_video_writer()

    def _init_video_writer(self) -> None:
        if self.config.output.save_video:
            out_path = self.config.output.path
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            fps = self.video_source.get_fps() or 30.0
            # Default resolution placeholder; initialized on first frame
            self.video_writer_path = out_path
            self.video_writer_fps = fps

    def process_stream(self, max_frames: Optional[int] = None) -> Dict[str, Any]:
        """Run main processing loop on video stream."""
        frame_idx = 0
        last_detections = []

        print("[Pipeline] Starting video processing loop...")
        try:
            while self.video_source.is_opened():
                t_frame_start = time.time()
                ret, frame, frame_num, ts = self.video_source.read_frame()
                if not ret or frame is None:
                    print("[Pipeline] Stream end or empty frame received.")
                    break

                frame_idx += 1
                if max_frames and frame_idx > max_frames:
                    print(f"[Pipeline] Reached maximum requested frames ({max_frames}). Stopping.")
                    break

                # Setup VideoWriter on first valid frame
                if self.config.output.save_video and self.video_writer is None:
                    h, w = frame.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    self.video_writer = cv2.VideoWriter(self.video_writer_path, fourcc, self.video_writer_fps, (w, h))

                # --- 1. DETECTION (with Skip Frames) ---
                t_det_start = time.time()
                skip = self.config.detection.skip_frames
                if skip == 0 or (frame_idx % (skip + 1) == 1) or not last_detections:
                    detections = self.detector.detect(frame, frame_num, ts)
                    last_detections = detections
                else:
                    detections = last_detections
                t_det_ms = (time.time() - t_det_start) * 1000.0

                # --- 2. TRACKING ---
                t_track_start = time.time()
                tracked_targets: List[TrackedTarget] = self.tracker.update(detections, frame_num, ts)
                t_track_ms = (time.time() - t_track_start) * 1000.0

                # --- 3. RECOGNITION, REGISTRATION & STATE MACHINE ---
                t_rec_start = time.time()
                visible_track_ids: Set[int] = set()

                with self.db_manager.get_session() as session:
                    for target in tracked_targets:
                        visible_track_ids.add(target.track_id)
                        crop = crop_face(frame, target.bbox)

                        # Extract embedding if crop is valid
                        emb = self.recognition_engine.extract_embedding(crop) if crop is not None else None
                        match_res = self.matcher.match(emb, self.embedding_store) if emb is not None else None

                        if match_res and match_res.matched and match_res.face_id:
                            # KNOWN VISITOR
                            self.visitor_manager.process_recognized_track(
                                db_session=session,
                                track_id=target.track_id,
                                face_id=match_res.face_id,
                                bbox=target.bbox,
                                face_crop=crop,
                                confidence=match_res.similarity,
                                frame_number=frame_num
                            )
                        else:
                            # UNKNOWN FACE -> Buffer Candidate for Auto-Registration
                            if crop is not None:
                                self.registration_engine.add_candidate(
                                    track_id=target.track_id,
                                    frame=frame,
                                    bbox=target.bbox,
                                    confidence=target.confidence,
                                    frame_number=frame_num,
                                    timestamp=ts
                                )

                                if self.registration_engine.is_ready_to_register(target.track_id):
                                    new_face_id, best_crop, _ = self.registration_engine.register_new_visitor(session, target.track_id)
                                    if new_face_id:
                                        target_crop = best_crop if (best_crop is not None and best_crop.size > 0) else crop
                                        self.visitor_manager.process_recognized_track(
                                            db_session=session,
                                            track_id=target.track_id,
                                            face_id=new_face_id,
                                            bbox=target.bbox,
                                            face_crop=target_crop,
                                            confidence=target.confidence,
                                            frame_number=frame_num
                                        )

                    # Update missing tracks for exit timeouts
                    self.visitor_manager.update_missing_tracks(session, visible_track_ids, frame_num)

                t_rec_ms = (time.time() - t_rec_start) * 1000.0
                t_total_ms = (time.time() - t_frame_start) * 1000.0

                self.metrics.update_frame(t_det_ms, t_track_ms, t_rec_ms, t_total_ms)

                # --- 4. OVERLAY ANNOTATION & RENDERING ---
                annotated_frame = self._render_overlays(frame, tracked_targets)

                if self.video_writer is not None:
                    self.video_writer.write(annotated_frame)

        except Exception as e:
            print(f"[Pipeline] Exception during stream processing: {e}")
            if self.event_logger:
                self.event_logger.log_event("APPLICATION_ERROR", level="ERROR", metadata={"error": str(e)})
        finally:
            self._shutdown(frame_idx)

        # Return final measured metrics summary
        with self.db_manager.get_session() as session:
            unique_count = VisitorRepository.count_unique_visitors(session)

        res_usage = self.metrics.get_resource_usage()
        avg_lat = self.metrics.get_average_latencies()

        return {
            "unique_visitors": unique_count,
            "total_frames_processed": frame_idx,
            "processing_fps": res_usage["processing_fps"],
            "cpu_percent": res_usage["cpu_percent"],
            "ram_mb": res_usage["ram_mb"],
            "gpu_info": res_usage["gpu_info"],
            "average_latencies_ms": avg_lat
        }

    def _render_overlays(self, frame: np.ndarray, tracked_targets: List[TrackedTarget]) -> np.ndarray:
        """Draw readable bounding boxes and header status metrics on frame."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # Draw Target BBoxes & Labels
        for target in tracked_targets:
            x1, y1, x2, y2 = target.bbox
            track_state = self.visitor_manager.active_tracks.get(target.track_id)

            if track_state and track_state.face_id:
                face_id_str = track_state.face_id
                status_str = track_state.status.value
                color = (0, 255, 0) if status_str == "INSIDE" else (0, 200, 255)
            else:
                face_id_str = "UNKNOWN"
                status_str = "REGISTERING"
                color = (0, 165, 255)

            # Box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Label text: VIS-00001 | Track 18 | 0.91 | INSIDE
            label = f"{face_id_str} | Trk {target.track_id} | {target.confidence:.2f} | {status_str}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

            # Label background box
            cv2.rectangle(annotated, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, max(th + 6, y1)), color, -1)
            cv2.putText(annotated, label, (x1 + 3, max(th, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

        # Header HUD Banner
        hud_bg = np.zeros((40, w, 3), dtype=np.uint8)
        cv2.rectangle(hud_bg, (0, 0), (w, 40), (20, 20, 20), -1)
        annotated = cv2.addWeighted(annotated, 1.0, cv2.add(np.zeros_like(annotated), 0), 0.0, 0)
        annotated[0:40, 0:w] = hud_bg

        fps_val = self.metrics.current_fps
        active_count = len([t for t in self.visitor_manager.active_tracks.values() if t.status.value == "INSIDE"])

        hud_text = f"VISITR-AI | FPS: {fps_val:.1f} | Active Inside: {active_count} | Targets: {len(tracked_targets)}"
        cv2.putText(annotated, hud_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        return annotated

    def _shutdown(self, last_frame_num: int) -> None:
        """Clean shutdown releasing resources and flushing remaining exit events."""
        print("[Pipeline] Flushing active visitor exit events...")
        try:
            with self.db_manager.get_session() as session:
                self.visitor_manager.force_flush_exits(session, last_frame_num)
        except Exception as e:
            print(f"[Pipeline] Error during exit flush: {e}")

        if self.video_writer is not None:
            self.video_writer.release()

        self.video_source.release()
        print("[Pipeline] Shutdown complete.")
