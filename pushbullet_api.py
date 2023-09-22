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
    """python async interface to PushBullet's REST API"""

    PUSHBULLET_API_URL = "https://api.pushbullet.com"

    def __init__(
            self,
            api_key: Optional[str] = None,
            device_iden: Optional[str] = None,
            httpx_client: Optional[httpx.AsyncClient] = None,
    ):
        """
        construct an instance

        Parameters
        ----------
        api_key : Optional[str], optional
            API key / access token for authentication, by default None.
            If None, uses value of environment variable `PUSHBULLET_DEVICE_ID`.
            Can get this value from https://www.pushbullet.com/#settings > Account
        device_iden : Optional[str], optional
            ID of the mobile device that will be sending SMS messages, by default None.
            If None, uses value of environment variable `PUSHBULLET_DEVICE_ID`.
            See https://docs.pushbullet.com/#list-devices for help getting this ID
        httpx_client : Optional[httpx.AsyncClient], optional
            pre-instantiated client, by default None.
            If None, a new client instance is created and this `PushBullet` must be opened and closed using an `async with` block.
        """
        api_key = api_key or os.environ["PUSHBULLET_API_KEY"]
        self._headers = {
            "Authorization": f"Basic {api_key}",
            "Accept": "*/*",
            "Api-Version": "2014-05-07",
            "Content-Type": "application/json",
        }
        self._device_iden = device_iden or os.environ["PUSHBULLET_DEVICE_ID"]
        self._httpx_client_lock = threading.Lock() if httpx_client is None else None
        self._httpx_client = httpx_client

    async def __aenter__(self):
        """async context manager open; instantiates and opens a httpx.AsyncClient if needed"""
        lock = self._httpx_client_lock
        if lock is not None:  # no external client was provided
            with lock:
                if self._httpx_client is not None:
                    raise RuntimeError("cannot open a client that is already open")
                self._httpx_client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """async context manager close; closes our httpx.AsyncClient if we were the ones who opened it"""
        lock = self._httpx_client_lock
        if lock is not None:  # no external client was provided
            with lock:
                client = self._httpx_client
                self._httpx_client = None
            if client is not None:
                await client.aclose()

    def _ensure_httpx_client(self) -> httpx.AsyncClient:
        """helper function for safely retrieving our httpx.AsyncClient, or correctly raising an error if we don't have one"""
        client = self._httpx_client
        if client is None:
            raise RuntimeError("an httpx.AsyncClient was not found; you must either provide "
                               "one to `__init__` or open this object using `async with`")
        return client

    @classmethod
    def check_for_errors(cls, response: httpx.Response) -> httpx.Response:
        """wrapper around `httpx.Response.raise_for_status which raises a custom exception with a more descriptive message"""
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise APIError(f"response contained an error code of {response.status_code} "
                           f"and had a body/payload of {response.text!r}") from e
        return response

    async def send_sms(self, phone_numbers: list[str] | str, message: str) -> str:
        """
        send an SMS message to the specified phone number(s) (if multiple, it's sent as a GROUP message)

        Parameters
        ----------
        phone_numbers : list[str] | str
            the phone number or phone numbers to send an SMS to.
            if multiple phone numbers, the message is sent as a GROUP message
        message : str
            the message to be sent

        Returns
        -------
        str
            ID (`iden`) of the sent message
        """
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
            f"{self.PUSHBULLET_API_URL}/v3/create-text",
            json=request.model_dump(),
            headers=self._headers,
        )
        self.check_for_errors(response)
        response_parsed = SendSmsResponse.model_validate(response.json())
        return response_parsed.iden
