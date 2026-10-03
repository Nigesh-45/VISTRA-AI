"""VISITR-AI Main CLI Application Entry Point."""

import argparse
import sys
from app.config.loader import load_config
from app.pipeline.processor import PipelineProcessor


import signal

def main():
    parser = argparse.ArgumentParser(description="VISITR-AI: Intelligent Face Tracking, Auto-Registration & Unique Visitor Analytics")
    parser.add_argument("--config", type=str, default="config.json", help="Path to configuration JSON file")
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum number of frames to process")
    parser.add_argument("--rtsp", type=str, default=None, help="Override input source with RTSP URL")

    args = parser.parse_args()

    print("============================================================")
    print("                 VISITR-AI ENGINE START                     ")
    print("============================================================")

    config = load_config(args.config)

    if args.rtsp:
        config.input.type = "rtsp"
        config.input.source = args.rtsp

    print(f"[Main] Configuration loaded from: {args.config}")
    print(f"[Main] Input Source: {config.input.source} (type: {config.input.type})")
    print(f"[Main] Detection Skip Frames: {config.detection.skip_frames}")

    processor = PipelineProcessor(config)

    # Register signal handlers for clean interrupt recovery
    def handle_signal(sig, frame):
        print(f"\n[Main] Signal {sig} received. Initiating graceful shutdown...")
        processor._shutdown(processor.metrics.frame_count)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    summary = processor.process_stream(max_frames=args.max_frames)

    print("\n============================================================")
    print("                 EXECUTION SUMMARY RESULTS                  ")
    print("============================================================")
    print(f"  Unique Visitors Counted : {summary['unique_visitors']}")
    print(f"  Total Frames Processed  : {summary['total_frames_processed']}")
    print(f"  Processing Speed (FPS)  : {summary['processing_fps']:.1f}")
    print(f"  CPU Usage               : {summary['cpu_percent']:.1f}%")
    print(f"  RAM Usage               : {summary['ram_mb']:.1f} MB")
    print(f"  GPU Hardware            : {summary['gpu_info']}")
    print("  Average Component Latencies:")
    for k, v in summary['average_latencies_ms'].items():
        print(f"    - {k:12s}: {v:.2f} ms")
    print("============================================================")


if __name__ == "__main__":
    main()
