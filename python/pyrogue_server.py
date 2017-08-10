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

import pyrogue
import pyrogue.protocols
import rogue.protocols.srp
import rogue.protocols.udp
import pyrogue.utilities.fileio
import rogue.interfaces.stream
import PyQt4.QtGui
import pyrogue.gui
import pyrogue.epics

from FpgaTopLevel import FpgaTopLevel

# Print the usage message
def usage(name):
    print("Usage: %s -a|--addr IP_address [-d|--defaults config_file] \
        [-s|--server] [-p|--pyro group_name] [-e|--epics prefix] [-h|--help]" \
        % name)
    print("    -h||--help                : show this message")
    print("    -a|--addr IP_address      : FPGA IP address")
    print("    -d|--defaults config_file : Default configuration file (optional)")
    print("    -p|--pyro group_name      : Start a Pyro4 server with group name \"group_name\"")
    print("    -e|--epics prefix         : Start an EPICS server with PV name prefix \"prefix\"")
    print("    -s|--server               : Server mode, without staring a GUI (Must be use with -p and/or -e)")
    print("")
    print("Examples:")
    print("    %s -a IP_address                           : \
        Start a local rogue server, with GUI, without Pyro nor EPICS servers" \
        % name)
    print("    %s -a IP_address -e prefix                 : \
        Start a local rogue server, with GUI, with EPICS server" \
        % name)
    print("    %s -a IP_address -e prefix -p group_name -s : \
        Start a local rogure server, without GUI, with Pyro and EPICS servers" \
        % name)
    print("")

# Cretae gui interface
def CreateGui(root):
    AppTop = PyQt4.QtGui.QApplication(sys.argv)
    GuiTop = pyrogue.gui.GuiTop(group='GuiTop')
    GuiTop.resize(800, 1000)
    GuiTop.addTree(root)
    print("Starting GUI...\n")

    try:
        AppTop.exec_()
    except KeyboardInterrupt:
        # Catch keyboard interrupts while the GUI was open
        pass

    print("GUI was closed...")

# Exit with a error message
def ExitMessage(message):
    print(message)
    print("")
    exit()

# Get the hostname of this PC
def GetHostName():
    return subprocess.check_output("hostname").strip().decode("utf-8")

