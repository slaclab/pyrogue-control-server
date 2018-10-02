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
from packaging import version
from pathlib import Path

import pyrogue
import pyrogue.utilities.fileio
import rogue.interfaces.stream

# Print the usage message
def usage(name):
    print("Usage: {} -a|--addr IP_address [-d|--defaults config_file]".format(name),\
        " [-s|--server] [-p|--pyro group_name] [-e|--epics prefix]",\
        " [-n|--nopoll] [-b|--stream-size byte_size] [-f|--stream-type data_type]",\
        " [-c|--commType comm_type] [-l|--slot slot_number] [-h|--help]")
    print("    -h|--help                  : Show this message")
    print("    -a|--addr IP_address       : FPGA IP address")
    print("    -d|--defaults config_file  : Default configuration file")
    print("    -p|--pyro group_name       : Start a Pyro4 server with",\
        "group name \"group_name\"")
    print("    -e|--epics prefix          : Start an EPICS server with",\
        "PV name prefix \"prefix\"")
    print("    -s|--server                : Server mode, without staring",\
        "a GUI (Must be used with -p and/or -e)")
    print("    -n|--nopoll                : Disable all polling")
    print("    -c|--commType comm_type    : Communication type with the FPGA",\
        "(default to \"eth-rssi-non-interleaved\"")
    print("    -l|--pcie-rssi-link index  : PCIe RSSI link (only needed with"\
        "PCIe). Supported values are 0 to 5")
    print("    -b|--stream-size data_size : Expose the stream data as EPICS",\
        "PVs. Only the first \"data_size\" points will be exposed.",\
        "(Must be used with -e)")
    print("    -f|--stream-type data_type : Stream data type (UInt16, Int16,",\
        "UInt32 or Int32). Default is UInt16. (Must be used with -e and -b)")
    print("    -u|--dump-pvs file_name    : Dump the PV list to \"file_name\".",\
        "(Must be used with -e)")
    print("")
    print("Examples:")
    print("    {} -a IP_address                            :".format(name),\
        " Start a local rogue server, with GUI, without Pyro nor EPICS servers")
    print("    {} -a IP_address -e prefix                  :".format(name),\
        " Start a local rogue server, with GUI, with EPICS server")
    print("    {} -a IP_address -e prefix -p group_name -s :".format(name),\
        " Start a local rogure server, without GUI, with Pyro and EPICS servers")
    print("")

