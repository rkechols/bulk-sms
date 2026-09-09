import random
import secrets
import string
from argparse import ArgumentParser
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from bulk_sms.schemas import Recipients

DOCS_ROUTE = "/docs"


@asynccontextmanager
async def lifespan(app_: FastAPI):
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


class SendBulkSmsResponse(BaseModel):
    pass


@app.post("/send-bulk-sms", dependencies=[ValidatePasscodeDep])
async def send_bulk_sms(request_body: Recipients) -> SendBulkSmsResponse:
    pass


def main():
    arg_parser = ArgumentParser(description="Run phone-side server for bulk SMS operations")
    arg_parser.add_argument("--port", "-p", type=int, default=8080)
    args = arg_parser.parse_args()
    port: int = args.port

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
