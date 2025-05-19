from typing import Type, Any, Optional, List, Tuple, Dict
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeMeta
from app.extensions import db


def select_with_filter(
    model: Type[DeclarativeMeta],
    filters: Optional[List[Any]] = None,
    order_by: Optional[List[Any]] = None,
):
    stmt = select(model)
    if filters:
        for cond in filters:
            stmt = stmt.where(cond)
    if order_by:
        stmt = stmt.order_by(*order_by)
    result = db.session.execute(stmt).scalars().all()
    return result


def select_with_filter_one(
    model: Type[DeclarativeMeta],
    filters: Optional[List[Any]] = None,
    order_by: Optional[List[Any]] = None,
):
    stmt = select(model)
    if filters:
        for cond in filters:
            stmt = stmt.where(cond)
    if order_by:
        stmt = stmt.order_by(*order_by)
    result = db.session.execute(stmt).scalars().first()
    return result


def select_by_id(
    model: Type[DeclarativeMeta],
    pk: Any,
):
    return db.session.get(model, pk)


def select_with_pagination(
    model: Type[DeclarativeMeta],
    page: int,
    per_page: int,
    filters: Optional[List[Any]] = None,
    order_by: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    stmt = select(model)
    if filters:
        for cond in filters:
            stmt = stmt.where(cond)
    if order_by:
        stmt = stmt.order_by(*order_by)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.session.execute(count_stmt).scalar_one()

    items = (
        db.session.execute(stmt.offset((page - 1) * per_page).limit(per_page))
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


def update_by_id(
    model: Type[DeclarativeMeta],
    pk: Any,
    data: Dict[str, Any],
) -> Optional[Type[DeclarativeMeta]]:
    instance = db.session.get(model, pk)
    if instance:
        for key, value in data.items():
            setattr(instance, key, value)
        db.session.commit()
        return instance
    return None
