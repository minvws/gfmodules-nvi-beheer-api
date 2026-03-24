from typing import TypeVar

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


TBase = TypeVar("TBase", bound=Base)
