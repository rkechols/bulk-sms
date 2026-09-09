# ruff: noqa: S603, S607

import logging
import random
import secrets
import string
import subprocess
from argparse import ArgumentParser
from collections.abc import Callable
from typing import cast

from flask import Flask, jsonify, redirect, request
from flask.typing import ResponseReturnValue

from bulk_sms.schemas import BulkSmsRequest, BulkSmsResponse, USAPhoneNumber

LOGGER = logging.getLogger(__name__)
PASSCODE_CONFIG_KEY = "PASSCODE"


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


def initialize_app(app_: Flask) -> None:
    ensure_sms_viability()
    passcode = "".join(random.choices(string.digits + string.ascii_uppercase[:6], k=8))
    app_.config[PASSCODE_CONFIG_KEY] = passcode
    print(f"PASSCODE: {passcode}")  # noqa: T201


def validate_passcode(
    view: Callable[..., ResponseReturnValue],
) -> Callable[..., ResponseReturnValue]:
    def wrapped_view(*args: object, **kwargs: object) -> ResponseReturnValue:
        authorization = request.authorization
        passcode = cast(str, app.config[PASSCODE_CONFIG_KEY])
        token = authorization.token if authorization is not None else None
        if (
            authorization is None
            or authorization.type.lower() != "bearer"
            or not isinstance(token, str)
            or not secrets.compare_digest(token, passcode)
        ):
            return "", 401, {"WWW-Authenticate": "Bearer"}
        return view(*args, **kwargs)

    return wrapped_view


app = Flask(__name__)


@app.get("/")
def get_root() -> ResponseReturnValue:
    return redirect("/bulk-sms")


@app.post("/bulk-sms")
@validate_passcode
def post_bulk_sms() -> ResponseReturnValue:
    request_body = cast(BulkSmsRequest, request.get_json())
    recipients_universal = {
        USAPhoneNumber.normalize(phone_number)
        for phone_number in request_body["recipients"]["copy_on_all"].values()
    }  # fmt: skip
    groups_succeeded: set[str] = set()
    groups_failed: set[str] = set()
    for group_name, group in request_body["recipients"]["groups"].items():
        recipients_merged = recipients_universal | {
            USAPhoneNumber.normalize(phone_number)
            for phone_number in group
        }  # fmt: skip
        try:
            send_sms(request_body["message"], recipients_merged)
        except Exception:
            LOGGER.exception(f"Failed to send bulk SMS for group {group_name!r}")
            groups_failed.add(group_name)
        else:
            groups_succeeded.add(group_name)
    response: BulkSmsResponse = {
        "groups_succeeded": sorted(groups_succeeded),
        "groups_failed": sorted(groups_failed),
    }
    return jsonify(response)


def main():
    arg_parser = ArgumentParser(description="Run phone-side server for bulk SMS operations")
    arg_parser.add_argument("--port", "-p", type=int, default=8080)
    args = arg_parser.parse_args()
    port: int = args.port

    initialize_app(app)
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
