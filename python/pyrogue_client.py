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
import subprocess

import pyrogue
import pyrogue.protocols
import pyrogue.utilities.fileio
import PyQt4.QtGui
import pyrogue.gui

# Print the usage message
def usage(name):
    print("Usage: %s [-g|--group group_name] [-h|--help]" % name)
    print("    -h||--help                : show this message")
    print("    -g|--group group_name     : Pyro4 group name. Default = \"pyrogue_test\"")
    print("")

# Cretae gui interface
def CreateGui(root):
    # Create GUI
    AppTop = PyQt4.QtGui.QApplication(sys.argv)
    GuiTop = pyrogue.gui.GuiTop(group='GuiTop')
    GuiTop.resize(800, 1000)
    GuiTop.addTree(root)
    
    print("Starting GUI...\n")
    
    # Run GUI
    AppTop.exec_()

    print("GUI was closed...")

# Get the hostname of this PC
def GetHostName():
    return subprocess.check_output("hostname").strip().decode("utf-8")

# Remote client class
class RemoteClient(pyrogue.PyroRoot):
    def __init__(self, GroupName):
        HostName = GetHostName()
        try:
            print("Creating client on %s..." % HostName)
            self.client = pyrogue.PyroClient(group=GroupName, host=HostName)
        except pyrogue.NodeError as NE:
            print("Error during client creation: %s" % NE)
        else:
            try:
                print("Reading root from remote server...")
                self = self.client.getRoot('AMCc')
            except pyrogue.NodeError as NE:
                print("Error reading the root from the server: %s" % NE)
                self.client.stop()
            else:
                CreateGui(self)

    def __del__(self):
        try:
            self.client.stop()
        except Exception as e:
            print("Unexpected exception caught while destroying the RemoteClient object: %s" % e)

# Main body
def main():

    GroupName = "pyrogue_test"

    # Read Arguments
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "hg:", ["help", "group="])
    except getopt.GetoptError:
        usage(sys.argv[0])
        sys.exit()

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(sys.argv[0])
            sys.exit()
        elif opt in ("-g", "--group"):       # Group name
            GroupName = arg
    
    # Start client
    client = RemoteClient(GroupName)

    # Stop client
    del client
    
    print("")

if __name__ == "__main__":
    main()
