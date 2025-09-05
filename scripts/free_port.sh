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

# Find PIDs of processes listening on the specified port
PIDS=$(sudo lsof -t -i:"$PORT" -sTCP:LISTEN || true)

if [ -z "$PIDS" ]; then
  echo "No process found listening on port $PORT."
  exit 0
fi

# Display information for each process found
for PID in $PIDS; do
  COMMAND_NAME=$(ps -p "$PID" -o comm=)
  echo "Process '$COMMAND_NAME' (PID: $PID) is listening on port $PORT."
done

# Kill the processes
read -p "Are you sure you want to kill these processes? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Killing processes with PIDs: $PIDS..."
  echo "$PIDS" | xargs sudo kill -9
  echo "Processes killed."
else
  echo "Aborted."
fi
