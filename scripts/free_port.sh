#!/bin/bash
#
# Find and kill the process running on a given port.
#
# Usage: ./free_port.sh <port>
#
set -e

PORT=$1

if [ -z "$PORT" ]; then
  echo "Usage: $0 <port>"
  exit 1
fi

# Find the PID of the process listening on the specified port
PID=$(sudo lsof -t -i:"$PORT" -sTCP:LISTEN)

if [ -z "$PID" ]; then
  echo "No process found listening on port $PORT."
  exit 0
fi

# Get the command name for the PID
COMMAND_NAME=$(ps -p "$PID" -o comm=)

echo "Process '$COMMAND_NAME' (PID: $PID) is listening on port $PORT."

# Kill the process
read -p "Are you sure you want to kill this process? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Killing process $PID..."
  sudo kill -9 "$PID"
  echo "Process killed."
else
  echo "Aborted."
fi
