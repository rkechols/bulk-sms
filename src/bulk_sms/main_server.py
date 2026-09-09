from argparse import ArgumentParser

import uvicorn
from fastapi import FastAPI

api = FastAPI(title="Bulk SMS Server")


def main():
    arg_parser = ArgumentParser(description="Run phone-side server for bulk SMS operations")
    arg_parser.add_argument("--port", "-p", type=int, default=8080)
    args = arg_parser.parse_args()
    port: int = args.port

    uvicorn.run(api, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
