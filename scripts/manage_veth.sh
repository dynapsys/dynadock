#!/bin/bash
#
# Manage virtual network interfaces for DynaDock services
# This script is intended to be run with sudo.
#

set -e

IFACE_PREFIX="dynadock"

# Function to bring up multiple interfaces from a file
up_all() {
    local ip_map_file=$1
    if [ ! -f "$ip_map_file" ]; then
        echo "Error: IP map file not found at $ip_map_file" >&2
        exit 1
    fi

    while IFS= read -r line; do
        service_name=$(echo "$line" | cut -d'=' -f1)
        ip_address=$(echo "$line" | cut -d'=' -f2)
        iface_name="${IFACE_PREFIX}-${service_name}"

        if ip link show "$iface_name" &>/dev/null; then
            echo "Interface '$iface_name' already exists. Skipping."
            continue
        fi

        echo "Creating virtual interface '$iface_name' with IP $ip_address..."
        ip link add "$iface_name" type dummy
        ip addr add "$ip_address/32" dev "$iface_name"
        ip link set "$iface_name" up
    done < "$ip_map_file"

    echo "✓ All virtual interfaces are up."
}

# Function to tear down multiple interfaces from a file
down_all() {
    local ip_map_file=$1
    if [ ! -f "$ip_map_file" ]; then
        # If the file doesn't exist, there's nothing to do.
        exit 0
    fi

    while IFS= read -r line; do
        service_name=$(echo "$line" | cut -d'=' -f1)
        iface_name="${IFACE_PREFIX}-${service_name}"

        if ip link show "$iface_name" &>/dev/null; then
            echo "Deleting virtual interface '$iface_name'..."
            ip link delete "$iface_name"
        fi
    done < "$ip_map_file"

    echo "✓ All virtual interfaces are down."
}

# Main command handler
COMMAND=$1
IP_MAP_FILE=$2

if [ -z "$COMMAND" ] || [ -z "$IP_MAP_FILE" ]; then
    echo "Usage: $0 {up|down} <path_to_ip_map_file>" >&2
    exit 1
fi

case "$COMMAND" in
    up)
        up_all "$IP_MAP_FILE"
        ;;
    down)
        down_all "$IP_MAP_FILE"
        ;;
    *)
        echo "Invalid command: $COMMAND" >&2
        echo "Usage: $0 {up|down} <path_to_ip_map_file>" >&2
        exit 1
        ;;
esac
