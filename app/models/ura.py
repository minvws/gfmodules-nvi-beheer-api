from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class UraNumber:
    """
    Representation of an URA Number, where it can adhere to the requirements
    of that number.
    See: https://www.zorgcsp.nl/documents/10-01-2025%20RK1%20CPS%20UZI-register%20V11.9%20NL.pdf
    """

    value: str

    def __init__(self, value: Any) -> None:
        if isinstance(value, UraNumber):
            value = value.value

        if (isinstance(value, int) or isinstance(value, str)) and len(str(value)) <= 8 and str(value).isdigit():
            self.value = str(value).zfill(8)
        else:
            raise ValueError("URA number must be 8 digits or less")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"UraNumber({self.value})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, UraNumber):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._pydantic_validate,
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def _pydantic_validate(cls, value: Any) -> "UraNumber":
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except (ValueError, TypeError) as exc:
            raise ValueError(str(exc)) from exc

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema: core_schema.CoreSchema, _handler: Any) -> JsonSchemaValue:
        return {
            "type": "string",
            "pattern": r"^\d{8}$",
            "examples": ["00000001", "12345678"],
            "description": "URA number as an 8-digit string (left-padded with zeros when input is shorter).",
        }
