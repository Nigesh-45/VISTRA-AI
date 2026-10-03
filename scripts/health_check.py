"""Health check self-diagnostic script for VISITR-AI deployment environment."""

import sys
import os

# Add project root directory to sys.path for standalone script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_health_check() -> bool:
    print("============================================================")
    print("           VISITR-AI PRE-DEPLOYMENT HEALTH CHECK            ")
    print("============================================================")

    all_pass = True

    # 1. Dependency Checks
    print("[1/5] Checking Python Dependencies...")
    required_mods = ["cv2", "ultralytics", "insightface", "sqlalchemy", "pydantic", "psutil"]
    for mod in required_mods:
        try:
            __import__(mod)
            print(f"  [PASS] {mod}: Available")
        except ImportError as e:
            print(f"  [FAIL] {mod}: FAILED ({e})")
            all_pass = False

    # 2. Configuration Check
    print("\n[2/5] Checking Configuration Loader...")
    try:
        from app.config.loader import load_config
        cfg = load_config("config.json")
        print(f"  [PASS] config.json: Valid (Input: {cfg.input.source}, Skip: {cfg.detection.skip_frames})")
    except Exception as e:
        print(f"  [FAIL] config.json: FAILED ({e})")
        all_pass = False

    # 3. Database Check
    print("\n[3/5] Checking Database Initialization...")
    try:
        from app.database.database import DatabaseManager
        from app.database.repository import VisitorRepository
        db = DatabaseManager("sqlite:///:memory:")
        db.init_db()
        with db.get_session() as session:
            cnt = VisitorRepository.count_unique_visitors(session)
        print(f"  [PASS] SQLite Engine & ORM: Operational (Query returned {cnt} unique visitors)")
    except Exception as e:
        print(f"  [FAIL] Database Initialization: FAILED ({e})")
        all_pass = False

    # 4. Directory Permissions Check
    print("\n[4/5] Checking Filesystem Directory Permissions...")
    req_dirs = ["data", "database", "logs/entries", "logs/exits", "output/processed", "models"]
    for d in req_dirs:
        try:
            os.makedirs(d, exist_ok=True)
            test_file = os.path.join(d, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print(f"  [PASS] Directory {d:20s}: Writable")
        except Exception as e:
            print(f"  [FAIL] Directory {d:20s}: FAILED ({e})")
            all_pass = False

    # 5. Model Setup Check
    print("\n[5/5] Checking Model Weights...")
    if os.path.exists("yolov8n.pt"):
        print("  [PASS] YOLO Weight File (yolov8n.pt): Present locally")
    else:
        print("  [INFO] YOLO Weight File (yolov8n.pt): Will auto-download on first execution")

    print("\n============================================================")
    if all_pass:
        print("           HEALTH CHECK VERDICT: 100% HEALTHY               ")
        print("============================================================")
        return True
    else:
        print("           HEALTH CHECK VERDICT: ISSUES DETECTED            ")
        print("============================================================")
        return False

if __name__ == "__main__":
    success = run_health_check()
    sys.exit(0 if success else 1)
