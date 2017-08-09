#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : PyRogue Server
#-----------------------------------------------------------------------------
# File       : python/pyrogue_epics_server.py
# Created    : 2017-06-20
#-----------------------------------------------------------------------------
# Description:
# Python script to start a PyRogue EPICS Server
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
import pyrogue.epics
import pyrogue.utilities.prbs

from FpgaTopLevel import *

# Print the usage message
def usage(name):
    print("Usage: %s -a|--addr IP_address [-s|--server] [-g|--group group_name] [-d|--defaults config_file] [-h|--help]" % name)
    print("    -h||--help                : show this message")
    print("    -a|--addr IP_address      : FPGA IP address")
    print("    -e|--prefixi epics_prefix : EPICS PV name prefix. Default = \"pyrogue_test\"")
    print("    -d|--defaults config_file : Default configuration file (optional)")
    print("")

# Exit with a error message
def exitMessage(message):
    print(message)
    print("")
    exit()

class dataBuffer(rogue.interfaces.stream.Slave):
    """
    Data buffer class use to receive data from a stream interface and copies into a local buffer using a especific format
    """
    def __init__(self, size):
        rogue.interfaces.stream.Slave.__init__(self)
        print('Data buffer created')
        self._buf = [0] * size

        # Data format: uint16, le
        self._dataByteOrder = '<'        
        self._dataFormat    = 'h'
        self._dataSize      = 2
        self._callback      = lambda: None

    def _acceptFrame(self, frame):
        """
        This method is called when a stream frame is received
        """
        data = bytearray(frame.getPayload())
        frame.read(data, 0)
        self._buf = struct.unpack('%s%d%s' % (self._dataByteOrder, (len(data)//self._dataSize), self._dataFormat), data)
        self._callback()

    def setCb(self,cb):
        self._callback = cb

    def getVal(self):
        """
        Function to read the data buffer
        """
        return self._buf

    def setDataFormat(self, formatString):
        """
        Set data transformation format from war bytes.
        formatString must constain in this order:
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

        if len(formatString) == 2:
            dataFormat = formatString[1]
            byteOrder  = formatString[0]
        else:
            if formatString[0].isalpha():
                dataFormat = formatString[0]
            else:
                byteOrder = formatString[0]

        if 'dataFormat' in locals():
            if dataFormat == 'B' or dataFormat == 'b':      # uint8, int8
                self._dataFormat = dataFormat
                self._dataSize   = 1
            if dataFormat == 'H' or  dataFormat == 'h':     # uint16, int16
                self._dataFormat = dataFormat
                self._dataSize   = 2
            elif dataFormat == 'I' or dataFormat == 'i':    # uint32, int32
                self._dataFormat = dataFormat
                self._dataSize   = 4
            else:
                print("Data format not supported: \"%s\"" % dataFormat)
        
        if 'byteOrder' in locals():
            if byteOrder == '<' or byteOrder == '>':        # le, be
                self._dataByteOrder = byteOrder
            else:
                print("Data byte order not supported: \"%s\"" % byteOrder)

def testFunction():
    print('Test function called')        

# Local server class
class localServer(pyrogue.Root):

    def __init__(self, ipAddr, epicsPrefix, configFile):
        
        try:       
            pyrogue.Root.__init__(self,name='AMCc',description='AMC Carrier')

            # Instantiate Fpga top level
            fpga = FpgaTopLevel(ipAddr=ipAddr)

            # Add devices     
            self.add(fpga)

            # Add data streams (0-7) to local variables so they are expose as PVs
            buf = []
            for i in range(8):
                buf.append(dataBuffer(2*1024*1024))	# 2MB buffers
                pyrogue.streamConnect(fpga.stream.application(0x80 + i ), buf[i])
                v = pyrogue.LocalVariable(name='Stream%d' % i,
                                          description='Stream %d' % i,
                                          mode='RO', value=0,
                                          localGet=buf[i].getVal,update=False,hidden=True)
                self.add(v)
                buf[i].setCb(v.updated)

            # Set global timeout
            self.setTimeout(timeout=1)

            # lcaPut limits the maximun lenght of a string to 40 chars, as defined in the EPICS R3.14 CA reference manual.
            # This won't allowed to use the command 'readConfig' with a long file path, which is usually the case.
            # This function is a workaround to that problem. Fomr matlab one can just call this function without arguments
            # an the function readConfig will be called with a predefined file passed during startup
            self.configFile = configFile
            self.add(pyrogue.LocalCommand(name='setDefaults', description='Set default configuration', function=self.setDefaultsCmd))

            # Start the root
            self.start()
            self.readAll()

        except KeyboardInterrupt:
            print("Killing server creation...")
            super().stop()
            exit()
        
        # Show image build information
        try:
            print("")
            print("FPGA image build information:")
            print("===================================")
            print("BuildStamp              : %s"   % self.FpgaTopLevel.AmcCarrierCore.AxiVersion.BuildStamp.get())
            print("FPGA Version            : 0x%x" % self.FpgaTopLevel.AmcCarrierCore.AxiVersion.FpgaVersion.get())
            print("Git hash                : 0x%x" % self.FpgaTopLevel.AmcCarrierCore.AxiVersion.GitHash.get())
        except AttributeError as ae: 
            print("Attibute error: %s" % ae)
        except Exception as e:
            print("Unexpected exception caught while reading build information: %s" % e)
        print("")

        # Create EPICS server
        print("Starting EPICS server using prefix \"%s\"" % epicsPrefix)
        try:
            self.epics = pyrogue.epics.EpicsCaServer(base=epicsPrefix, root=self)
            self.epics.start()
            print("EPICS server started. press Crtl+C to exit")
        except:
            print("  ERROR: Couldn't start the EPICS server...")
            return

        # Stop the server when Crtl+C is pressed
        try:
            # Wait for Ctrl+C
            while True:
                time.sleep(1)           
        except KeyboardInterrupt:
            pass

    # Function for setting a default configuration. 
    def setDefaultsCmd(self):
        # Check if a default configuration file has been defined
        if not self.configFile:
            print('No default configuration file was specified...')
            return

        print('Setting defaults from file %s' % self.configFile)
        self.readConfig(self.configFile)

    def stop(self):
        print("Stopping EPICS server...")
        self.epics.stop()
        super().stop()


# Main body
def main(argv):

    ipAddr      = ""
    epicsPrefix = "pyrogue_test"
    configFile  = ''

    # Read Arguments
    try:
        opts, args = getopt.getopt(argv,"ha:p:d:",["help", "addr=", "prefix=", "defaults="])
    except getopt.GetoptError:
        usage(sys.argv[0])
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h","--help"):
            usage(sys.argv[0])
            sys.exit()
        elif opt in ("-a","--addr"):        # IP Address
            ipAddr = arg
        elif opt in ("-p","--prefix"):      # EPICS prefix
            epicsPrefix = arg
        elif opt in ("-d", "--defaults"):   # Default configuration file
            configFile = arg


    try:
        socket.inet_aton(ipAddr)
    except socket.error:
        exitMessage("ERROR: Invalid IP Address.")

    print("")
    print("Trying to ping the FPGA...")
    try:
        FNULL = open(os.devnull, 'w')
        subprocess.check_call(["ping", "-c2", ipAddr], stdout=FNULL, stderr=FNULL)
        print("    FPGA is online")
        print("")
    except subprocess.CalledProcessError:
        exitMessage("    ERROR: FPGA can't be reached!")

    # Start pyRogue server
    server = localServer(ipAddr, epicsPrefix, configFile)
    
    # Stop server
    server.stop()        
        
    print("")

if __name__ == "__main__":
    main(sys.argv[1:])
