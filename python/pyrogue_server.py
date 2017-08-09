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

from FpgaTopLevel import FpgaTopLevel

# Print the usage message
def usage(name):
    print("Usage: %s -a|--addr IP_address [-s|--server] \
        [-g|--group group_name] [-h|--help]" % name)
    print("    -h||--help                : show this message")
    print("    -a|--addr IP_address      : FPGA IP address")
    print("    -s|--server               : Start only the Pyro and EPICS servers (without GUI)")
    print("    -g|--group group_name     : Pyro4 group name. Default = \"pyrogue_test\"")
    print("    -e|--epics prefix         : EPICS PV name prefix. Default = \"pyrogue_test\"")
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

# Local server class
class LocalServer(pyrogue.Root):

    def __init__(self, IpAddr, ServerMode, GroupName, EpicsPrefix):

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

            # Start the root
            if ServerMode:
                HostName = GetHostName()
                print("Starting rogue server with Pyro using group name \"%s\"" % GroupName)
                self.start(pyroGroup=GroupName, pyroHost=HostName, pyroNs=None)
            else:
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

        # If no in server Mode, start the GUI
        if not ServerMode:
            CreateGui(self)
        else:
            # Create EPICS server
            print("Starting EPICS server using prefix \"%s\"" % EpicsPrefix)
            self.epics = pyrogue.epics.EpicsCaServer(base=EpicsPrefix, root=self)
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
        super(LocalServer, self).stop()

# Main body
def main():

    IpAddr      = ""
    GroupName   = "pyrogue_test"
    EpicsPrefix = "pyrogue_test"
    ServerMode  = False

    # Read Arguments
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "ha:sg:e:", ["help", "addr=", "server", "group=", "epics="])
    except getopt.GetoptError:
        usage(sys.argv[0])
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(sys.argv[0])
            sys.exit()
        elif opt in ("-a", "--addr"):        # IP Address
            IpAddr = arg
        elif opt in ("-s", "--server"):      # Server mode
            ServerMode = True
        elif opt in ("-g", "--group"):       # Group name
            GroupName = arg
        elif opt in ("-e", "--epics"):       # EPICS prefix
            EpicsPrefix = arg


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

    # Start pyRogue server
    server = LocalServer(IpAddr, ServerMode, GroupName, EpicsPrefix)
    
    # Stop server
    server.stop()        
        
    print("")

if __name__ == "__main__":
    main(sys.argv[1:])
