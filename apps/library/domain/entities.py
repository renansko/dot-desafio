from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Book:
    title: str
    author: str
    publication_date: date
    summary: str
    id: int | None = None