class DataBuffer(rogue.interfaces.stream.Slave):
    """
    Data buffer class use to receive data from a stream interface and \
    copies into a local buffer using a especific format
    """
    def __init__(self, size):
        rogue.interfaces.stream.Slave.__init__(self)
        print('Data buffer created')
        self._buf = [0] * size

        # Data format: uint16, le
        self._DataByteOrder = '<'        
        self._DataFormat    = 'h'
        self._DataSize      = 2
        self._callback      = lambda: None

    def _acceptFrame(self, frame):
        """
        This method is called when a stream frame is received
        """
        data = bytearray(frame.getPayload())
        frame.read(data, 0)
        self._buf = struct.unpack('%s%d%s' % (self._DataByteOrder, \
            (len(data)//self._DataSize), self._DataFormat), data)
        self._callback()

    def SetCb(self,cb):
        self._callback = cb

    def GetVal(self):
        """
        Function to read the data buffer
        """
        return self._buf

    def SetDataFormat(self, FormatString):
        """
        Set data transformation format from war bytes.
        FormatString must constain in this order:
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

        if len(FormatString) == 2:
            DataFormat = FormatString[1]
            ByteOrder  = FormatString[0]
        else:
            if FormatString[0].isalpha():
                DataFormat = FormatString[0]
            else:
                ByteOrder = FormatString[0]

        if 'DataFormat' in locals():
            if DataFormat == 'B' or DataFormat == 'b':      # uint8, int8
                self._DataFormat = DataFormat
                self._DataSize = 1
            if DataFormat == 'H' or  DataFormat == 'h':     # uint16, int16
                self._DataFormat = DataFormat
                self._DataSize = 2
            elif DataFormat == 'I' or DataFormat == 'i':    # uint32, int32
                self._DataFormat = DataFormat
                self._DataSize = 4
            else:
                print("Data format not supported: \"%s\"" % DataFormat)
        
        if 'ByteOrder' in locals():
            if ByteOrder == '<' or ByteOrder == '>':        # le, be
                self._DataByteOrder = ByteOrder
            else:
                print("Data byte order not supported: \"%s\"" % ByteOrder)

# Local server class
class LocalServer(pyrogue.Root):

    def __init__(self, IpAddr, ConfigFile, ServerMode, GroupName, EpicsPrefix):

        try:       
            pyrogue.Root.__init__(self, name='AMCc', description='AMC Carrier')

            # File writer for streaming interfaces
            StmDataWriter = pyrogue.utilities.fileio.StreamWriter(name='streamDataWriter')
            self.add(StmDataWriter)

            # Instantiate Fpga top level
            fpga = FpgaTopLevel(ipAddr=IpAddr)

            # Add devices     
            self.add(fpga)

            # Add data streams (0-7) to file channels (0-7)
            for i in range(8):
                pyrogue.streamConnect(fpga.stream.application(0x80 + i), StmDataWriter.getChannel(i))
            
            # Set global timeout
            self.setTimeout(timeout=1)
            
            # Run control for streaming interfaces
            self.add(pyrogue.RunControl(    name        = 'streamRunControl',
                                            description = 'Run controller',
                                            cmd         = fpga.SwDaqMuxTrig,
                                            rates       = {
                                                            1:  '1 Hz', 
                                                            10: '10 Hz', 
                                                            30: '30 Hz'
                                                           }
                                        ))

            # Devices used only with an EPICS server
            if EpicsPrefix:
                # Add data streams (0-7) to local variables so they are expose as PVs
                buf = []
                for i in range(8):
                    buf.append(DataBuffer(2*1024*1024)) # 2MB buffers
                    pyrogue.streamTap(fpga.stream.application(0x80 + i), buf[i])
                    V = pyrogue.LocalVariable(  name        = 'Stream%d' % i,
                                                description = 'Stream %d' % i,
                                                mode        = 'RO', 
                                                value       =  0,
                                                localGet    =  buf[i].GetVal, 
                                                update      =  False,
                                                hidden      =  True)
                    self.add(V)
                    buf[i].SetCb(V.updated)

            # lcaPut limits the maximun lenght of a string to 40 chars, as defined
            # in the EPICS R3.14 CA reference manual. This won't allowed to use the
            # command 'readConfig' with a long file path, which is usually the case.
            # This function is a workaround to that problem. Fomr matlab one can 
            # just call this function without arguments an the function readConfig 
            # will be called with a predefined file passed during startup
            # However, it can be usefull also win the GUI, so it is always added.
            self.ConfigFile = ConfigFile
            self.add(pyrogue.LocalCommand(  name        = 'setDefaults', 
                                            description = 'Set default configuration', 
                                            function    = self.SetDefaultsCmd))

            # Start the root
            if GroupName:
                # Start with Pyro4 server
                HostName = GetHostName()
                print("Starting rogue server with Pyro using group name \"%s\"" % GroupName)
                self.start(pyroGroup=GroupName, pyroHost=HostName, pyroNs=None)
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
        except AttributeError as AE: 
            print("Attibute error: %s" % AE)
        except Exception as e:
            print("Unexpected exception caught while reading build information: %s" % e)
        print("")

        # Start the EPICS server
        if EpicsPrefix:
            print("Starting EPICS server using prefix \"%s\"" % EpicsPrefix)
            self.epics = pyrogue.epics.EpicsCaServer(base=EpicsPrefix, root=self)
            self.epics.start()

        # If no in server Mode, start the GUI
        if not ServerMode:
            CreateGui(self)
        else:
            # Stop the server when Crtl+C is pressed
            try:
                # Wait for Ctrl+C
                while True:
                    time.sleep(1)           
            except KeyboardInterrupt:
                pass

    # Function for setting a default configuration. 
    def SetDefaultsCmd(self):
        # Check if a default configuration file has been defined
        if not self.ConfigFile:
            print('No default configuration file was specified...')
            return

        print('Setting defaults from file %s' % self.ConfigFile)
        self.readConfig(self.ConfigFile)

    def stop(self):
        print("Stopping servers...")
        if hasattr(self, 'epics'):
            print("Stopping EPICS server...")
            self.epics.stop()
        super(LocalServer, self).stop()

# Main body
def main():
    IpAddr      = ""
    GroupName   = ""
    EpicsPrefix = ""
    ConfigFile  = ""
    ServerMode  = False

    # Read Arguments
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "ha:sp:e:d:", ["help", "addr=", "server", "pyro=", "epics=", "defaults="])
    except getopt.GetoptError:
        usage(sys.argv[0])
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(sys.argv[0])
            sys.exit()
        elif opt in ("-a", "--addr"):       # IP Address
            IpAddr = arg
        elif opt in ("-s", "--server"):     # Server mode
            ServerMode = True
        elif opt in ("-p", "--pyro"):       # Pyro group name
            GroupName = arg
        elif opt in ("-e", "--epics"):      # EPICS prefix
            EpicsPrefix = arg
        elif opt in ("-d", "--defaults"):   # Default configuration file
            ConfigFile = arg

    try:
        socket.inet_aton(IpAddr)
    except socket.error:
        ExitMessage("ERROR: Invalid IP Address.")

    print("")
    print("Trying to ping the FPGA...")
    try:
        DevNull = open(os.devnull, 'w')
        subprocess.check_call(["ping", "-c2", IpAddr], stdout=DevNull, stderr=DevNull)
        print("    FPGA is online")
        print("")
    except subprocess.CalledProcessError:
        ExitMessage("    ERROR: FPGA can't be reached!")

    if ServerMode and not (GroupName or EpicsPrefix):
        ExitMessage("    ERROR: Can not start in server mode without Pyro or EPICS server")

    # Start pyRogue server
    server = LocalServer(   IpAddr      = IpAddr, 
                            ConfigFile  = ConfigFile, 
                            ServerMode  = ServerMode, 
                            GroupName   = GroupName, 
                            EpicsPrefix = EpicsPrefix)
    
    # Stop server
    server.stop()        
        
    print("")

if __name__ == "__main__":
    main()
