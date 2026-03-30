from dataclasses import dataclass
from typing import Any


@dataclass
class OinNumber:
    def __init__(self, value: Any) -> None:
        """
        Representation of OIN Number, where it can adhere to the requirements
        of that number.
        See: https://logius-standaarden.github.io/Digikoppeling-Identificatie-en-Authenticatie/#oin-formaat-als-thans-in-gebruik-voor-overheids-organisaties
        """
        if (isinstance(value, int) or isinstance(value, str)) and len(str(value)) == 20 and str(value).isdigit():
            self.value = str(value)

        else:
            raise ValueError("OIN must be 20 digits")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"OinNumber({self.value})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, OinNumber):
            return self.value == other.value

        return False
