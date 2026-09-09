import json
from pathlib import Path

from bulk_sms.schemas import BulkSmsRequest, BulkSmsResponse

CLASSES_TO_DUMP = (
    BulkSmsRequest,
    BulkSmsResponse,
)

OUTPUT_DIR = Path("src/bulk_sms")


def main():
    for class_ in CLASSES_TO_DUMP:
        schema = class_.model_json_schema()
        with open(OUTPUT_DIR / f"{class_.__name__}.schema.json", "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)


if __name__ == "__main__":
    main()
