#!/usr/bin/env python3
"""
Script để kiểm tra trạng thái connection pool chi tiết
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.config import configs as config
from sqlalchemy import text


def check_pool_status():
    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]
    app = create_app(config_app)

    with app.app_context():
        try:
            engine = db.get_engine()
            pool = engine.pool

            print("🔍 CONNECTION POOL STATUS:")
            print(f"📊 Pool Size: {pool.size()}")
            print(f"📈 Pool Checked Out: {pool.checkedout()}")
            print(f"📉 Pool Checked In: {pool.checkedin()}")
            print(f"🔄 Pool Overflow: {pool.overflow()}")

            # Kiểm tra MySQL processlist
            result = db.session.execute(text("SHOW FULL PROCESSLIST")).fetchall()

            sleep_connections = []
            for row in result:
                if len(row) >= 5 and row[4] == "Sleep":
                    sleep_connections.append(
                        {"id": row[0], "user": row[1], "host": row[2], "time": row[5]}
                    )

            print(f"\n😴 SLEEP CONNECTIONS: {len(sleep_connections)}")

            # Phân loại theo thời gian
            time_groups = {"<10s": 0, "10-60s": 0, "60-300s": 0, ">300s": 0}

            for conn in sleep_connections:
                time_sec = conn["time"]
                if time_sec < 10:
                    time_groups["<10s"] += 1
                elif time_sec < 60:
                    time_groups["10-60s"] += 1
                elif time_sec < 300:
                    time_groups["60-300s"] += 1
                else:
                    time_groups[">300s"] += 1

            print("⏱️  Time Distribution:")
            for time_range, count in time_groups.items():
                print(f"   {time_range}: {count}")

            # Long running connections
            long_connections = [
                conn for conn in sleep_connections if conn["time"] > 120
            ]
            if long_connections:
                print(f"\n🚨 LONG CONNECTIONS (>2min): {len(long_connections)}")
                for conn in long_connections[:10]:  # Show first 10
                    print(
                        f"   ID:{conn['id']} | {conn['user']} | {conn['time']}s | {conn['host']}"
                    )

            # Connection pool efficiency
            total_capacity = pool.size() + pool.overflow()
            usage_percent = (
                (pool.checkedout() / total_capacity * 100) if total_capacity > 0 else 0
            )

            print(f"\n📈 POOL EFFICIENCY:")
            print(f"   Capacity: {total_capacity}")
            print(f"   Used: {pool.checkedout()} ({usage_percent:.1f}%)")
            print(f"   Available: {pool.checkedin()}")

            # Health check
            if len(sleep_connections) > 50:
                print("\n❌ HEALTH: CRITICAL - Too many sleep connections")
            elif len(sleep_connections) > 20:
                print("\n⚠️  HEALTH: WARNING - High sleep connections")
            else:
                print("\n✅ HEALTH: GOOD - Normal connection count")

        except Exception as e:
            print(f"❌ Error checking pool status: {e}")
        finally:
            try:
                db.session.remove()
            except:
                pass


if __name__ == "__main__":
    check_pool_status()
