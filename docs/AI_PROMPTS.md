# AI Prompts & Development Logs - VISITR-AI

This document preserves the key prompts, instructions, and engineering directives utilized during the development of VISITR-AI.

## Initial System Directive

```
You are the lead engineer responsible for building my final submission for the Katomaran Hackathon.

PROJECT: VISITR-AI
Intelligent Face Tracking, Auto-Registration & Unique Visitor Analytics

MISSION: Build a technically excellent, production-style, modular, reliable and interview-defensible computer vision application that satisfies EVERY requirement in the provided Katomaran problem statement.

CRITICAL IDENTITY ARCHITECTURE:
NEVER confuse TRACK ID with FACE ID.
TRACK ID is temporary (ByteTrack).
FACE ID is persistent (VIS-XXXXX).
A visitor may have track_id = 17 and later track_id = 31 while remaining face_id = VIS-00017.
This is fundamental to re-identification.
```

## Architectural Engineering Directives

- **Directive 1 (Prohibited Libraries)**: DO NOT use the Python `face_recognition` library. Use InsightFace / ArcFace for 512-d feature embeddings.
- **Directive 2 (State Machine & Events)**: Enforce exactly-once `ENTRY` and `EXIT` events per visit cycle using explicit state guards (`OUTSIDE`, `INSIDE`).
- **Directive 3 (Persistence Integrity)**: Implement atomic file writes (`cv2.imencode` -> temp file -> atomic rename -> DB transaction -> log commit).
- **Directive 4 (Testing & Verification)**: IMPLEMENT -> RUN -> TEST -> INSPECT -> FIX -> RE-RUN.
