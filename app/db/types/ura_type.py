from sqlalchemy import Dialect, String, TypeDecorator

from app.models.ura import UraNumber


class UraType(TypeDecorator[UraNumber]):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: UraNumber | None, dialect: Dialect) -> str | None:
        if value is not None:
            return str(value)
        return None

    def process_result_value(self, value: str | None, dialect: Dialect) -> UraNumber | None:
        if value is not None:
            return UraNumber(value)
        return None
