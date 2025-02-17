#!/usr/bin/env python

# pip install deluge-client

from __future__ import print_function
import os
import sys
import time
from deluge_client import DelugeRPCClient

# Get command line arguments for torrent ID, name, and path
torrent_id = sys.argv[1]
torrent_name = sys.argv[2]
torrent_path = sys.argv[3]

# Get Deluge RPC client connection details from env if available
ip = os.getenv('DELUGE_HOST', "127.0.0.1")
port = int(os.getenv('DELUGE_PORT', 58846))
username = os.getenv('DELUGE_USER', 'admin')
password = os.getenv('DELUGE_PASS', 'deluge')

# Set up loop parameters
max_iterations = 120
iteration_interval = 7


# TODO: disable printing unless VERBOSE
def dprint(msg):
    now = time.localtime()
    hms = time.strftime('%H:%M:%S', now)
    id_short = torrent_id[:7]
    print(f'[{hms}] {id_short} {msg}')


# Connect to the Deluge RPC client
dprint(f'Connecting to {ip}:{port} as user {username}')
client = DelugeRPCClient(ip, port, username, password)
client.connect()
dprint(f'Connected')

# Loop for a maximum number of iterations
for i in range(max_iterations):
    
    # Sleep for the iteration interval
    dprint(f'i={i} Sleeping {iteration_interval} ...')
    time.sleep(iteration_interval)

    # Get torrent information
    dprint(f'i={i} Calling get_torrent_status')
    torrent_info = client.call('core.get_torrent_status', torrent_id, [])

    # Check if the torrent is found
    if not torrent_info:
        print("Torrent not found or removed.")
        break

    # Get tracker status
    tracker_status = torrent_info.get(b'tracker_status', b'').decode('utf-8')
    dprint(f'i={i} tracker_status={tracker_status}')

    if 'Error: Too Many Requests' in tracker_status:
        # Slow down, cowboy
        dprint(f'i={i} Backing off')
        pass
    elif any(substr in tracker_status for substr in ['unregistered', 'Sent', 'End of file', 'Bad Gateway', 'Error']):
        # Force reannounce if tracker status indicates an issue
        dprint(f'i={i} Forcing reannounce')
        client.call('core.force_reannounce', [torrent_id])
    else:
        # Get seed information
        seeds = torrent_info.get(b'num_seeds', 0)
        total_seeds = torrent_info.get(b'total_seeds', 0)

        # If there are seeds, perform additional reannounces
        if seeds > 0 or total_seeds > 0:
            dprint(f'i={i} num_seeds={seeds} total_seeds={total_seeds}')

            extra_iterations = 2
            extra_interval = 30

            for j in range(extra_iterations):
                dprint(f'i={i} j={j} Sleeping {extra_interval}')
                time.sleep(extra_interval)
                dprint(f'i={i} j={j} Forcing reannounce')
                client.call('core.force_reannounce', [torrent_id])

            dprint(f'i={i} Found working torrent')

            break
        else:
            # Force reannounce if no seeds are found
            dprint(f'i={i} No seeds, forcing reannounce')
            client.call('core.force_reannounce', [torrent_id])

# Disconnect from the Deluge RPC client
client.disconnect()
