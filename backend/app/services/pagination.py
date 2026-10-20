from math import ceil
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def paginate(db: Session, statement: Select[Any], page: int, page_size: int) -> dict[str, Any]:
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = db.scalar(count_statement) or 0
    items = list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all())
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total else 0,
    }
