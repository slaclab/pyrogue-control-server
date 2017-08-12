#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : PyRogue Server
#-----------------------------------------------------------------------------
# File       : python/pyrogue_server.py
# Created    : 2017-06-20
#-----------------------------------------------------------------------------
# Description:
# Python script to start a PyRogue Control Server
#-----------------------------------------------------------------------------
# This file is part of the pyrogue-control-server software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import sys
import getopt
import socket 
import os
import subprocess
import time
import struct

import pyrogue
import pyrogue.protocols
import rogue.protocols.srp
import rogue.protocols.udp
import pyrogue.utilities.fileio
import rogue.interfaces.stream
import PyQt4.QtGui
import pyrogue.gui
import pyrogue.epics

try:
    from FpgaTopLevel import FpgaTopLevel
except ModuleNotFoundError:
    pass

# Print the usage message
def usage(name):
    print("Usage: %s -a|--addr IP_address [-d|--defaults config_file] [-s|--server] [-p|--pyro group_name] [-e|--epics prefix] [-h|--help]" % name)
    print("    -h||--help                : show this message")
    print("    -a|--addr IP_address      : FPGA IP address")
    print("    -d|--defaults config_file : Default configuration file (optional)")
    print("    -p|--pyro group_name      : Start a Pyro4 server with group name \"group_name\"")
    print("    -e|--epics prefix         : Start an EPICS server with PV name prefix \"prefix\"")
    print("    -s|--server               : Server mode, without staring a GUI (Must be use with -p and/or -e)")
    print("")
    print("Examples:")
    print("    %s -a IP_address                            : Start a local rogue server, with GUI, without Pyro nor EPICS servers" % name)
    print("    %s -a IP_address -e prefix                  : Start a local rogue server, with GUI, with EPICS server" % name)
    print("    %s -a IP_address -e prefix -p group_name -s : Start a local rogure server, without GUI, with Pyro and EPICS servers" % name)
    print("")

# Cretae gui interface
def create_gui(root):
    app_top = PyQt4.QtGui.QApplication(sys.argv)
    gui_top = pyrogue.gui.GuiTop(group='GuiTop')
    gui_top.resize(800, 1000)
    gui_top.addTree(root)
    print("Starting GUI...\n")

    try:
        app_top.exec_()
    except KeyboardInterrupt:
        # Catch keyboard interrupts while the GUI was open
        pass

    print("GUI was closed...")

# Exit with a error message
def exit_message(message):
    print(message)
    print("")
    exit()

# Get the hostname of this PC
def get_host_name():
    return subprocess.check_output("hostname").strip().decode("utf-8")

