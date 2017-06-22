#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : PyRogue Client
#-----------------------------------------------------------------------------
# File       : python/pyrogue_client.py
# Created    : 2017-06-20
#-----------------------------------------------------------------------------
# Description:
# Python script to start a PyRogue Control Client
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

import pyrogue
import pyrogue.protocols
import rogue.protocols.srp
import rogue.protocols.udp
import pyrogue.utilities.fileio
import rogue.interfaces.stream
import PyQt4.QtGui
import pyrogue.gui

# Print the usage message
def usage(name):
    print("Usage: %s [-g|--group group_name] [-h|--help]" % name)
    print("    -h||--help                : show this message")
    print("    -g|--group group_name     : Pyro4 group name. Default = \"pyrogue_test\"")
    print("")

# Cretae gui interface
def createGui(root):
    # Create GUI
    appTop = PyQt4.QtGui.QApplication(sys.argv)
    guiTop = pyrogue.gui.GuiTop(group='GuiTop')
    guiTop.resize(800, 1000)
    guiTop.addTree(root)
    
    print("Starting GUI...\n");
    
    # Run GUI
    appTop.exec_()

    print("GUI was closed...")

# Exit with a error message
def exitMessage(message):
    print(message)
    print("")
    exit()

# Get the hostname of this PC
def getHostName():
    return subprocess.check_output("hostname").strip().decode("utf-8")

# Remote client class
class remoteClient(pyrogue.PyroRoot):
    def __init__(self, groupName):
        try:
            hostName = getHostName()
            print("Creating client on %s and reading root from remtoe server" % hostName)
            self.client = pyrogue.PyroClient(groupName, host=hostName)
            self = self.client.getRoot('AMCc')
            createGui(self)
        except pyrogue.NodeError as e:
            print("Error during client creation: %s" % e) 

    def __del__(self):
        try:
            self.client.stop()
        except:
            pass

# Main body
def main(argv):

    ipAddr     = ""
    groupName  = "pyrogue_test"
    serverMode = False
    clientMode = False

    # Read Arguments
    try:
        opts, args = getopt.getopt(argv,"hg:",["help", "group="])
    except getopt.GetoptError:
        usage(sys.argv[0])
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h","--help"):
            usage(sys.argv[0])
            sys.exit()
        elif opt in ("-g","--group"):       # Group name
            groupName = arg
    
    # Start client
    client = remoteClient(groupName)

    # Stop client
    del client
    
    print("")

if __name__ == "__main__":
    main(sys.argv[1:])