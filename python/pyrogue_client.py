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
def create_gui(root):
    # Create GUI
    app_top = PyQt4.QtGui.QApplication(sys.argv)
    gui_top = pyrogue.gui.gui_top(group='GuiTop')
    gui_top.resize(800, 1000)
    gui_top.addTree(root)
    
    print("Starting GUI...\n")
    
    # Run GUI
    app_top.exec_()

    print("GUI was closed...")

# Get the hostname of this PC
def get_host_name():
    return subprocess.check_output("hostname").strip().decode("utf-8")

# Remote client class
class RemoteClient(pyrogue.PyroRoot):
    def __init__(self, group_name):
        host_name = get_host_name()
        try:
            print("Creating client on %s..." % host_name)
            self.client = pyrogue.PyroClient(group=group_name, host=host_name)
        except pyrogue.NodeError as ne:
            print("Error during client creation: %s" % ne)
        else:
            try:
                print("Reading root from remote server...")
                self = self.client.getRoot('AMCc')
            except pyrogue.NodeError as ne:
                print("Error reading the root from the server: %s" % ne)
                self.client.stop()
            else:
                create_gui(self)

    def __del__(self):
        try:
            self.client.stop()
        except Exception as re:
            print("Error while destroying the remote client object: %s" % re)

# Main body
def main():

    group_name = "pyrogue_test"

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
            group_name = arg
    
    # Start client
    client = RemoteClient(group_name)

    # Stop client
    del client
    
    print("")

if __name__ == "__main__":
    main()
