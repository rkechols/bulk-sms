import os
import re
import threading
from typing import Optional
from uuid import uuid4

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
    if re.fullmatch(r"\d{10}", value) is None:
        raise ValueError("not recognized as valid USA phone number; please write 10 digits with no other symbols or spaces")
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
    PUSHBULLET_API_URL = "https://api.pushbullet.com/v3"

    def __init__(
            self,
            api_key: Optional[str] = None,
            device_iden: Optional[str] = None,
            httpx_client: Optional[httpx.AsyncClient] = None,
    ):
        api_key = api_key or os.environ["PUSHBULLET_API_KEY"]
        self._headers = {
            "Authorization": f"Basic {api_key}",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9,sr-RS;q=0.8,sr;q=0.7,bs-BA;q=0.6,bs;q=0.5,sl-SI;q=0.4,sl;q=0.3,es-US;q=0.2,es;q=0.1,de-DE;q=0.1,de;q=0.1,hr-HR;q=0.1,hr;q=0.1",
            "Api-Version": "2014-05-07",
            "Content-Type": "application/json",
            "Origin": "https://www.pushbullet.com",
            "Referer": "https://www.pushbullet.com/",
            "Sec-Ch-Ua": '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "X-User-Agent": "Pushbullet Website 162",
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

    async def send_sms(self, phone_numbers: list[str] | str, message: str) -> str:
        if isinstance(phone_numbers, str):
            phone_numbers = [phone_numbers]
        client = self._ensure_httpx_client()
        message_uid = str(uuid4()).replace("-", "")[:22]
        request = SendSmsRequest(data=SmsRequestData(
            target_device_iden=self._device_iden,
            addresses=phone_numbers,
            message=message,
            guid=message_uid,
        ))
        response = await client.post(
            f"{self.PUSHBULLET_API_URL}/create-text",
            json=request.model_dump(),
            headers=self._headers,
        )
        self.check_for_errors(response)
        response_parsed = SendSmsResponse.model_validate(response.json())
        return response_parsed.iden
