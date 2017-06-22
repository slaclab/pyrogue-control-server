# PyRogue General Purpose Control Server

## Overview

This packages generates a general purpose control server interface to an FPGA using PyRogue.

Two python scripts are provide for starting a pyrogue server or a pyrogue client 
- python/pyrogue_server.py
- python/pyrogue_client.py

For each one of these python scripts, bash startup scripts are provide. They prepare the environment and launch the python scripts. A regular use should use these wrappers instead. 
- start_server.sh
- start_client.sh  

## Modes of operation 

This package can be run in three different modes:

### Local Mode

In this mode, a PyRogue server is run in the local host and the GUI is launched. 
The root is export to a Pyro4 name server so you can run a client on a remote host to connect to the system too. You can specify the Pyro4 group name with the "-g" flag, otherwise the default "pyrogue_test" name will be used

**Example**
./start_server.sh -t <pyrogue.tar.gz> -a <ip_addr> [-g pyro4_group]

where:
- pyrogue.tar.gz : is a tarball with the PyRogue definition python classes
- ip_addr        : is the FPGA's IP Address
- pyro4_group    : Optional Pyro4 group name (default = "pyrogue_test")

**Note:** The FPGA must be connected to the local host so the PyRogue server can establish a communication path. 

### Server Mode

In this mode a PyRogue server is run in the local host but no GUI is launch. 
The root is export to a Pyro4 name server so you can connect to the system with a client from a remote host. You can specify the Pyro4 group name with the "-g" flag, otherwise the default "pyrogue_test" name will be used

**Example**
./start_server.sh -t <pyrogue.tar.gz> -a <ip_addr> [-g pyro4_group] -s

where:
- pyrogue.tar.gz : is a tarball with the PyRogue definition python classes
- ip_addr        : is the FPGA's IP Address
- pyro4_group    : Optional Pyro4 group name (default = "pyrogue_test")

**Note:** The FPGA must be connected to the local host so the PyRogue server can establish a communication path. 

### Client Mode

In this mode a client is started on the local host. The client looks for a remote name server, connects to it and looks for the Pyro4 group name. If founds, it will get the root and launch a GUI.
You can especify the Pyro4 group name with the "-g" flag, otherwise the default "pyrogue_test" name will be used

**Example**
./start_client.sh [-g pyro4_group]

where:
- pyro4_group    : Optional Pyro4 group name (default = "pyrogue_test")

## Protocol supported

Currently, the control server supports only UDP+RSSI+SRP to communicate with the FPGA.

The server creates:
- An SRP interface to the FPGA using: 
-- UDP port 8193, frame size 1500
-- RSSI
-- Packetizer 
-- SRP V3

- Eight Stream interfaces to the FPGA using:
-- UDP port 8194, frame size 1500
-- RSSI
-- Packetizer with TDEST from 0 to 7

The eight streams are connected to data writers, so data sis written to disk.

## Requirements

In order to run this software, you need:
- Python v3
- An instance of Rogue: its location is defined in the bash startup scripts.



