import re
from typing import TypedDict


class USAPhoneNumber(str):
    """Special type alias that gets basedpyright to fully differentiate"""

    __slots__ = ()

    @classmethod
    def normalize(cls, s: str) -> "USAPhoneNumber":
        s = re.sub(r"[\-\s\(\)]", "", s)  # Strip hyphens, whitespace, and parens
        if not re.fullmatch(r"\+1\d{10}", s):
            raise ValueError("USA phone number must start with +1 and then contain exactly 10 additional digits")
        return USAPhoneNumber(s)


class Recipients(TypedDict):
    copy_on_all: dict[str, str]
    groups: dict[str, list[str]]


class BulkSmsRequest(TypedDict):
    recipients: Recipients
    message: str


class BulkSmsResponse(TypedDict):
    groups_succeeded: list[str]
    groups_failed: list[str]
