import asyncio
from pathlib import Path

from pydantic import BaseModel

from pushbullet_api_v2 import PhoneNumberUSA, PushBullet


class RecipientSpecs(BaseModel):
    universals: dict[str, PhoneNumberUSA] = {}
    groups: dict[str, dict[str, PhoneNumberUSA] | PhoneNumberUSA] = {}


def load_data(group_specs_filepath: Path) -> list[tuple[str, list[PhoneNumberUSA]]]:
    with open(group_specs_filepath, "r", encoding="utf-8") as f:
        group_specs = RecipientSpecs.model_validate_json(f.read())
    universals = set(group_specs.universals.values())
    groups = {}
    for group_name, group in group_specs.groups.items():
        if isinstance(group, str):  # single phone number
            group_numbers = {group}
        else:  # dict
            group_numbers = set(group.values())
        groups[group_name] = sorted(group_numbers | universals)
    groups_ordered = sorted(groups.items())
    return groups_ordered


async def send_messages(message: str, groups_ordered: list[tuple[str, list[PhoneNumberUSA]]]) -> list[str | Exception]:
    async with PushBullet() as pb:
        results = await asyncio.gather(
            *(pb.send_sms(phone_numbers, message) for _, phone_numbers in groups_ordered),
            return_exceptions=True,
        )
    return results


def main(group_specs_filepath: Path, message: str):
    groups_ordered = load_data(group_specs_filepath)
    # check with the user
    print("----- MESSAGE -----")
    print(message)
    print("----- RECIPIENTS -----")
    for group_name, phone_numbers in groups_ordered:
        print(f"{group_name}:", ", ".join(phone_numbers))
    print("-" * 20)
    response = input("Would you like to send? (y/N): ")
    if response.strip().lower() not in ("y", "yes"):
        print("ABORT")
        return
    print("sending...")
    # execute, then display results
    results = asyncio.run(send_messages(message, groups_ordered))
    print("----- RESULTS -----")
    for (group_name, phone_numbers), result in zip(groups_ordered, results):
        print(f"{group_name}:")
        print("  phone numbers:", ", ".join(phone_numbers))
        print(f"  result: {result!r}")


if __name__ == "__main__":
    from argparse import ArgumentParser
    arg_parser = ArgumentParser()
    arg_parser.add_argument("group_specs_filepath", type=Path)
    arg_parser.add_argument("--message", "-m", type=str, required=True)
    args = arg_parser.parse_args()
    main(args.group_specs_filepath, args.message)
