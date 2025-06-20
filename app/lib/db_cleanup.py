"""
Database connection cleanup utilities
"""

import logging
from app.extensions import db

logger = logging.getLogger(__name__)


def force_cleanup_db_session():
    """
    Force cleanup database session and connections
    Sử dụng khi db.session.remove() không đủ mạnh
    """
    try:
        # Step 1: Rollback any pending transactions
        if db.session.is_active:
            db.session.rollback()

        # Step 2: Close session
        db.session.close()

        # Step 3: Remove session from registry
        db.session.remove()

        # Step 4: Force dispose engine connections (drastic measure)
        # Chỉ dùng khi cần thiết vì nó đóng TẤT CẢ connections
        # db.engine.dispose()

    except Exception as e:
        logger.error(f"Error in force_cleanup_db_session: {e}")
        try:
            # Last resort: force remove
            db.session.remove()
        except:
            pass


def cleanup_db_session_safe():
    """
    Safe cleanup - dùng cho hầu hết trường hợp
    """
    try:
        # Commit any pending changes
        if db.session.dirty or db.session.new or db.session.deleted:
            db.session.commit()
    except Exception as e:
        logger.error(f"Error committing session: {e}")
        try:
            db.session.rollback()
        except:
            pass
    finally:
        try:
            db.session.remove()
        except Exception as e:
            logger.error(f"Error removing session: {e}")


def cleanup_db_session_aggressive():
    """
    Aggressive cleanup - dùng khi có connection leaks nghiêm trọng
    """
    try:
        # Force rollback
        db.session.rollback()

        # Close all connections in session
        db.session.close()

        # Remove from registry
        db.session.remove()

        # Get connection pool and force return connections
        engine = db.get_engine()
        if hasattr(engine.pool, "_return_conn"):
            # Force return all checked out connections
            pool = engine.pool
            if hasattr(pool, "_checked_out"):
                checked_out = list(pool._checked_out)
                for conn in checked_out:
                    try:
                        pool._return_conn(conn)
                    except:
                        pass

    except Exception as e:
        logger.error(f"Error in aggressive cleanup: {e}")
        try:
            db.session.remove()
        except:
            pass