# Cretae gui interface
def create_gui(root):
    app_top = pyrogue.gui.application(sys.argv)
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

        # Supported data format and byte order
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
        self._buf = struct.unpack('{}{}{}'.format((self._data_byte_order, \
            (len(data)//self._data_size), self._data_format), data))
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
        return '{}{}'.format(self._data_byte_order, self._data_format)

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
        polling_en, comm_type, pcie_rssi_link, stream_pv_size, stream_pv_type,\
        pv_dump_file):

        try:
            pyrogue.Root.__init__(self, name='AMCc', description='AMC Carrier')

            # File writer for streaming interfaces
            stm_data_writer = pyrogue.utilities.fileio.StreamWriter(name='streamDataWriter')
            self.add(stm_data_writer)

            # Instantiate Fpga top level
            # fpga = FpgaTopLevel(ipAddr=ip_addr)
            fpga = FpgaTopLevel(ipAddr=ip_addr,
                commType=comm_type,
                pcieRssiLink=pcie_rssi_link)

            # Add devices
            self.add(fpga)

            # Add data streams (0-7) to file channels (0-7)
            for i in range(8):
                pyrogue.streamConnect(fpga.stream.application(0x80 + i),
                 stm_data_writer.getChannel(i))
                pyrogue.streamConnect(fpga.stream.application(0xC0 + i),
                 stm_data_writer.getChannel(8+i))

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
            if epics_prefix and stream_pv_size:
                if use_pcas:

                    print("Enabling stream data on PVs (buffer size = {} points, data type = {})"\
                        .format(stream_pv_size,stream_pv_type))

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
                            name='Stream{}'.format(i),
                            description='Stream {}'.format(i),
                            mode='RO',
                            value=0,
                            localGet=data_buffer.read,
                            update=False,
                            hidden=True)

                        # Set the buffer callback to update the variable
                        data_buffer.set_callback(stream_var.updated)

                        # Variable to set the data format
                        data_format_var = pyrogue.LocalVariable(
                            name='StreamDataFormat{}'.format(i),
                            description='Type of data being unpacked',
                            mode='RW',
                            value=0,
                            enum={i:j for i,j in enumerate(data_buffer.get_data_format_list())},
                            localSet=data_buffer.set_data_format,
                            localGet=data_buffer.get_data_format,
                            hidden=True)

                        # Variable to set the data byte order
                        byte_order_var = pyrogue.LocalVariable(
                            name='StreamDataByteOrder{}'.format(i),
                            description='Byte order of data being unpacked',
                            mode='RW',
                            value=0,
                            enum={i:j for i,j in enumerate(data_buffer.get_data_byte_order_list())},
                            localSet=data_buffer.set_data_byte_order,
                            localGet=data_buffer.get_data_byte_order,
                            hidden=True)

                        # Variable to read the data format string
                        format_string_var = pyrogue.LocalVariable(
                            name='StreamDataFormatString{}'.format(i),
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
                print("Starting rogue server with Pyro using group name \"{}\"".format(group_name))
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
            print("BuildStamp              : {}"\
                .format(self.FpgaTopLevel.AmcCarrierCore.AxiVersion.BuildStamp.get()))
            print("FPGA Version            : 0x{:x}"\
                .format(self.FpgaTopLevel.AmcCarrierCore.AxiVersion.FpgaVersion.get()))
            print("Git hash                : 0x{:x}"\
                .format(self.FpgaTopLevel.AmcCarrierCore.AxiVersion.GitHash.get()))
        except AttributeError as attr_error:
            print("Attibute error: {}".format(attr_error))
        print("")

        # Start the EPICS server
        if epics_prefix:
            print("Starting EPICS server using prefix \"{}\"".format(epics_prefix))

            # Choose the appropiate epics module:
            if use_pcas:
                self.epics = pyrogue.epics.EpicsCaServer(base=epics_prefix, root=self)
            else:
                self.epics = pyrogue.protocols.epics.EpicsCaServer(base=epics_prefix, root=self)

                # PVs for stream data, used on GDD-based EPICS server
                if stream_pv_size:

                    print("Enabling stream data on PVs (buffer size = {} points, data type = {})"\
                        .format(stream_pv_size,stream_pv_type))

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

            # Dump the PV list to the especified file
            if pv_dump_file:
                try:
                    # Try to open the output file
                    f = open(pv_dump_file, "w")
                except IOError:
                    print("Could not open the PV dump file \"{}\"".format(pv_dump_file))
                else:
                    with f:
                        print("Dumping PV list to \"{}\"...".format(pv_dump_file))
                        try:
                            try:
                                # Redirect the stdout to the output file momentarily
                                original_stdout, sys.stdout = sys.stdout, f
                                self.epics.dump()
                            finally:
                                sys.stdout = original_stdout

                            print("Done!")
                        except:
                            # Capture error from epics.dump() if any
                            print("Errors were found during epics.dump()")

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

        print('Setting defaults from file {}'.format(self.config_file))
        self.ReadConfig(self.config_file)

    def stop(self):
        print("Stopping servers...")
        if hasattr(self, 'epics'):
            print("Stopping EPICS server...")
            self.epics.stop()
        super(LocalServer, self).stop()

def setupPcieCard(open, link, ip_addr=""):

    # Import PCIe related modules
    import rogue.hardware.axi
    import SmurfKcu1500RssiOffload as smurf

    # Build the device
    pcie = pyrogue.Root(name='pcie',description='')
    memMap = rogue.hardware.axi.AxiMemMap('/dev/datadev_0')
    pcie.add(smurf.Core(memBase=memMap))
    pcie.start(pollEn='False',initRead='True')

    # Read the bypass RSSI mask
    mask = pcie.Core.EthLane[0].EthConfig.BypRssi.get()

    if open:
        print("Opening PCIe RSSI link {}".format(link))

        # Clear the RSSI bypass bit
        mask &= ~(1<<link)

        # Setup udp client IP address and port number
        if ip_addr:
            pcie.Core.EthLane[0].UdpClient[link].ClientRemoteIp.set(ip_addr)
        pcie.Core.EthLane[0].UdpClient[link].ClientRemotePort.set(8198)
    else:
        print("Closing PCIe RSSI link {}".format(link))

        # Set the RSSI bypass bit
        mask |= (1<<link)

        # Setup udp client port number
        pcie.Core.EthLane[0].UdpClient[link].ClientRemotePort.set(8192)

    # Set the bypass RSSi mask
    pcie.Core.EthLane[0].EthConfig.BypRssi.set(mask)

    # Set the Open and close connection registers
    pcie.Core.EthLane[0].RssiClient[link].CloseConn.set(int(not open))
    pcie.Core.EthLane[0].RssiClient[link].OpenConn.set(int(open))
    pcie.Core.EthLane[0].RssiClient[link].HeaderChksumEn.set(1)

    # Printt register status after setting them
    print("PCIe register status:")
    print("EthConfig.BypRssi = 0x{:02X}".format(
        pcie.Core.EthLane[0].EthConfig.BypRssi.get()))
    print("UdpClient[{}].ClientRemoteIp = {}".format(link,
        pcie.Core.EthLane[0].UdpClient[link].ClientRemoteIp.get()))
    print("UdpClient[{}].ClientRemotePort = {}".format(link,
        pcie.Core.EthLane[0].UdpClient[link].ClientRemotePort.get()))
    print("RssiClient[{}].CloseConn = {}".format(link,
        pcie.Core.EthLane[0].RssiClient[link].CloseConn.get()))
    print("RssiClient[{}].OpenConn = {}".format(link,
        pcie.Core.EthLane[0].RssiClient[link].OpenConn.get()))
    print("")

    # Close device
    pcie.stop()

# Main body
if __name__ == "__main__":
    ip_addr = ""
    group_name = ""
    epics_prefix = ""
    config_file = ""
    server_mode = False
    polling_en = True
    stream_pv_size = 0
    stream_pv_type = "UInt16"
    stream_pv_valid_types = ["UInt16", "Int16", "UInt32", "Int32"]
    comm_type = "eth-rssi-non-interleaved";
    comm_type_valid_types = ["eth-rssi-non-interleaved", "eth-rssi-interleaved", "pcie-rssi-interleaved"]
    pcie_rssi_link=0
    pv_dump_file= ""
    pcie_dev=Path("/dev/datadev_0")

    # Read Arguments
    try:
        opts, _ = getopt.getopt(sys.argv[1:],
            "ha:sp:e:d:nb:f:c:l:u:",
            ["help", "addr=", "server", "pyro=", "epics=", "defaults=", "nopoll",
            "stream-size=", "stream-type=", "commType=", "pcie-rssi-link=", "dump-pvs="])
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
                print("Invalid data type. Using {} instead".format(stream_pv_type))
        elif opt in ("-d", "--defaults"):   # Default configuration file
            config_file = arg
        elif opt in ("-c", "--commType"):   # Communication type
            if arg in comm_type_valid_types:
                comm_type = arg
            else:
                print("Invalid communication type. Valid choises are:")
                for c in comm_type_valid_types:
                    print("  - \"{}\"".format(c))
                exit_message("ERROR: Invalid communication type")
        elif opt in ("-l", "--pcie-rssi-link"):       # PCIe RSSI Link
            pcie_rssi_link = int(arg)
        elif opt in ("-u", "--dump-pvs"):   # Dump PV file
            pv_dump_file = arg

    # Verify if IP address is valid
    if ip_addr:
        try:
            socket.inet_pton(socket.AF_INET, ip_addr)
        except socket.error:
            exit_message("ERROR: Invalid IP Address.")

    # Check connection with the board if using eth communication
    if "eth-" in comm_type:
        if not ip_addr:
            exit_message("ERROR: Must specify an IP address for ethernet base communication devices.")

        print("")
        print("Trying to ping the FPGA...")
        try:
           dev_null = open(os.devnull, 'w')
           subprocess.check_call(["ping", "-c2", ip_addr], stdout=dev_null, stderr=dev_null)
           print("    FPGA is online")
           print("")
        except subprocess.CalledProcessError:
           exit_message("    ERROR: FPGA can't be reached!")

        # If the PCIe device exist, and we are using ETH communication, disable it.
        if pcie_dev.exists():
            setupPcieCard(open=False, link=pcie_rssi_link)

    elif "pcie-" in comm_type:

        # Verify is PCIe device exists
        if not pcie_dev.exists():
            exit_message("ERROR: PCIe device {} does not exist.".format(pcie_dev))

        # Verify if RSSI link is valid
        if pcie_rssi_link in range(0, 6):
            setupPcieCard(open=True, link=pcie_rssi_link, ip_addr=ip_addr)
        else:
            exit_message("ERROR: Invalid slot number. Must be between 2 and 7")

    if server_mode and not (group_name or epics_prefix):
        exit_message("    ERROR: Can not start in server mode without Pyro or EPICS server")

    # Try to import the FpgaTopLevel defintion
    try:
        from FpgaTopLevel import FpgaTopLevel
    except ImportError as ie:
        print("Error importing FpgaTopLevel: {}".format(ie))
        exit()

    # If EPICS server is enable, import the epics module
    if epics_prefix:
        # Choose the appropiate epics module:
        #  - until version 2.6.0 rogue uses PCASpy
        #  - later versions use GDD
        use_pcas = True
        try:
            ver = pyrogue.__version__
            if (version.parse(ver) > version.parse('2.6.0')):
                use_pcas = False
        except AttributeError:
            pass

        if use_pcas:
            print("Using PCAS-based EPICS server")
            import pyrogue.epics
        else:
            print("Using GDD-based EPICS server")
            import pyrogue.protocols.epics

    # Import the QT and gui modules if not in server mode
    if not server_mode:
        import pyrogue.gui

    # Start pyRogue server
    server = LocalServer(
        ip_addr=ip_addr,
        config_file=config_file,
        server_mode=server_mode,
        group_name=group_name,
        epics_prefix=epics_prefix,
        polling_en=polling_en,
        comm_type=comm_type,
        pcie_rssi_link=pcie_rssi_link,
        stream_pv_size=stream_pv_size,
        stream_pv_type=stream_pv_type,
        pv_dump_file=pv_dump_file)

    # Stop server
    server.stop()

    # Close the PCIe link before exit
    if "pcie-" in comm_type:
        setupPcieCard(open=False, link=pcie_rssi_link)

    print("")
