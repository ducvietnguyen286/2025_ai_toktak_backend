from typing import Type, List, Any, Dict, Optional
from mongoengine import Document, Q


def select_with_pagination_mongo(
    model: Type[Document],
    page: int,
    per_page: int,
    filters: Optional[List[Q]] = None,
    order_by: Optional[List[str]] = None,
) -> Dict[str, Any]:
    qs = model.objects

    if filters:
        for cond in filters:
            qs = qs.filter(cond)
    if order_by:
        qs = qs.order_by(*order_by)

    total = qs.count()

    skip = (max(page, 1) - 1) * per_page
    items = qs.skip(skip).limit(per_page)

    total_pages = (total + per_page - 1) // per_page

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": total_pages,
        "items": list(items),
    }
