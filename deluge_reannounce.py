#!/usr/bin/env python

import json
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
max_iterations = 60
iteration_interval = 7


# debug print
# TODO: real logging with levels
def dprint(msg):
    log_notice(msg)


# print notice-level message
def log_notice(msg):
    now = time.localtime()
    hms = time.strftime('%H:%M:%S', now)
    id_short = torrent_id[:7]
    print(f'[{hms}] {id_short} {msg}')


def convert_bytes_to_strings(o):
    """Converts all bytes in a nested object to strings

    Deluge RPC returns bytes for keys and values in dictionaries.
    """
    if isinstance(o, dict):
        new_o = {}
        for k, v in o.items():
            if isinstance(k, bytes):
                new_k = k.decode('utf-8')
            else:
                new_k = k
            new_o[new_k] = convert_bytes_to_strings(v) # Recursively handle nested objects
        return new_o
    elif isinstance(o, list):
        return [convert_bytes_to_strings(item) for item in o]
    elif isinstance(o, tuple):
        return tuple([convert_bytes_to_strings(item) for item in o])
    elif isinstance(o, bytes):
        return o.decode('utf-8')
    else:
        return o


def dump_torrent_info(torrent_info):
    info = convert_bytes_to_strings(torrent_info)
    sparse_info = {k: v for k, v in info.items() if k in [
        'active_time', 'all_time_download', 'is_finished', 'message', 'next_announce', 'num_peers', 'num_seeds',
        'progress', 'state', 'total_payload_download', 'total_payload_upload', 'total_peers', 'total_seeds',
        'tracker_status', 'time_since_download', 'time_since_upload']}
    pretty_info = json.dumps(sparse_info, indent=4)
    dprint(f'i={i} info={pretty_info}')


# Connect to the Deluge RPC client
dprint(f'Connecting to {ip}:{port} as user {username}')
client = DelugeRPCClient(ip, port, username, password)
client.connect()
dprint(f'Connected')

# Loop for a maximum number of iterations
for i in range(max_iterations):

    # Sleep for the iteration interval
    dprint(f'i={i} Sleep {iteration_interval} ...')
    time.sleep(iteration_interval)

    # Get torrent information
    dprint(f'i={i} Calling get_torrent_status')
    torrent_info = client.call('core.get_torrent_status', torrent_id, [])

    # Check if the torrent is found
    if not torrent_info:
        log_notice('Torrent not found or removed.')
        break

    # Print a bunch of stuff for debugging
    dump_torrent_info(torrent_info)
    progress = torrent_info.get(b'progress', 0.0)
    total_payload_download = torrent_info.get(b'total_payload_download', 0)
    total_payload_upload = torrent_info.get(b'total_payload_upload', 0)
    dprint(f'i={i} progress={progress} down={total_payload_download} up={total_payload_upload}')

    # Bail if complete
    if torrent_info.get(b'is_finished', True):
        log_notice('Torrent is finished.')
        break

    # Get tracker status
    tracker_status = torrent_info.get(b'tracker_status', b'').decode('utf-8')
    dprint(f'i={i} tracker_status={tracker_status}')

    if 'Too Many Requests' in tracker_status:
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
        dprint(f'i={i} num_seeds={seeds} total_seeds={total_seeds}')

        # If there are seeds, perform additional reannounces
        # (but why???)
        if seeds > 0 or total_seeds > 0:
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
