#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL Connection Monitor - Theo dõi và cảnh báo Sleep connections
Chạy: python monitor_connections.py
"""

import os
import sys
import time
import threading
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from app import create_app
from app.config import configs as config
from app.extensions import db
from app.lib.logger import logger
from sqlalchemy import text

# Configuration
ALERT_THRESHOLD = 50  # Alert when > 50 sleep connections
CHECK_INTERVAL = 30  # Check every 30 seconds
KILL_THRESHOLD = 120  # Kill connections > 2 minutes


def get_sleep_connections():
    """Lấy danh sách Sleep connections"""
    try:
        result = db.session.execute(text("SHOW FULL PROCESSLIST")).fetchall()
        sleep_connections = []

        for row in result:
            if len(row) >= 5 and row[4] == "Sleep":
                connection_info = {
                    "id": row[0],
                    "user": row[1],
                    "host": row[2],
                    "db": row[3],
                    "command": row[4],
                    "time": row[5],  # Time in seconds
                    "state": row[6] if len(row) > 6 else "",
                    "info": row[7] if len(row) > 7 else "",
                }
                sleep_connections.append(connection_info)

        return sleep_connections
    except Exception as e:
        logger.error(f"Error getting sleep connections: {e}")
        return []


def get_connection_stats():
    """Lấy thống kê connection"""
    try:
        # Current connections
        current_result = db.session.execute(
            text("SHOW STATUS LIKE 'Threads_connected'")
        ).fetchone()
        current_connections = int(current_result[1]) if current_result else 0

        # Max connections
        max_result = db.session.execute(
            text("SHOW VARIABLES LIKE 'max_connections'")
        ).fetchone()
        max_connections = int(max_result[1]) if max_result else 0

        # Connection usage percentage
        usage_percent = (
            (current_connections / max_connections * 100) if max_connections > 0 else 0
        )

        return {
            "current": current_connections,
            "max": max_connections,
            "usage_percent": usage_percent,
        }
    except Exception as e:
        logger.error(f"Error getting connection stats: {e}")
        return {"current": 0, "max": 0, "usage_percent": 0}


def kill_long_running_connections(threshold_seconds=KILL_THRESHOLD):
    """Kill các connection Sleep quá lâu"""
    try:
        sleep_connections = get_sleep_connections()
        killed_count = 0

        for conn in sleep_connections:
            if conn["time"] > threshold_seconds and conn["user"] == "toktak":
                try:
                    db.session.execute(text(f"KILL {conn['id']}"))
                    logger.warning(
                        f"🔪 Killed connection ID {conn['id']} (Sleep {conn['time']}s)"
                    )
                    killed_count += 1
                except Exception as e:
                    logger.error(f"Failed to kill connection {conn['id']}: {e}")

        if killed_count > 0:
            logger.info(f"🔪 Killed {killed_count} long-running connections")

        return killed_count
    except Exception as e:
        logger.error(f"Error killing connections: {e}")
        return 0


def monitor_connections():
    """Main monitoring function"""
    logger.info("🔍 Starting MySQL Connection Monitor...")
    last_alert_time = 0
    alert_cooldown = 300  # 5 minutes between alerts

    while True:
        try:
            sleep_connections = get_sleep_connections()
            stats = get_connection_stats()

            sleep_count = len(sleep_connections)
            current_time = time.time()

            # Log current status
            logger.info(
                f"📊 Connections: {stats['current']}/{stats['max']} "
                f"({stats['usage_percent']:.1f}%), Sleep: {sleep_count}"
            )

            # Detailed sleep analysis
            if sleep_count > 0:
                time_groups = {"<10s": 0, "10-30s": 0, "30-60s": 0, ">60s": 0}
                long_connections = []

                for conn in sleep_connections:
                    time_sec = conn["time"]
                    if time_sec < 10:
                        time_groups["<10s"] += 1
                    elif time_sec < 30:
                        time_groups["10-30s"] += 1
                    elif time_sec < 60:
                        time_groups["30-60s"] += 1
                    else:
                        time_groups[">60s"] += 1
                        if time_sec > 60:
                            long_connections.append(f"ID:{conn['id']}({time_sec}s)")

                logger.info(f"⏱️  Sleep breakdown: {time_groups}")
                if long_connections:
                    logger.warning(
                        f"🚨 Long connections: {', '.join(long_connections)}"
                    )

            # Alert on high sleep connections
            if sleep_count > ALERT_THRESHOLD:
                if current_time - last_alert_time > alert_cooldown:
                    alert_msg = (
                        f"🚨 HIGH SLEEP CONNECTIONS ALERT!\n"
                        f"Sleep Connections: {sleep_count}\n"
                        f"Total: {stats['current']}/{stats['max']} "
                        f"({stats['usage_percent']:.1f}%)\n"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )

                    logger.warning(alert_msg)
                    last_alert_time = current_time

            # Auto-kill very long connections
            if sleep_count > 100:  # Only if too many connections
                killed = kill_long_running_connections(KILL_THRESHOLD)
                if killed > 0:
                    logger.info(
                        f"🔪 Auto-killed {killed} connections to prevent overload"
                    )

            # Connection usage warning
            if stats["usage_percent"] > 80:
                logger.warning(
                    f"⚠️  High connection usage: {stats['usage_percent']:.1f}%"
                )

        except Exception as e:
            logger.error(f"Monitor error: {e}")

        finally:
            # Always cleanup session
            try:
                db.session.remove()
            except:
                pass

        time.sleep(CHECK_INTERVAL)


def print_current_status():
    """In trạng thái hiện tại một lần"""
    try:
        sleep_connections = get_sleep_connections()
        stats = get_connection_stats()

        print(
            f"\n🔍 MySQL Connection Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(
            f"📊 Total Connections: {stats['current']}/{stats['max']} ({stats['usage_percent']:.1f}%)"
        )
        print(f"😴 Sleep Connections: {len(sleep_connections)}")

        if sleep_connections:
            print(f"\n📋 Sleep Connection Details:")
            for i, conn in enumerate(sleep_connections[:10]):  # Show first 10
                print(
                    f"  {i+1:2d}. ID:{conn['id']:3d} | {conn['user']:<10} | {conn['time']:3d}s | {conn['host']}"
                )

            if len(sleep_connections) > 10:
                print(f"  ... and {len(sleep_connections) - 10} more")

        print("")

    except Exception as e:
        print(f"Error: {e}")
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
        if len(sys.argv) > 1 and sys.argv[1] == "--status":
            # Chỉ in trạng thái hiện tại
            print_current_status()
        elif len(sys.argv) > 1 and sys.argv[1] == "--kill":
            # Kill long-running connections
            print("🔪 Killing long-running connections...")
            killed = kill_long_running_connections(60)  # Kill > 60s
            print(f"🔪 Killed {killed} connections")
        else:
            # Chạy monitor liên tục
            try:
                monitor_connections()
            except KeyboardInterrupt:
                logger.info("🛑 Monitor stopped by user")
            except Exception as e:
                logger.error(f"Monitor crashed: {e}")
