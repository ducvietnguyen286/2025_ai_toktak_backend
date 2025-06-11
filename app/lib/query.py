from typing import Type, Any, Optional, List, Tuple, Dict
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeMeta
from app.extensions import db


def select_with_filter(
    model: Type[DeclarativeMeta],
    filters: Optional[List[Any]] = None,
    order_by: Optional[List[Any]] = None,
    eager_opts: Optional[List[Any]] = None,
):
    stmt = select(model)
    if filters:
        for cond in filters:
            stmt = stmt.where(cond)
    if eager_opts:
        stmt = stmt.options(*eager_opts)
    if order_by is not None and len(order_by) > 0:
        stmt = stmt.order_by(*order_by)
    result = db.session.execute(stmt).scalars().all()
    db.session.close()
    return result


def select_with_filter_one(
    model: Type[DeclarativeMeta],
    filters: Optional[List[Any]] = None,
    order_by: Optional[List[Any]] = None,
    eager_opts: Optional[List[Any]] = None,
):
    stmt = select(model)
    if filters:
        for cond in filters:
            stmt = stmt.where(cond)
    if eager_opts:
        stmt = stmt.options(*eager_opts)
    if order_by:
        stmt = stmt.order_by(*order_by)
    result = db.session.execute(stmt).scalars().first()
    db.session.close()
    return result


def select_by_id(
    model: Type[DeclarativeMeta],
    pk: Any,
    eager_opts: Optional[List[Any]] = None,
):
    if eager_opts:
        stmt = select(model).options(*eager_opts).where(model.id == pk)
    else:
        stmt = select(model).where(model.id == pk)
    result = db.session.execute(stmt).scalars().first()
    db.session.close()
    return result


def select_with_pagination(
    model: Type[DeclarativeMeta],
    page: int,
    per_page: int,
    filters: Optional[List[Any]] = None,
    order_by: Optional[List[Any]] = None,
    eager_opts: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    stmt = select(model)
    if filters:
        for cond in filters:
            stmt = stmt.where(cond)
    if eager_opts:
        stmt = stmt.options(*eager_opts)
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
    db.session.close()

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
        db.session.close()
        return instance
    db.session.close()
    return None


def update_by_filter(
    model: Type[DeclarativeMeta],
    filters: List[Any],
    data: Dict[str, Any],
) -> int:
    stmt = select(model)
    for cond in filters:
        stmt = stmt.where(cond)

    instances = db.session.execute(stmt).scalars().all()

    if not instances:
        db.session.close()
        return 0

    for instance in instances:
        for key, value in data.items():
            setattr(instance, key, value)

    db.session.commit()
    db.session.close()
    return len(instances)


def update_multiple_by_ids(
    model: Type[DeclarativeMeta],
    ids: List[Any],
    data: Dict[str, Any],
) -> int:
    stmt = select(model).where(model.id.in_(ids))
    instances = db.session.execute(stmt).scalars().all()

    if not instances:
        db.session.close()
        return 0

    for instance in instances:
        for key, value in data.items():
            setattr(instance, key, value)

    db.session.commit()
    db.session.close()
    return len(instances)


def delete_by_id(
    model: Type[DeclarativeMeta],
    pk: Any,
) -> bool:
    instance = db.session.get(model, pk)
    if instance:
        db.session.delete(instance)
        db.session.commit()
        db.session.close()
        return True
on.commit()
    return len(instances)