class DataBuffer(rogue.interfaces.stream.Slave):
    """
    Data buffer class use to receive data from a stream interface and \
    copies into a local buffer using a especific format
    """
    def __init__(self, size):
        rogue.interfaces.stream.Slave.__init__(self)
        self._buf = [0] * size

        # Data format: uint16, le
        self._data_byte_order = '<'        
        self._data_format     = 'h'
        self._data_size       = 2
        self._callback        = lambda: None

    def _acceptFrame(self, frame):
        """
        This method is called when a stream frame is received
        """
        data = bytearray(frame.getPayload())
        frame.read(data, 0)
        self._buf = struct.unpack('%s%d%s' % (self._data_byte_order, \
            (len(data)//self._data_size), self._data_format), data)
        self._callback()

    def set_cb(self, callback):
        self._callback = callback

    def get_val(self):
        """
        Function to read the data buffer
        """
        return self._buf

    def set_data_format(self, format_string):
        """
        Set data transformation format from war bytes.
        format_string must constain in this order:
          - a character describing the byte order (optional)
            * '<' : litle-endian
            * '>' : big-endian
          - a character describing the data format (optional)
            * 'B' : unsigned 8-bit values
            * 'b' : signed 8-bit values
            * 'H' : unsigned 16-bit values
            * 'h' : signed 16-bit values
            * 'I' : unsigned 32-bit values
            * 'i' : signed 32-bit values
          Examples: '>H', '<', 'I'
        """

        if len(format_string) == 2:
            data_format = format_string[1]
            byte_order  = format_string[0]
        else:
            if format_string[0].isalpha():
                data_format = format_string[0]
            else:
                byte_order = format_string[0]

        if 'data_format' in locals():
            if data_format == 'B' or data_format == 'b':      # uint8, int8
                self._data_format = data_format
                self._data_size = 1
            if data_format == 'H' or  data_format == 'h':     # uint16, int16
                self._data_format = data_format
                self._data_size = 2
            elif data_format == 'I' or data_format == 'i':    # uint32, int32
                self._data_format = data_format
                self._data_size = 4
            else:
                print("Data format not supported: \"%s\"" % data_format)
        
        if 'byte_order' in locals():
            if byte_order == '<' or byte_order == '>':        # le, be
                self._data_byte_order = byte_order
            else:
                print("Data byte order not supported: \"%s\"" % byte_order)

# Local server class
class LocalServer(pyrogue.Root):

    def __init__(self, ip_addr, config_file, server_mode, group_name, epics_prefix):

        try:       
            pyrogue.Root.__init__(self, name='AMCc', description='AMC Carrier')

            # File writer for streaming interfaces
            stm_data_writer = pyrogue.utilities.fileio.StreamWriter(name='streamDataWriter')
            self.add(stm_data_writer)

            # Instantiate Fpga top level
            fpga = FpgaTopLevel(ipAddr=ip_addr)

            # Add devices     
            self.add(fpga)

            # Add data streams (0-7) to file channels (0-7)
            for i in range(8):
                pyrogue.streamConnect(fpga.stream.application(0x80 + i),
                                      stm_data_writer.getChannel(i))
            
            # Set global timeout
            self.setTimeout(timeout=1)
            
            # Run control for streaming interfaces
            self.add(pyrogue.RunControl(
                name        = 'streamRunControl',
                description = 'Run controller',
                cmd         = fpga.SwDaqMuxTrig,
                rates       = {
                                1:  '1 Hz', 
                                10: '10 Hz', 
                                30: '30 Hz'
                               }))

            # Devices used only with an EPICS server
            if epics_prefix:
                # Add data streams (0-7) to local variables so they are expose as PVs
                buf = []
                for i in range(8):
                    buf.append(DataBuffer(2*1024*1024)) # 2MB buffers
                    pyrogue.streamTap(fpga.stream.application(0x80 + i), buf[i])
                    local_var = pyrogue.LocalVariable(
                        name        = 'Stream%d' % i,
                        description = 'Stream %d' % i,
                        mode        = 'RO', 
                        value       =  0,
                        localGet    =  buf[i].get_val, 
                        update      =  False,
                        hidden      =  True)

                    self.add(local_vafr)
                    buf[i].set_cb(local_var.updated)

            # lcaPut limits the maximun lenght of a string to 40 chars, as defined
            # in the EPICS R3.14 CA reference manual. This won't allowed to use the
            # command 'readConfig' with a long file path, which is usually the case.
            # This function is a workaround to that problem. Fomr matlab one can 
            # just call this function without arguments an the function readConfig 
            # will be called with a predefined file passed during startup
            # However, it can be usefull also win the GUI, so it is always added.
            self.config_file = config_file
            self.add(pyrogue.LocalCommand(  
                name        = 'setDefaults', 
                description = 'Set default configuration', 
                function    = self.set_defaults_cmd))

            # Start the root
            if group_name:
                # Start with Pyro4 server
                host_name = get_host_name()
                print("Starting rogue server with Pyro using group name \"%s\"" % group_name)
                self.start(pyroGroup=group_name, pyroHost=host_name, pyroNs=None)
            else:
                # Start without Pyro4 server
                print("Starting rogue server")
                self.start()

            self.readAll()

        except KeyboardInterrupt:
            print("Killing server creation...")
            super(LocalServer, self).stop()
            exit()
        
        # Show image build information
        try:
            print("")
            print("FPGA image build information:")
            print("===================================")
            print("BuildStamp              : %s" % \
                self.FpgaTopLevel.AmcCarrierCore.AxiVersion.BuildStamp.get())
            print("FPGA Version            : 0x%x" % \
                self.FpgaTopLevel.AmcCarrierCore.AxiVersion.FpgaVersion.get())
            print("Git hash                : 0x%x" % \
                self.FpgaTopLevel.AmcCarrierCore.AxiVersion.GitHash.get())
        except AttributeError as attr_error: 
            print("Attibute error: %s" % attr_error)
        print("")

        # Start the EPICS server
        if epics_prefix:
            print("Starting EPICS server using prefix \"%s\"" % epics_prefix)
            self.epics = pyrogue.epics.EpicsCaServer(base=epics_prefix, root=self)
            self.epics.start()

        # If no in server Mode, start the GUI
        if not server_mode:
            create_gui(self)
        else:
            # Stop the server when Crtl+C is pressed
            try:
                # Wait for Ctrl+C
                while True:
                    time.sleep(1)           
            except KeyboardInterrupt:
                pass

    # Function for setting a default configuration. 
    def set_defaults_cmd(self):
        # Check if a default configuration file has been defined
        if not self.config_file:
            print('No default configuration file was specified...')
            return

        print('Setting defaults from file %s' % self.config_file)
        self.readConfig(self.config_file)

    def stop(self):
        print("Stopping servers...")
        if hasattr(self, 'epics'):
            print("Stopping EPICS server...")
            self.epics.stop()
        super(LocalServer, self).stop()

# Main body
def main():
    ip_addr      = ""
    group_name   = ""
    epics_prefix = ""
    config_file  = ""
    server_mode  = False

    # Read Arguments
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 
            "ha:sp:e:d:", 
            ["help", "addr=", "server", "pyro=", "epics=", "defaults="])
    except getopt.GetoptError:
        usage(sys.argv[0])
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(sys.argv[0])
            sys.exit()
        elif opt in ("-a", "--addr"):       # IP Address
            ip_addr = arg
        elif opt in ("-s", "--server"):     # Server mode
            server_mode = True
        elif opt in ("-p", "--pyro"):       # Pyro group name
            group_name = arg
        elif opt in ("-e", "--epics"):      # EPICS prefix
            epics_prefix = arg
        elif opt in ("-d", "--defaults"):   # Default configuration file
            config_file = arg

    try:
        socket.inet_aton(ip_addr)
    except socket.error:
        exit_message("ERROR: Invalid IP Address.")

    print("")
    print("Trying to ping the FPGA...")
    try:
        dev_null = open(os.devnull, 'w')
        subprocess.check_call(["ping", "-c2", ip_addr], stdout=dev_null, stderr=dev_null)
        print("    FPGA is online")
        print("")
    except subprocess.CalledProcessError:
        exit_message("    ERROR: FPGA can't be reached!")

    if server_mode and not (group_name or epics_prefix):
        exit_message("    ERROR: Can not start in server mode without Pyro or EPICS server")

    # Start pyRogue server
    server = LocalServer(   
        ip_addr      = ip_addr, 
        config_file  = config_file, 
        server_mode  = server_mode, 
        group_name   = group_name, 
        epics_prefix = epics_prefix)
    
    # Stop server
    server.stop()        
        
    print("")

if __name__ == "__main__":
    main()
