[![Build Status](https://travis-ci.org/slaclab/pyrogue-control-server.svg?branch=master)](https://travis-ci.org/slaclab/pyrogue-control-server)

# PyRogue General Purpose Control Server

## Overview

This packages generates a general purpose control server interface to an FPGA using [Rogue](https://github.com/slaclab/rogue).

Two python scripts are provided for starting a pyrogue-based server or client:
- python/pyrogue_server.py
- python/pyrogue_client.py

For each one of these python scripts, bash startup scripts are provide. They prepare the environment and launch the python scripts:
- start_server.sh
- start_client.sh

## Requirements

In order to run this software, you need:
- Python3
- An instance of Rogue. A setup script called "setup_rogue.sh" must be provided at the top level, which sources the rogue's environment.
- An instance of the PCIe software (if the PCIe card is present in the system).
- An instance of EPICS (is the EPICS server is intended to be used).

You can create setup scripts named `setup_*.sh` with the commands to setup the environment for each case. For example, `setup_rogue.sh` with the setup for Rogue, `setup_epics.sh` with the setup for EPICS, and so on. The bash scripts (`start_server.sh`, `start_client.sh`) will source all the setup scripts defined in the top directory.

## Communication protocol supported

Currently, the control server supports both Ethernet and PCIe communications. In both Ethernet, RSSI interleaved and not-interleaved are supported; PCIe communication only supports RSSI interleaved.

## Functionalities provided by the server

The control server provides a wrapper around pyrogue, and provides functionalities common to most applications.

First of all, the `start_server.sh` untar the pyrogue tarball in a temporal location and setups the python environment so that Rogue can locate all the application classes definitions. Then it calls `pyrogue_server.py` script with the updated environment.

Secondly, the `pyrogue_server.py` start a rogue Root device, and attached to it an instance of the common module `FpgaTopLevel`. It then add the following modules provided by Rogue:
- A dataWriter to the 8 DDR streams,
- A dataWriter to the 8 streaming interface streams,
- A RunControl,
- An EPICS server (if enabled by the user), with:
  - PVs to read the data from the DDR streams with the possibility to select a maximum number of points,
    - In the obsoleted PCAS server, it also provides additional PV for:
      - Set the data format,
      - Set the data byte order,
  - A PV to load a default configuration file, specified by the user when the server is started,
  - A wrapper to call the function to dump the PV name list to a file when the server is started,
- A Pyro4 server (if enabled by the user)
- A wrapper to disable the Rogue polling when the server is started


Additionally, the `pyrogue_server.py` automatically handles the PCIe card configuration, depending if the card is present in the system, and the type of communication choose by the user in the following way:
- If the PCIe card is present in the system:
  - All the RSSI connection links which point to the target IP address will be closed.
  - If PCIe communication type is used, the RSSI connection is open in the specific link. Also, when the the server is closed, the RSSI connection is closed.
- If the PCIe card is not present:
  - If PCIe communication type is used, the program is terminated.
   - If ETH communication type is used, then this class does not do anything.

## Server arguments

```
Usage: ./start_server.sh -t|--tar <pyrogue.tar.gz>  [-a|--addr IP_address] [-d|--defaults config_file] [-s|--server]
                         [-p|--pyro group_name] [-e|--epics prefix]  [-n|--nopoll] [-b|--stream-size byte_size]
                         [-f|--stream-type data_type]  [-c|--commType comm_type] [-l|--slot slot_number] [-h|--help]

    -t|--tar <pyrogue.tar.gz>  : tarball file with pyrogue definitions.
    -a|--addr IP_address       : FPGA IP address. Mandatory if Ethernet communication is used.
    -d|--defaults config_file  : Default configuration file
    -p|--pyro group_name       : Start a Pyro4 server with group name "group_name"
    -e|--epics prefix          : Start an EPICS server with PV name prefix "prefix"
    -s|--server                : Server mode, without staring a GUI (Must be used with -p and/or -e)
    -n|--nopoll                : Disable all polling
    -c|--commType comm_type    : Communication type with the FPGA (default to "eth-rssi-non-interleaved"
    -l|--pcie-rssi-link index  : PCIe RSSI link (only needed with PCIe). Supported values are 0 to 5
    -b|--stream-size data_size : Expose the stream data as EPICS PVs. Only the first "data_size" points will be exposed. (Must be used with -e)
    -f|--stream-type data_type : Stream data type (UInt16, Int16, UInt32 or Int32). Default is UInt16. (Must be used with -e and -b)
    -u|--dump-pvs file_name    : Dump the PV list to "file_name". (Must be used with -e)
    -h|--help                  : Show this message
```

## Client arguments

```
usage: ./start_client.sh -p|--pyro group_name [-h|--help]
    -p|--pyro group_name     : Pyro4 group name
    -h||--help               : show this message
```

## Modes of operation

This package can be run in three different modes:

### Local Mode

In this mode, a PyRogue server is run in the local host, and a GUI is launched in the same host attached to the server.

Optionally, a Pyro4 and/or EPICS server can be started too (with the `-p` and `-e` options respectively).

For example:

```
./start_server.sh -t <pyrogue.tar.gz> -a <ip_addr> [-p pyro4_group] [-e epics_prefix]
```

**Note:** The FPGA must be connected to the local host so the PyRogue server can establish a communication path.

### Server Mode

Use the argument `s` to enter this mode. In this case a PyRogue server is run in the local host but no GUI is launch.

The root is export to a Pyro4 name server so you can connect to the system with a client from a remote host. Also, an EPICS sever can be started as well in this mode.

To enter this mode, use the argument `s`. Note that in this case, it is mandatory that either the argument `p` or `e` are used.


For example:
```
./start_server.sh -t <pyrogue.tar.gz> -a <ip_addr> -s [-g pyro4_group] [-e epics_prefix]
```

**Note:** The FPGA must be connected to the local host so the PyRogue server can establish a communication path.

### Client Mode

In this mode a client is started on the local host. The client looks for a remote name server, connects to it and looks for the Pyro4 group name. If founds, it will get the root and launch a GUI.

You must specify the Pyro4 group name used to start the server.

For example:

```
./start_client.sh [-g pyro4_group]
```

## Dockers

A Docker image containing Rogue and this control server is provided with each tagged released of this repository. You can find more information in [here](README.docker.md)