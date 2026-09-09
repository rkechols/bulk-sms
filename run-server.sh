#!/usr/bin/env bash

set -e

export PORT=8080

tunnel_pid=""

cleanup() {
  if [[ -n "$tunnel_pid" ]] && kill -0 "$tunnel_pid" 2>/dev/null; then
    kill "$tunnel_pid" 2>/dev/null || true
    wait "$tunnel_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

ssh -R "443:localhost:$PORT" v2@connect.ngrok-agent.com http &
tunnel_pid=$!

uv run --no-default-groups -- sms-server --port "$PORT"
