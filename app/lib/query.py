from typing import Type, Any, Optional, List, Dict
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
import logging

logger = logging.getLogger(__name__)


def select_with_filter(
    model: Type[DeclarativeMeta],
    filters: Optional[List[Any]] = None,
    order_by: Optional[List[Any]] = None,
    eager_opts: Optional[List[Any]] = None,
):
    try:
        with db.session() as session:
            stmt = select(model)
            if filters:
                for cond in filters:
                    stmt = stmt.where(cond)
            if eager_opts:
                stmt = stmt.options(*eager_opts)
            if order_by is not None and len(order_by) > 0:
                stmt = stmt.order_by(*order_by)
            result = session.execute(stmt).scalars().all()
            return result
    except SQLAlchemyError as e:
        logger.error(f"Database error in select_with_filter: {e}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in select_with_filter: {e}")
        db.session.rollback()
        raise
    finally:
        db.session.remove()


def select_with_filter_one(
    model: Type[DeclarativeMeta],
    filters: Optional[List[Any]] = None,
    order_by: Optional[List[Any]] = None,
    eager_opts: Optional[List[Any]] = None,
):
    try:
        with db.session() as session:
            stmt = select(model)
            if filters:
                for cond in filters:
                    stmt = stmt.where(cond)
            if eager_opts:
                stmt = stmt.options(*eager_opts)
            if order_by:
                stmt = stmt.order_by(*order_by)
            result = session.execute(stmt).scalars().first()
            return result
    except SQLAlchemyError as e:
        logger.error(f"Database error in select_with_filter_one: {e}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in select_with_filter_one: {e}")
        db.session.rollback()
        raise
    finally:
        db.session.remove()


def select_by_id(
    model: Type[DeclarativeMeta],
    pk: Any,
    eager_opts: Optional[List[Any]] = None,
):
    try:
        with db.session() as session:
            if eager_opts:
                stmt = select(model).options(*eager_opts).where(model.id == pk)
            else:
                stmt = select(model).where(model.id == pk)
            result = session.execute(stmt).scalars().first()
            return result
    except SQLAlchemyError as e:
        logger.error(f"Database error in select_by_id: {e}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in select_by_id: {e}")
        db.session.rollback()
        raise
    finally:
        db.session.remove()


def select_with_pagination(
    model: Type[DeclarativeMeta],
    page: int,
    per_page: int,
    filters: Optional[List[Any]] = None,
    order_by: Optional[List[Any]] = None,
    eager_opts: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    try:
        with db.session() as session:
            stmt = select(model)
            if filters:
                for cond in filters:
                    stmt = stmt.where(cond)
            if eager_opts:
                stmt = stmt.options(*eager_opts)
            if order_by:
                stmt = stmt.order_by(*order_by)

            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = session.execute(count_stmt).scalar_one()

            items = (
                session.execute(stmt.offset((page - 1) * per_page).limit(per_page))
                .scalars()
                .all()
            )

            total_pages = (total + per_page - 1) // per_page

            return {
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": total_pages,
                "items": items,
            }
    except SQLAlchemyError as e:
        logger.error(f"Database error in select_with_pagination: {e}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in select_with_pagination: {e}")
        db.session.rollback()
        raise
    finally:
        db.session.remove()


def update_by_id(
    model: Type[DeclarativeMeta],
    pk: Any,
    data: Dict[str, Any],
) -> Optional[Type[DeclarativeMeta]]:
    try:
        with db.session() as session:
            instance = session.get(model, pk)
            if instance:
                for key, value in data.items():
                    setattr(instance, key, value)
                session.commit()
                return instance
            return None
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_by_id: {e}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_by_id: {e}")
        db.session.rollback()
        raise
    finally:
        db.session.remove()


def update_by_filter(
    model: Type[DeclarativeMeta],
    filters: List[Any],
    data: Dict[str, Any],
) -> int:
    try:
        with db.session() as session:
            stmt = select(model)
            for cond in filters:
                stmt = stmt.where(cond)

            instances = session.execute(stmt).scalars().all()

            if not instances:
                return 0

            for instance in instances:
                for key, value in data.items():
                    setattr(instance, key, value)

            session.commit()
            return len(instances)
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_by_filter: {e}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_by_filter: {e}")
        db.session.rollback()
        raise
    finally:
        db.session.remove()


def update_multiple_by_ids(
    model: Type[DeclarativeMeta],
    ids: List[Any],
    data: Dict[str, Any],
) -> int:
    try:
        with db.session() as session:
            stmt = select(model).where(model.id.in_(ids))
            instances = session.execute(stmt).scalars().all()

            if not instances:
                return 0

            for instance in instances:
                for key, value in data.items():
                    setattr(instance, key, value)

            session.commit()
            return len(instances)
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_multiple_by_ids: {e}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_multiple_by_ids: {e}")
        db.session.rollback()
        raise
    finally:
        db.session.remove()


def delete_by_id(
    model: Type[DeclarativeMeta],
    pk: Any,
) -> bool:
    try:
        with db.session() as session:
            instance = session.get(model, pk)
            if instance:
                session.delete(instance)
                session.commit()
                return True
            return False
    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_by_id: {e}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_by_id: {e}")
        db.session.rollback()
        raise
    finally:
        db.session.remove()
