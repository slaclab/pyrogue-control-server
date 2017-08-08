#!/usr/bin/env bash
#-----------------------------------------------------------------------------
# Title      : PyRogue Server Startup Script
#-----------------------------------------------------------------------------
# File       : start_epics.sh
# Created    : 2017-07-07
#-----------------------------------------------------------------------------
# Description:
# Bash script wrapper to start a PyRogue EPICS Server
#-----------------------------------------------------------------------------
# This file is part of the pyrogue-control-server software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

SCRIPT_NAME=$0

usage() {
    echo ""
    echo "Start a PyRogue server to communicate with an FPGA."
    echo ""
    echo "usage: $SCRIPT_NAME -t <pyrogue.tar.gz> -a <ip_addr> [-s] [-g group_name] [-h]"
    echo "    -h                  : Show this message"
    echo "    -t <pyrogue.tar.gz> : tarball file with pyrogue definitions."
    echo "    -a <ip_addr>        : target IP address."
    echo "    -p <epics_prefix>   : EPICS PV name prefix (default \"pyrogue_test\")."
    echo "    -d <config_file>    : Default configuration file (optional)"
    echo ""
    exit
}

ARGS=""

while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        -a)
            ARGS="-a $2"
            shift
            ;;
        -t)
            TAR_FILE="$2"
            shift
            ;;
        -p)
            ARGS="$ARGS -p $2"
            shift
            ;;
        -d)
            ARGS="$ARGS -d $2"
            shift
            ;;
        -h)
            usage
            ;;
        *)
            echo "Uknown option"
            usage
            ;;
    esac
    shift
done

echo ""

# The tarball is required
if [ ! -f "$TAR_FILE" ]
then
    echo "Tar file not found!"
    usage
fi

# Untar the pyrogue definitions
TEMP_DIR=/tmp/$USER/pyrogue
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR
echo "Untaring pyrogue tarball into $TEMP_DIR"
tar -zxf  $TAR_FILE -C $TEMP_DIR

# Get the pyrogue directory path
PROJ=$(ls $TEMP_DIR)
DIR=$TEMP_DIR/$PROJ
echo "Project name = $PROJ"
echo "PyRogue directory = $DIR"

# Setup the enviroment 
echo "Setting the enviroment..."
source setup_epics.sh
source setup_rogue.sh
export PYTHONPATH=$PYTHONPATH:$DIR/python

# Start the server
echo "Starting the server..."
CMD="python/pyrogue_epics_server.py $ARGS"
echo $CMD
$CMD
