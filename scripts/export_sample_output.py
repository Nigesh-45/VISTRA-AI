"""Export actual execution outputs into sample_output/ directory."""

import json
import os
import shutil
import sqlite3


def export_sample_output(
    db_path: str = "database/visitors.db",
    log_path: str = "logs/events.log",
    entries_dir: str = "logs/entries",
    exits_dir: str = "logs/exits",
    output_dir: str = "sample_output"
):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "entries"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "exits"), exist_ok=True)

    # 1. Copy Log File
    if os.path.exists(log_path):
        shutil.copy2(log_path, os.path.join(output_dir, "events.log"))

    # 2. Copy Cropped Images
    if os.path.exists(entries_dir):
        for root, dirs, files in os.walk(entries_dir):
            for f in files:
                if f.endswith(".jpg"):
                    shutil.copy2(os.path.join(root, f), os.path.join(output_dir, "entries", f))

    if os.path.exists(exits_dir):
        for root, dirs, files in os.walk(exits_dir):
            for f in files:
                if f.endswith(".jpg"):
                    shutil.copy2(os.path.join(root, f), os.path.join(output_dir, "exits", f))

    # 3. Export Database SQL Snapshot
    sql_snapshot_path = os.path.join(output_dir, "database_snapshot.sql")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        with open(sql_snapshot_path, "w", encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
        conn.close()

    # 4. Generate Summary JSON from actual DB metrics
    summary_path = os.path.join(output_dir, "summary.json")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM visitors")
        unique_cnt = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM events WHERE event_type = 'ENTRY'")
        entries_cnt = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM events WHERE event_type = 'EXIT'")
        exits_cnt = c.fetchone()[0]

        c.execute("SELECT SUM(total_visits - 1) FROM visitors")
        reident_cnt = c.fetchone()[0] or 0

        conn.close()

        summary_data = {
            "unique_visitors": unique_cnt,
            "total_entries": entries_cnt,
            "total_exits": exits_cnt,
            "re_identifications": reident_cnt,
            "sample_execution": True
        }

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        print(f"[Export] Exported sample outputs to {output_dir}/")
        print(f"  Summary: {summary_data}")


if __name__ == "__main__":
    export_sample_output()
