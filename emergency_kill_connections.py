#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emergency Kill Sleep Connections - Giải pháp khẩn cấp
Chạy: python emergency_kill_connections.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from app import create_app
from app.config import configs as config
from app.extensions import db
from sqlalchemy import text


def emergency_kill_sleep_connections(min_time_seconds=30):
    """Emergency kill tất cả sleep connections > X giây"""
    try:
        print(
            f"🚨 EMERGENCY: Killing all toktak sleep connections > {min_time_seconds}s"
        )

        # Get all sleep connections
        result = db.session.execute(text("SHOW FULL PROCESSLIST")).fetchall()
        killed_count = 0
        total_sleep = 0

        for row in result:
            if len(row) >= 5:
                connection_id = row[0]
                user = row[1]
                command = row[4]
                time_sec = row[5]

                if command == "Sleep" and user == "toktak":
                    total_sleep += 1
                    if time_sec >= min_time_seconds:
                        try:
                            db.session.execute(text(f"KILL {connection_id}"))
                            print(
                                f"🔪 Killed connection ID {connection_id} (Sleep {time_sec}s)"
                            )
                            killed_count += 1
                        except Exception as e:
                            print(f"❌ Failed to kill connection {connection_id}: {e}")

        print(f"\n📊 Results:")
        print(f"  Total Sleep Connections: {total_sleep}")
        print(f"  Killed Connections: {killed_count}")
        print(f"  Remaining Sleep: {total_sleep - killed_count}")

        return killed_count

    except Exception as e:
        print(f"💥 Emergency kill failed: {e}")
        return 0
    finally:
        try:
            db.session.remove()
        except:
            pass


def show_connection_status():
    """Hiển thị trạng thái connections"""
    try:
        result = db.session.execute(text("SHOW FULL PROCESSLIST")).fetchall()

        total_connections = len(result)
        sleep_connections = []
        active_connections = []

        for row in result:
            if len(row) >= 5:
                if row[4] == "Sleep":
                    sleep_connections.append(
                        {"id": row[0], "user": row[1], "time": row[5]}
                    )
                else:
                    active_connections.append(
                        {"id": row[0], "user": row[1], "command": row[4]}
                    )

        print(f"\n🔍 Connection Status - {datetime.now().strftime('%H:%M:%S')}")
        print(f"📊 Total: {total_connections}")
        print(f"😴 Sleep: {len(sleep_connections)}")
        print(f"⚡ Active: {len(active_connections)}")

        if sleep_connections:
            toktak_sleep = [c for c in sleep_connections if c["user"] == "toktak"]
            print(f"👤 Toktak Sleep: {len(toktak_sleep)}")

            # Group by time ranges
            time_groups = {"<30s": 0, "30-60s": 0, "1-2min": 0, ">2min": 0}
            very_long = []

            for conn in toktak_sleep:
                time_sec = conn["time"]
                if time_sec < 30:
                    time_groups["<30s"] += 1
                elif time_sec < 60:
                    time_groups["30-60s"] += 1
                elif time_sec < 120:
                    time_groups["1-2min"] += 1
                else:
                    time_groups[">2min"] += 1
                    if time_sec > 120:
                        very_long.append(f"ID:{conn['id']}({time_sec}s)")

            print(f"⏱️  Time breakdown: {time_groups}")
            if very_long:
                print(f"🚨 Very long (>2min): {', '.join(very_long[:5])}")
                if len(very_long) > 5:
                    print(f"    ... and {len(very_long) - 5} more")

    except Exception as e:
        print(f"Error showing status: {e}")
    finally:
        try:
            db.session.remove()
        except:
            pass


if __name__ == "__main__":
    # Create Flask app
    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]
    app = create_app(config_app)

    with app.app_context():
        print("=" * 60)
        print("🚨 EMERGENCY MYSQL CONNECTION KILLER")
        print("=" * 60)

        # Show current status first
        show_connection_status()

        if len(sys.argv) > 1:
            if sys.argv[1] == "--kill-all":
                # Kill ALL sleep connections > 10s
                print(f"\n⚠️  WARNING: Killing ALL sleep connections > 10s")
                input("Press Enter to continue or Ctrl+C to abort...")
                killed = emergency_kill_sleep_connections(10)

            elif sys.argv[1] == "--kill-long":
                # Kill connections > 60s
                print(f"\n🔪 Killing long sleep connections > 60s")
                killed = emergency_kill_sleep_connections(60)

            elif sys.argv[1] == "--kill-very-long":
                # Kill connections > 120s
                print(f"\n🔪 Killing very long sleep connections > 120s")
                killed = emergency_kill_sleep_connections(120)

            else:
                print(f"\nUsage:")
                print(f"  python {sys.argv[0]} --status           # Show status only")
                print(
                    f"  python {sys.argv[0]} --kill-very-long   # Kill >120s connections"
                )
                print(
                    f"  python {sys.argv[0]} --kill-long        # Kill >60s connections"
                )
                print(
                    f"  python {sys.argv[0]} --kill-all         # Kill >10s connections (DANGEROUS)"
                )

        else:
            # Interactive mode
            print(f"\nOptions:")
            print(f"1. Kill connections > 120s (recommended)")
            print(f"2. Kill connections > 60s")
            print(f"3. Kill connections > 30s (careful!)")
            print(f"4. Show status again")
            print(f"5. Exit")

            try:
                choice = input("\nEnter choice (1-5): ").strip()

                if choice == "1":
                    killed = emergency_kill_sleep_connections(120)
                elif choice == "2":
                    killed = emergency_kill_sleep_connections(60)
                elif choice == "3":
                    print("⚠️  WARNING: This will kill connections > 30s")
                    confirm = input("Type 'YES' to confirm: ")
                    if confirm == "YES":
                        killed = emergency_kill_sleep_connections(30)
                    else:
                        print("Cancelled.")
                elif choice == "4":
                    show_connection_status()
                elif choice == "5":
                    print("👋 Goodbye!")
                else:
                    print("Invalid choice")

            except KeyboardInterrupt:
                print("\n👋 Cancelled by user")

        # Show final status
        print(f"\n" + "=" * 40)
        show_connection_status()
        print("=" * 60)
