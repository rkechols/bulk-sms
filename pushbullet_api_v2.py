import os
import re
import threading
from typing import Optional

import httpx
from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

__all__ = [
    "PhoneNumberUSA",
    "APIError",
    "PushBullet",
]


# pydantic models


def validate_phone_number_usa(value: str) -> str:
    if re.fullmatch(r"\+1\d{10}", value) is None:
        raise ValueError("not recognized as valid USA phone number; use E.164 format")
    return value

PhoneNumberUSA = Annotated[str, AfterValidator(validate_phone_number_usa)]


class SmsRequestData(BaseModel):
    target_device_iden: str = Field(min_length=1)
    addresses: list[PhoneNumberUSA] = Field(min_length=1)
    message: str
    guid: Optional[str] = None


class SendSmsRequest(BaseModel):
    data: SmsRequestData


class SendSmsResponse(BaseModel):
    iden: str


# user interface


class APIError(Exception):
    """The remote API returned an error code"""


class PushBullet:
    PUSHBULLET_API_URL = "https://api.pushbullet.com/v2"

    def __init__(
            self,
            api_key: Optional[str] = None,
            device_iden: Optional[str] = None,
            httpx_client: Optional[httpx.AsyncClient] = None,
    ):
        api_key = api_key or os.environ["PUSHBULLET_API_KEY"]
        self._headers = {
            "Access-Token": api_key,
        }
        self._device_iden = device_iden or os.environ["PUSHBULLET_DEVICE_ID"]
        self._httpx_client_lock = threading.Lock() if httpx_client is None else None
        self._httpx_client = httpx_client

    async def __aenter__(self):
        lock = self._httpx_client_lock
        if lock is not None:  # no external client was provided
            with lock:
                if self._httpx_client is not None:
                    raise RuntimeError("cannot open a client that is already open")
                self._httpx_client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        lock = self._httpx_client_lock
        if lock is not None:  # no external client was provided
            with lock:
                client = self._httpx_client
                self._httpx_client = None
            if client is not None:
                await client.aclose()

    def _ensure_httpx_client(self) -> httpx.AsyncClient:
        client = self._httpx_client
        if client is None:
            raise RuntimeError("an httpx.AsyncClient was not found; you must either provide "
                               "one to `__init__` or open this object using `async with`")
        return client

    @classmethod
    def check_for_errors(cls, response: httpx.Response) -> httpx.Response:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise APIError(f"response contained an error code of {response.status_code} "
                           f"and had a body/payload of {response.text!r}") from e
        return response

    async def send_sms(self, phone_numbers: list[str] | str, message: str, message_uid: Optional[str] = None) -> str:
        if isinstance(phone_numbers, str):
            phone_numbers = [phone_numbers]
        client = self._ensure_httpx_client()
        request = SendSmsRequest(data=SmsRequestData(
            target_device_iden=self._device_iden,
            addresses=phone_numbers,
            message=message,
            guid=message_uid,
        ))
        response = await client.post(
            f"{self.PUSHBULLET_API_URL}/texts",
            json=request.model_dump(),
            headers=self._headers,
        )
        self.check_for_errors(response)
        response_parsed = SendSmsResponse.model_validate(response.json())
        return response_parsed.iden
