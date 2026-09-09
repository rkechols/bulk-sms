import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel


def _validate_usa_phone_number(s: str) -> str:
    s = re.sub(r"-\s\(\)", "", s)  # Strip hyphens, whitespace, and parens
    if not re.fullmatch(r"\+1\d{10}", s):
        raise ValueError("USA phone number must start with +1 and then contain exactly 10 additional digits")
    return s


type USAPhoneNumber = Annotated[str, AfterValidator(_validate_usa_phone_number)]


class Recipients(BaseModel):
    copy_on_all: dict[str, USAPhoneNumber]
    groups: dict[str, set[USAPhoneNumber]]
