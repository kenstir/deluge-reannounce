#!/usr/bin/env python
#
# deluge_reannounce - loop and reannounce until torrent in good health after starting
#
#     Derived from xx
#     which was probably derived from xx
#
# usage: deluge_reannounce.py $torrent_id $torrent_name $torrent_path

import json
import os
import sys
import time
from deluge_client import DelugeRPCClient

torrent_id = ''


def main():
    # Get command line arguments for torrent ID, name, and path
    if len(sys.argv) != 4:
        print('usage: deluge_reannounce torrent_id torrent_name torrent_path')
        exit(1)
    global torrent_id
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
    extra_iterations = 2
    extra_interval = 30

    # Connect to the Deluge RPC client
    log_debug(f'Connecting to {ip}:{port} as user {username}')
    client = DelugeRPCClient(ip, port, username, password)
    client.connect()
    log_notice(f'Connected to {ip}:{port}')

    # Loop for a maximum number of iterations
    for i in range(max_iterations):

        # Sleep for the iteration interval
        log_debug(f'i={i} Sleep {iteration_interval} ...')
        time.sleep(iteration_interval)

        # Get torrent information
        log_debug(f'i={i} Calling get_torrent_status')
        torrent_info = client.call('core.get_torrent_status', torrent_id, [])

        # Check if the torrent is found
        if not torrent_info:
            log_notice('Torrent not found or removed.')
            break

        # Print a bunch of stuff for debugging
        info = debug_torrent_info(torrent_info)
        log_debug(f'i={i} info={info}')
        progress = torrent_info.get(b'progress', 0.0)
        total_payload_download = torrent_info.get(b'total_payload_download', 0)
        total_payload_upload = torrent_info.get(b'total_payload_upload', 0)
        log_debug(f'i={i} progress={progress} down={total_payload_download} up={total_payload_upload}')

        # Bail if complete
        if torrent_info.get(b'is_finished', True):
            log_notice('Torrent is finished.')
            break

        # Get tracker status
        tracker_status = torrent_info.get(b'tracker_status', b'').decode('utf-8')
        log_notice(f'i={i} tracker_status={tracker_status}')

        if any(substr in tracker_status for substr in ['Announce Sent', 'Too Many Requests']):
            # Slow down, cowboy
            log_notice(f'i={i} Holding off')
            pass
        elif any(substr in tracker_status for substr in ['unregistered', 'Sent', 'End of file', 'Bad Gateway', 'Error']):
            # Force reannounce if tracker status indicates an issue
            log_notice(f'i={i} Forcing reannounce')
            client.call('core.force_reannounce', [torrent_id])
        else:
            # Get seed information
            seeds = torrent_info.get(b'num_seeds', 0)
            total_seeds = torrent_info.get(b'total_seeds', 0)
            log_notice(f'i={i} num_seeds={seeds} total_seeds={total_seeds}')

            # If there are seeds, perform additional reannounces
            # (but why??? because upstream did it that's why)
            if seeds > 0 or total_seeds > 0:
                for j in range(extra_iterations):
                    log_debug(f'i={i} j={j} Sleeping {extra_interval}')
                    time.sleep(extra_interval)
                    log_notice(f'i={i} j={j} Forcing reannounce')
                    client.call('core.force_reannounce', [torrent_id])

                log_notice(f'i={i} Torrent OK')

                break
            else:
                # Force reannounce if no seeds are found
                log_notice(f'i={i} No seeds, forcing reannounce')
                client.call('core.force_reannounce', [torrent_id])

    # Disconnect from the Deluge RPC client
    client.disconnect()


# print debug-level message
# TODO: real logging with levels
def log_debug(msg):
    #log_msg(msg)
    pass


# print notice-level message
def log_notice(msg):
    log_msg(msg)


def log_msg(msg):
    hms = time.strftime('%Y-%m-%d %H:%M:%S')
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


def debug_torrent_info(torrent_info):
    info = convert_bytes_to_strings(torrent_info)
    sparse_info = {k: v for k, v in info.items() if k in [
        'active_time', 'all_time_download', 'is_finished', 'message', 'next_announce', 'num_peers', 'num_seeds',
        'progress', 'state', 'total_payload_download', 'total_payload_upload', 'total_peers', 'total_seeds',
        'tracker_status', 'time_since_download', 'time_since_upload']}
    pretty_info = json.dumps(sparse_info, indent=4)
    return pretty_info


if __name__ == '__main__':
    main()
