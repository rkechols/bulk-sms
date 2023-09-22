# bulk-sms
Uses PushBullet (pushbullet.com) to send the same SMS message to multiple recipient groups


## Repository structure

Brief descriptions of what's in this repo:
- `requirements.txt`: specifications for what 3rd-party python packages are needed
- `.vscode/`: config files for VS Code
- `pushbullet_api_v2.py`: python interface to the [PushBullet REST API](https://docs.pushbullet.com/)
- `send_bulk_sms.py`: script to programmatically send an SMS to multiple recipients


## Setup

### Environment variables

You'll likely need the following environment variables set:
- `PUSHBULLET_API_KEY`: access token
    (can get this from https://www.pushbullet.com/#settings > Account)
- `PUSHBULLET_DEVICE_ID`: ID of the mobile phone that will be sending SMS
    (see https://docs.pushbullet.com/#list-devices for help getting this ID)

### Python packages

Install 3rd-party python package dependencies using `python -m pip install -r requirements.txt`


## Usage

### send_bulk_sms.py

See help text with `python send_bulk_sms.py -h`

Example usage:
```bash
python send_bulk_sms.py --recipients recipients.json --message message.txt
```

To see an example of what `recipients.json` might contain, run the following in python:
```python
from send_bulk_sms import RecipientSpecs
print(RecipientSpecs.example_json())
```

### pushbullet_api.py

See docstrings inside the file for full explanations of functionality

Example usage:
```python
import asyncio
from pushbullet_api import PushBullet, APIError

async def main():
    async with PushBullet() as pb:
        try:
            message_id = await pb.send_sms(["5555555555", "5555555550"], "Hello world")
            print("sent message with ID", message_id)
        except APIError as e:
            print("ERROR:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
```
