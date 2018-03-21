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

# Choose the appropiate epics module:
#  - until version 2.6.0 rogue uses PCASpy
#  - later versions use GDD
use_pcas = True
try:
    ver = pyrogue.__version__
    if (ver > '2.6.0'):
        use_pcas = False
except AttributeError:
    pass

if (use_pcas):
    print("Using PCAS-based EPICS server")
    import pyrogue.epics
else:
    print("Using GDD-based EPICS server")
    import pyrogue.protocols.epics

try:
    from FpgaTopLevel import FpgaTopLevel
except ImportError as ie:
    print("Error importing FpgaTopLevel: %s" % ie)
    exit()

# Print the usage message
def usage(name):
    print("Usage: %s -a|--addr IP_address [-d|--defaults config_file]" % name,\
        " [-s|--server] [-p|--pyro group_name] [-e|--epics prefix]",\
        " [-n|--nopoll] [-b|--stream-size byte_size] [-f|--stream-type data_type]",\
        " [-h|--help]")
    print("    -h||--help                 : Show this message")
    print("    -a|--addr IP_address       : FPGA IP address")
    print("    -d|--defaults config_file  : Default configuration file")
    print("    -p|--pyro group_name       : Start a Pyro4 server with",\
        "group name \"group_name\"")
    print("    -e|--epics prefix          : Start an EPICS server with",\
        "PV name prefix \"prefix\"")
    print("    -s|--server                : Server mode, without staring",\
        "a GUI (Must be used with -p and/or -e)")
    print("    -n|--nopoll                : Disable all polling")
    print("    -b|--stream-size data_size : Expose the stream data as EPICS",\
        "PVs. Only the first \"data_size\" points will be exposed.",\
        "(Must be used with -e)")
    print("    -f|--stream-type data_type : Stream data type (UInt16, Int16,",\
        "UInt32 or Int32). Default is UInt16. (Must be used with -e and -b)")
    print("")
    print("Examples:")
    print("    %s -a IP_address                            :" % name,\
        " Start a local rogue server, with GUI, without Pyro nor EPICS servers")
    print("    %s -a IP_address -e prefix                  :" % name,\
        " Start a local rogue server, with GUI, with EPICS server")
    print("    %s -a IP_address -e prefix -p group_name -s :" % name,\
        " Start a local rogure server, without GUI, with Pyro and EPICS servers")
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
    Data buffer class use to capture data comming from the stream FIFO \
    and copy it into a local buffer using a especific data format.
    """
    def __init__(self, size, data_type):
        rogue.interfaces.stream.Slave.__init__(self)
        self._buf = [0] * size

        # Supported data foramt and byte order
        self._data_format_dict = {
            'B': 'unsigned 8-bit',
            'b': 'signed 8-bit',
            'H': 'unsigned 16-bit',
            'h': 'signed 16-bit',
            'I': 'unsigned 32-bit',
            'i': 'signed 32-bit'}

        self._data_byte_order_dict = {
            '<': 'little-endian',
            '>': 'big-endian'}

        # Get data format and size from data type
        if data_type == 'UInt16':
            self._data_format = 'H'
            self._data_size = 2
        elif data_type == 'Int16':
            self._data_format = 'h'
            self._data_size = 2
        elif data_type == 'UInt32':
            self._data_format = 'I'
            self._data_size = 4
        else:
            self._data_format = 'i'
            self._data_size = 4

        # Byte order: LE
        self._data_byte_order = '<'

        # Callback function
        self._callback = lambda: None

    def _acceptFrame(self, frame):
        """
        This method is called when a stream frame is received
        """
        data = bytearray(frame.getPayload())
        frame.read(data, 0)
        self._buf = struct.unpack('%s%d%s' % (self._data_byte_order, \
            (len(data)//self._data_size), self._data_format), data)
        self._callback()

    def set_callback(self, callback):
        """
        Function to set the callback function
        """
        self._callback = callback

    def read(self):
        """
        Function to read the data buffer
        """
        return self._buf

    def get_data_format_string(self):
        """
        Function to get the current format string
        """
        return '%s%s' % (self._data_byte_order, self._data_format)

    def get_data_format_list(self):
        """
        Function to get a list of supported data formats
        """
        return list(self._data_format_dict.values())

    def get_data_byte_order_list(self):
        """
        Function to get a list of supported data byte order options
        """
        return list(self._data_byte_order_dict.values())

    def set_data_format(self, dev, var, value):
        """
        Function to set the data format
        """
        if (value < len(self._data_format_dict)):
            data_format = (list(self._data_format_dict)[value])
            if data_format == 'B' or data_format == 'b':      # uint8, int8
                self._data_format = data_format
                self._data_size = 1
            elif data_format == 'H' or  data_format == 'h':     # uint16, int16
                self._data_format = data_format
                self._data_size = 2
            elif data_format == 'I' or data_format == 'i':    # uint32, int32
                self._data_format = data_format
                self._data_size = 4

    def get_data_format(self):
        """
        Function to read the data format
        """
        return list(self._data_format_dict).index(self._data_format)

    def set_data_byte_order(self, dev, var, value):
        """
        Function to set the data byte order
        """
        if (value < len(self._data_byte_order_dict)):
            self._data_byte_order = list(self._data_byte_order_dict)[value]

    def get_data_byte_order(self):
        """
        Function to read the data byte order
        """
        return list(self._data_byte_order_dict).index(self._data_byte_order)

# Local server class
class LocalServer(pyrogue.Root):

    def __init__(self, ip_addr, config_file, server_mode, group_name, epics_prefix,\
        polling_en, stream_pv_size, stream_pv_type):

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
                name='streamRunControl',
                description='Run controller',
                cmd=fpga.SwDaqMuxTrig,
                rates={
                    1:  '1 Hz',
                    10: '10 Hz',
                    30: '30 Hz'}))

            # PVs for stream data, used on PCAS-based EPICS server
            if use_pcas:
                if epics_prefix and stream_pv_size:

                    print("Enabling stream data on PVs (buffer size = %d bytes)" % stream_pv_size)

                    # Add data streams (0-7) to local variables so they are expose as PVs
                    # Also add PVs to select the data format
                    for i in range(8):

                        # Calculate number of bytes needed on the fifo
                        if '16' in stream_pv_type:
                            fifo_size = stream_pv_size * 2
                        else:
                            fifo_size = stream_pv_size * 4

                        # Setup a FIFO tapped to the steram data and a Slave data buffer
                        # Local variables will talk to the data buffer directly.
                        stream_fifo = rogue.interfaces.stream.Fifo(0, fifo_size)
                        data_buffer = DataBuffer(size=stream_pv_size, data_type=stream_pv_type)
                        stream_fifo._setSlave(data_buffer)
                        pyrogue.streamTap(fpga.stream.application(0x80 + i), stream_fifo)

                        # Variable to read the stream data
                        stream_var = pyrogue.LocalVariable(
                            name='Stream%d' % i,
                            description='Stream %d' % i,
                            mode='RO',
                            value=0,
                            localGet=data_buffer.read,
                            update=False,
                            hidden=True)

                        # Set the buffer callback to update the variable
                        data_buffer.set_callback(stream_var.updated)

                        # Variable to set the data format
                        data_format_var = pyrogue.LocalVariable(
                            name='StreamDataFormat%d' % i,
                            description='Type of data being unpacked',
                            mode='RW',
                            value=0,
                            enum={i:j for i,j in enumerate(data_buffer.get_data_format_list())},
                            localSet=data_buffer.set_data_format,
                            localGet=data_buffer.get_data_format,
                            hidden=True)

                        # Variable to set the data byte order
                        byte_order_var = pyrogue.LocalVariable(
                            name='StreamDataByteOrder%d' % i,
                            description='Byte order of data being unpacked',
                            mode='RW',
                            value=0,
                            enum={i:j for i,j in enumerate(data_buffer.get_data_byte_order_list())},
                            localSet=data_buffer.set_data_byte_order,
                            localGet=data_buffer.get_data_byte_order,
                            hidden=True)

                        # Variable to read the data format string
                        format_string_var = pyrogue.LocalVariable(
                            name='StreamDataFormatString%d' % i,
                            description='Format string used to unpack the data',
                            mode='RO',
                            value=0,
                            localGet=data_buffer.get_data_format_string,
                            hidden=True)

                        # Add listener to update the format string readback variable
                        # when the data format or data byte order is changed
                        data_format_var.addListener(format_string_var)
                        byte_order_var.addListener(format_string_var)

                        # Add the local variable to self
                        self.add(stream_var)
                        self.add(data_format_var)
                        self.add(byte_order_var)
                        self.add(format_string_var)

            # lcaPut limits the maximun lenght of a string to 40 chars, as defined
            # in the EPICS R3.14 CA reference manual. This won't allowed to use the
            # command 'ReadConfig' with a long file path, which is usually the case.
            # This function is a workaround to that problem. Fomr matlab one can
            # just call this function without arguments an the function ReadConfig
            # will be called with a predefined file passed during startup
            # However, it can be usefull also win the GUI, so it is always added.
            self.config_file = config_file
            self.add(pyrogue.LocalCommand(
                name='setDefaults',
                description='Set default configuration',
                function=self.set_defaults_cmd))

            # Start the root
            if group_name:
                # Start with Pyro4 server
                host_name = get_host_name()
                print("Starting rogue server with Pyro using group name \"%s\"" % group_name)
                self.start(pollEn=polling_en, pyroGroup=group_name, pyroHost=host_name, pyroNs=None)
            else:
                # Start without Pyro4 server
                print("Starting rogue server")
                self.start(pollEn=polling_en)

            self.ReadAll()

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

            # Choose the appropiate epics module:
            if use_pcas:
                self.epics = pyrogue.epics.EpicsCaServer(base=epics_prefix, root=self)
            else:
                self.epics = pyrogue.protocols.epics.EpicsCaServer(base=epics_prefix, root=self)

                # PVs for stream data, used on GDD-based EPICS server
                if stream_pv_size:

                    print("Enabling stream data on PVs (buffer size = %d points, data type = %s)"\
                        % (stream_pv_size,stream_pv_type))

                    for i in range(8):
                        stream_slave = self.epics.createSlave(name="AMCc:Stream{}".format(i), maxSize=stream_pv_size, type=stream_pv_type)

                        # Calculate number of bytes needed on the fifo
                        if '16' in stream_pv_type:
                            fifo_size = stream_pv_size * 2
                        else:
                            fifo_size = stream_pv_size * 4

                        stream_fifo = rogue.interfaces.stream.Fifo(0, fifo_size)
                        stream_fifo._setSlave(stream_slave)
                        pyrogue.streamTap(fpga.stream.application(0x80+i), stream_fifo)

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
        self.ReadConfig(self.config_file)

    def stop(self):
        print("Stopping servers...")
        if hasattr(self, 'epics'):
            print("Stopping EPICS server...")
            self.epics.stop()
        super(LocalServer, self).stop()

# Main body
def main():
    ip_addr = ""
    group_name = ""
    epics_prefix = ""
    config_file = ""
    server_mode = False
    polling_en = True
    stream_pv_size = 0
    stream_pv_type = "UInt16"
    stream_pv_valid_types = ["UInt16", "Int16", "UInt32", "Int32"]

    # Read Arguments
    try:
        opts, _ = getopt.getopt(sys.argv[1:],
            "ha:sp:e:d:nb:f:",
            ["help", "addr=", "server", "pyro=", "epics=", "defaults=", "nopoll", "stream-size=", "stream-type="])
    except getopt.GetoptError:
        usage(sys.argv[0])
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(sys.argv[0])
            sys.exit()
        elif opt in ("-a", "--addr"):        # IP Address
            ip_addr = arg
        elif opt in ("-s", "--server"):      # Server mode
            server_mode = True
        elif opt in ("-p", "--pyro"):        # Pyro group name
            group_name = arg
        elif opt in ("-e", "--epics"):       # EPICS prefix
            epics_prefix = arg
        elif opt in ("-n", "--nopoll"):      # Disable all polling
            polling_en = False
        elif opt in ("-b", "--stream-size"): # Stream data size (on PVs)
            try:
                stream_pv_size = int(arg)
            except ValueError:
                exit_message("ERROR: Invalid stream PV size")
        elif opt in ("-f", "--stream-type"): # Stream data type (on PVs)
            if arg in stream_pv_valid_types:
                stream_pv_type = arg
            else:
                print("Invalid data type. Using %s instead" % stream_pv_type)
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
        ip_addr=ip_addr,
        config_file=config_file,
        server_mode=server_mode,
        group_name=group_name,
        epics_prefix=epics_prefix,
        polling_en=polling_en,
        stream_pv_size=stream_pv_size,
        stream_pv_type=stream_pv_type)

    # Stop server
    server.stop()

    print("")

if __name__ == "__main__":
    main()
