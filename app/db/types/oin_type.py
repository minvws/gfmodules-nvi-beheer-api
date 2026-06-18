from sqlalchemy import Dialect, String, TypeDecorator

from app.models.oin import Oin


class OinType(TypeDecorator[Oin]):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Oin | None, dialect: Dialect) -> str | None:
        if value is not None:
            return str(value)
        return None

    def process_result_value(self, value: str | None, dialect: Dialect) -> Oin | None:
        if value is not None:
            return Oin(value)
        return None
