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
import pyrogue.utilities.fileio
import PyQt4.QtGui
import pyrogue.gui
import pyrogue.epics

from FpgaTopLevel import *

# Print the usage message
def usage(name):
    print("Usage: %s -a|--addr IP_address [-s|--server] [-g|--group group_name] [-h|--help]" % name)
    print("    -h||--help                : show this message")
    print("    -a|--addr IP_address      : FPGA IP address")
    print("    -s|--server               : Start only the Pyro and EPICS servers (without GUI)")
    print("    -g|--group group_name     : Pyro4 group name. Default = \"pyrogue_test\"")
    print("    -e|--epics prefix         : EPICS PV name prefix. Default = \"pyrogue_test\"")
    print("")

# Cretae gui interface
def createGui(root):
    appTop = PyQt4.QtGui.QApplication(sys.argv)
    guiTop = pyrogue.gui.GuiTop(group='GuiTop')
    guiTop.resize(800, 1000)
    guiTop.addTree(root)
    print("Starting GUI...\n");

    try:
        appTop.exec_()
    except KeyboardInterrupt:
        # Catch keyboard interrupts while the GUI was open
        pass

    print("GUI was closed...")

# Exit with a error message
def exitMessage(message):
    print(message)
    print("")
    exit()

# Get the hostname of this PC
def getHostName():
    return subprocess.check_output("hostname").strip().decode("utf-8")

# Local server class
class localServer(pyrogue.Root):

    def __init__(self, ipAddr, serverMode, groupName, epicsPrefix):

        try:       
            pyrogue.Root.__init__(self, name='AMCc', description='AMC Carrier')

            # File writer for streaming interfaces
            stmDataWriter = pyrogue.utilities.fileio.StreamWriter(name='streamDataWriter')
            self.add(stmDataWriter)

            # Instantiate Fpga top level
            fpga = FpgaTopLevel(ipAddr=ipAddr)

            # Add devices     
            self.add(fpga)

            # Add data streams (0-7) to file channels (0-7)
            for i in range(8):
                pyrogue.streamConnect(fpga.stream.application(0x80 + i ), stmDataWriter.getChannel(i))
               
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

            # Start the root
            if serverMode:
                hostName = getHostName()
                print("Starting rogue server with Pyro using group name \"%s\"" % groupName)
                self.start(pyroGroup=groupName, pyroHost=hostName, pyroNs=None)
            else:
                print("Starting rogue server")
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
            print("BuildStamp              : %s" % self.FpgaTopLevel.AmcCarrierCore.AxiVersion.BuildStamp.get())
            print("FPGA Version            : 0x%x" % self.FpgaTopLevel.AmcCarrierCore.AxiVersion.FpgaVersion.get())
            print("Git hash                : 0x%x" % self.FpgaTopLevel.AmcCarrierCore.AxiVersion.GitHash.get())
        except AttributeError as ae: 
            print("Attibute error: %s" % ae)
        except Exception as e:
            print("Unexpected exception caught while reading build information: %s" % e)
        print("")

        # If no in server Mode, start the GUI
        if not serverMode:
            createGui(self)
        else:
            # Create EPICS server
            print("Starting EPICS server using prefix \"%s\"" % epicsPrefix)
            self.epics = pyrogue.epics.EpicsCaServer(base=epicsPrefix, root=self)
            self.epics.start()

            # Stop the server when Crtl+C is pressed
            try:
                # Wait for Ctrl+C
                while True:
                    time.sleep(1)           
            except KeyboardInterrupt:
                pass

    def stop(self):
        print("Stopping servers...")
        if hasattr(self, 'epics'):
            print("Stopping EPICS server...")
            self.epics.stop()
        super().stop()

# Main body
def main(argv):

    ipAddr      = ""
    groupName   = "pyrogue_test"
    epicsPrefix = "pyrogue_test"
    serverMode  = False

    # Read Arguments
    try:
        opts, args = getopt.getopt(argv,"ha:sg:e:",["help", "addr=", "server", "group=", "epics="])
    except getopt.GetoptError:
        usage(sys.argv[0])
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h","--help"):
            usage(sys.argv[0])
            sys.exit()
        elif opt in ("-a","--addr"):        # IP Address
            ipAddr = arg
        elif opt in ("-s","--server"):      # Server mode
            serverMode = True
        elif opt in ("-g","--group"):       # Group name
            groupName = arg
        elif opt in ("-e","--epics"):       # EPICS prefix
            epicsPrefix = arg


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
    server = localServer(ipAddr, serverMode, groupName, epicsPrefix)
    
    # Stop server
    server.stop()        
        
    print("")

if __name__ == "__main__":
    main(sys.argv[1:])
