import random
import string
from argparse import ArgumentParser
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Request


@asynccontextmanager
async def lifespan(app_: FastAPI):
    password = "".join(random.choices(string.digits + string.ascii_uppercase[:6], k=8))
    app_.state.password = password
    print(f"PASSWORD: {password}")  # noqa: T201
    yield


def _get_password(request: Request) -> str:
    return request.app.state.password


type PasswordDep = Annotated[str, Depends(_get_password)]

app = FastAPI(title="Bulk SMS Server", lifespan=lifespan)


# @app.get("/")
# async def get_root(password: PasswordDep) -> HTMLResponse:
#     return HTMLResponse(content=f"<pre>Password: {password}</pre>")


def main():
    arg_parser = ArgumentParser(description="Run phone-side server for bulk SMS operations")
    arg_parser.add_argument("--port", "-p", type=int, default=8080)
    args = arg_parser.parse_args()
    port: int = args.port

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
