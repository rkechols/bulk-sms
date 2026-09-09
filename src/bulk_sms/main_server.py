# ruff: noqa: S603, S607

import asyncio
import json
import logging
import random
import secrets
import string
import subprocess
from argparse import ArgumentParser
from contextlib import asynccontextmanager
from functools import cache
from pathlib import Path
from typing import Annotated, Any

# import uvicorn
# from fastapi import Depends, FastAPI, HTTPException, Request, status
# from fastapi.responses import RedirectResponse
# from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from bulk_sms.schemas import USAPhoneNumber

DOCS_ROUTE = "/docs"

LOGGER = logging.getLogger(__name__)

JSON_SCHEMAS_DIR = Path(__file__).parent


@cache
def _load_json_schema(name: str) -> dict[str, Any]:
    with open(JSON_SCHEMAS_DIR / f"{name}.schema.json", "r", encoding="utf-8") as f:
        return json.load(f)


BulkSmsRequest = _load_json_schema("BulkSmsRequest")
BulkSmsResponse = _load_json_schema("BulkSmsResponse")
# Example usage: jsonschema.validate(payload, BulkSmsRequest)


class SmsAccessError(Exception):
    """Raise when sending an SMS error fails or is not possible"""


def ensure_sms_viability():
    subprocess.run(["termux-sms-send", "-h"], check=True)


def send_sms(message: str, recipients: set[USAPhoneNumber]):
    subprocess.run(
        [
            "termux-sms-send",
            "-n",
            ",".join(sorted(recipients)),
            message,
        ],
        check=True,
    )


@asynccontextmanager
async def lifespan(app_: FastAPI):
    await asyncio.to_thread(ensure_sms_viability)
    passcode = "".join(random.choices(string.digits + string.ascii_uppercase[:6], k=8))
    app_.state.passcode = passcode
    print(f"PASSCODE: {passcode}")  # noqa: T201
    yield


type AuthBearerDep = Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]


def _validate_passcode(request: Request, auth_bearer: AuthBearerDep):
    if not secrets.compare_digest(auth_bearer.credentials, request.app.state.passcode):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)


ValidatePasscodeDep = Depends(_validate_passcode)


app = FastAPI(title="Bulk SMS Server", docs_url=DOCS_ROUTE, lifespan=lifespan)


@app.get("/")
async def get_root() -> RedirectResponse:
    return RedirectResponse(DOCS_ROUTE)


@app.post("/bulk-sms", dependencies=[ValidatePasscodeDep])
def post_bulk_sms(request_body: BulkSmsRequest) -> BulkSmsResponse:
    recipients_universal = set(request_body.recipients.copy_on_all.values())
    groups_succeeded: set[str] = set()
    groups_failed: set[str] = set()
    for group_name, group in request_body.recipients.groups.items():
        recipients_merged = recipients_universal.union(group)
        try:
            send_sms(request_body.message, recipients_merged)
        except Exception:
            LOGGER.exception(f"Failed to send bulk SMS for group {group_name!r}")
            groups_failed.add(group_name)
        else:
            groups_succeeded.add(group_name)
    response = BulkSmsResponse(
        groups_succeeded=groups_succeeded,
        groups_failed=groups_failed,
    )
    return response


def main():
    arg_parser = ArgumentParser(description="Run phone-side server for bulk SMS operations")
    arg_parser.add_argument("--port", "-p", type=int, default=8080)
    args = arg_parser.parse_args()
    port: int = args.port

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
