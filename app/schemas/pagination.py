from math import ceil
from typing import Self

from pydantic import BaseModel


class Page[ItemType](BaseModel):
    items: list[ItemType]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list, total: int, page: int, size: int) -> Self:
        return cls(
            items=items, total=total, page=page, size=size, pages=ceil(total / size)
        )
