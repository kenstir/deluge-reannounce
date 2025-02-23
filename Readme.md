
# Deluge Torrent Reannounce Script

This Python script automates reannouncing torrents in Deluge to improve the chances of finding seeds. It uses the submodule `deluge-client` to communicate with the Deluge daemon.

Use this with the Execute plugin to be called on the Torrent Added event.


## Usage

```
/path/deluge-reannounce/reannounce torrent_id torrent_name save_path
```

The arguments `torrent_id`, `torrent_name`, and `save_path` are added automatically
when called from the Deluge Execute plugin on the Torrent Added event.


## Configuration

If you run the script inside the [LinuxServer.io docker container](https://docs.linuxserver.io/images/docker-deluge/),
then there is no configuration needed.  Otherwise, set the following variables in the environment:

| `DELUGE_HOST` | hostname or IP address of Deluge server |
| `DELUGE_PORT` | RPC port number                         |
| `DELUGE_USER` | username |
| `DELUGE_PASS` | password |
