# ruff: noqa: T201

import json
import os
from argparse import ArgumentParser
from pathlib import Path

import dotenv
import httpx2

from bulk_sms.schemas import BulkSmsRequest, Recipients, USAPhoneNumber

dotenv.load_dotenv()

SERVER_URL_BASE = os.environ["SERVER_URL_BASE"]
SERVER_URL = f"{SERVER_URL_BASE}/bulk-sms"


def _read_recipients_file(filepath: Path) -> Recipients:
    filepath = filepath.resolve()
    with open(filepath, "r", encoding="utf-8") as f:
        recipients_raw = json.load(f)
    recipients: Recipients = {
        "copy_on_all": {
            name: USAPhoneNumber.normalize(phone_number)
            for name, phone_number in recipients_raw["copy_on_all"].items()
        },
        "groups": {
            group_name: [USAPhoneNumber.normalize(phone_number) for phone_number in group]
            for group_name, group in recipients_raw["groups"].items()
        },
    }  # fmt: skip
    return recipients


def _read_message_file(filepath: Path) -> str:
    filepath = filepath.resolve()
    with open(filepath, "r", encoding="utf-8") as f:
        message = f.read().strip()
    if not message:
        raise ValueError(f"Message file empty: {filepath}")
    return message


def main():
    arg_parser = ArgumentParser(description="Send requests to phone-side server")
    arg_parser.add_argument("--passcode", "-p", required=True)
    arg_parser.add_argument("--recipients-file", "-r", type=Path, default=Path("recipients.json"))
    arg_parser.add_argument("--message-file", "-m", type=Path, default=Path("message.txt"))
    args = arg_parser.parse_args()
    passcode: str = args.passcode

    recipients = _read_recipients_file(args.recipients_file)
    message = _read_message_file(args.message_file)
    request: BulkSmsRequest = {
        "recipients": recipients,
        "message": message,
    }

    response = httpx2.post(
        SERVER_URL,
        headers={"Authorization": f"Bearer {passcode}"},
        json=request,
    )
    response.raise_for_status()
    print(f"Response: {json.dumps(response.json(), indent=2)}")


if __name__ == "__main__":
    main()
