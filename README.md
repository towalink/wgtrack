# wgtrack

> wgtrack tracks WireGuard links, exports the links' status, and updates endpoints as needed.

WireGuard is a great VPN solution. wgtrack provides the tooling around it to track the status of the links and export the data for monitoring solutions. It also re-resolves endpoint hostnames to thus support connections between dial-in peers with changing IP addresses.
Note: This is code in "works for me" quality; it is not tested properly. This tool started as an exercise in using Python's asyncio library.

---

## Installation

wgtrack can be installed easily on Linux:

- Make sure that you use Python version 3.5 or newer
- Install wgtrack from PyPi

```shell
$ pip install wgtrack
```

- Configure wgtrack using /etc/wgtrack.conf
- Configure wgtrack to run as services as needed

### Clone (for developers only)

- Clone this repo to your local machine using `https://github.com/towalink/wgtrack.git`

---

## Features

- Checks the status of WireGuard links based on heartbeat success
- Optionally ping the remote peers regularly to check the tunnels
- Export the status of WireGuard links (eg. attributes like tx/rx counters) for use by monitoring applications (currently: Telegraf)
- Re-resolve the endpoint in case of tunnel failure to thus support endpoints with changing IP addresses (can be used for "UDP Hole Punching" in NAT scenarios, tested with FritzBox routers)
- Fine-granular control of timers to avoid unnecessary traffic and DNS requests.

## Usage

- Basic usage

> Start wgtrack using the config file /etc/wgtrack.conf:

```shell
$ python -m wgtrack
```

- You may specify some command line parameters as needed

> Alternative config file:

```shell
$ python -m wgtrack --config /etc/my_special_wgtrack.conf
```
- Configure the detail of logging information

```shell
$ python -m wgtrack --loglevel debug
```

- Show help page for details on command line arguments

```shell
$ python -m wgtrack --help
```

## Documentation

After initialization (1), this tool periodically queries the status (2) of the WireGuard links, acts on their peers' status (3), and outputs the status (4) as requested.

### (1) Initialization

The wgtrack configuration file and also the WireGuard configuration files in "/etc/wireguard" are read. Based on this, the tool knows about all configured WireGuard interfaces and their peers (including configured endpoint hostnames). In case of a change of the configuration, wgtrack may be notified by a SIGHUP signal to redo this initialization step.

The wgtrack configuration file used the ini format. General parameters are specified in the "[general]" section. Parameters that shall be applied to all sections are specified in the "[DEFAULT]" section. Parameters for individual interfaces are specified in sections named "[interface:<ifname>]" with "<ifname>" being the name of the interface. Parameters for individual outputs are specified in sections named "[output:<outputname>]" with "<outputname>" being the name of the output.

### (2) Periodic queries

wgtrack periodically queries the status of the WireGuard interfaces and their peers. This is done using the "wg show all dump" command.
How often this is done can be configured using the "cycle_time" parameter (default: 30s).

In case the heartbeat of a link to a peer shows usual times that indicate a working link, the link can be checked using echo requests. By default, this is done each "cycle_time" (default "ping_interval" is 1 for this). It can be disabled by setting "ping_interval" to 0. After the configured number of failed echo requests ("ping_failafternum", default 2), the link is considered down despite the heartbeat appearing ok.
The first "allowed-ip" configured for the respective peer is used as the destination for the respective echo request.

### (3) Act on peer status

If a link is considered down, its peer endpoint can be re-resolved. Before this is done, the tool waits for the configured number of periods ("cycles_wait", default 2) to wait for an Internet connection with a dynamic IP address to be reestablished after disconnection. After that, the endpoint is re-resolved "cycles_checking" times each multitude "cycles_checkperiod" of the "cycle_time". After that, an exponential back-off takes place. However, "cycles_slowcheckingperiod" (default 20) defines the longest interval (as a multitude of the "cycle_time" until a regular recheck is done.

### (4) Output the interface and peer status

Outputs for the status information can be configured. Currently, the wire protocol of InfluxDB is supported as output format. This format is used by "Telegraf".

In the Telegraf config, something like the following needs to be added:
```
[[inputs.file]]
   files = ["/var/cache/wg-track_influx.out"]
```

---

## License

[![License](http://img.shields.io/:license-gpl3-blue.svg?style=flat-square)](http://opensource.org/licenses/gpl-license.php)

- **[GPL3 license](http://opensource.org/licenses/gpl-license.php)**
- Copyright 2020 © <a href="https://www.github.com/towalink/wgtrack" target="_blank">The Towalink Project</a>.
