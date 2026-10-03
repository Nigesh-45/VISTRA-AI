"""Script generating synthetic sample video data/sample_video.mp4 with realistic face features and motion paths."""

import os
import cv2
import numpy as np


def draw_synthetic_face(img, center, radius=40, skin_color=(180, 210, 240), face_id_seed=1):
    """Draw a realistic synthetic face with distinct features based on seed."""
    cx, cy = center
    # Face outline
    cv2.circle(img, (cx, cy), radius, skin_color, -1)
    cv2.circle(img, (cx, cy), radius, (50, 50, 50), 2)

    # Hair / Top feature
    hair_color = (40, 40, 40) if face_id_seed == 1 else (20, 80, 140)
    cv2.ellipse(img, (cx, cy - 10), (radius, int(radius * 0.6)), 0, 180, 360, hair_color, -1)

    # Eyes
    eye_offset = int(radius * 0.35)
    eye_y = cy - int(radius * 0.15)
    cv2.circle(img, (cx - eye_offset, eye_y), 6, (255, 255, 255), -1)
    cv2.circle(img, (cx + eye_offset, eye_y), 6, (255, 255, 255), -1)
    cv2.circle(img, (cx - eye_offset, eye_y), 3, (0, 0, 0), -1)
    cv2.circle(img, (cx + eye_offset, eye_y), 3, (0, 0, 0), -1)

    # Nose
    cv2.line(img, (cx, cy - 5), (cx - 3, cy + 10), (100, 120, 140), 2)

    # Mouth
    cv2.ellipse(img, (cx, cy + int(radius * 0.4)), (12, 6), 0, 0, 180, (50, 50, 180), 2)


def generate_sample_video(output_path="data/sample_video.mp4", width=640, height=480, fps=30, total_seconds=12):
    """Generate realistic synthetic sample video with entry, exit, and re-entry sequences."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, float(fps), (width, height))

    total_frames = fps * total_seconds

    print(f"[SampleGen] Generating {total_frames} frames into {output_path}...")

    for frame_idx in range(total_frames):
        # Dark clean background
        frame = np.full((height, width, 3), (35, 30, 30), dtype=np.uint8)

        # Draw grid lines for visual structure
        for y in range(0, height, 40):
            cv2.line(frame, (0, y), (width, y), (45, 40, 40), 1)
        for x in range(0, width, 40):
            cv2.line(frame, (x, 0), (x, height), (45, 40, 40), 1)

        # --- PERSON 1 (FACE SEED 1) SCENARIO ---
        # Frames 0 to 120 (0 to 4s): Person 1 Enters from Left -> Stops in Center -> Moves Right Out of Frame (EXITS)
        if 0 <= frame_idx <= 120:
            if frame_idx < 40:
                p1_x = int(50 + (frame_idx / 40.0) * 250)
            elif frame_idx < 80:
                p1_x = 300
            else:
                p1_x = int(300 + ((frame_idx - 80) / 40.0) * 400)  # Exits right

            if p1_x < width + 50:
                draw_synthetic_face(frame, (p1_x, 220), radius=45, skin_color=(175, 205, 235), face_id_seed=1)

        # --- PERSON 2 (FACE SEED 2) SCENARIO ---
        # Frames 60 to 180 (2s to 6s): Person 2 Enters from Top -> Crosses Bottom Out of Frame
        if 60 <= frame_idx <= 180:
            rel_f = frame_idx - 60
            p2_y = int(50 + (rel_f / 120.0) * 400)
            if p2_y < height + 50:
                draw_synthetic_face(frame, (480, p2_y), radius=45, skin_color=(190, 220, 210), face_id_seed=2)

        # --- PERSON 1 RE-ENTRY SCENARIO ---
        # Frames 210 to 330 (7s to 11s): Person 1 Re-enters from Left -> Same Face Seed 1 (RE-IDENTIFICATION)!
        if 210 <= frame_idx <= 330:
            rel_f = frame_idx - 210
            p1_re_x = int(50 + (rel_f / 120.0) * 400)
            draw_synthetic_face(frame, (p1_re_x, 240), radius=45, skin_color=(175, 205, 235), face_id_seed=1)

        # Frame overlay watermark
        cv2.putText(frame, f"Katomaran Benchmark Sample Video | Frame {frame_idx+1}/{total_frames}", (15, height - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

        out.write(frame)

    out.release()
    print(f"[SampleGen] Successfully created sample video: {output_path} ({os.path.getsize(output_path)} bytes)")


if __name__ == "__main__":
    generate_sample_video()
