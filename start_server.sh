#!/usr/bin/env bash
#-----------------------------------------------------------------------------
# Title      : PyRogue Server Startup Script
#-----------------------------------------------------------------------------
# File       : start_server.sh
# Created    : 2017-06-20
#-----------------------------------------------------------------------------
# Description:
# Bash script wrapper to start a PyRogue Server
#-----------------------------------------------------------------------------
# This file is part of the pyrogue-control-server software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# File name definitions
SCRIPT_NAME=$0
TOP=$(dirname -- "$(readlink -f $0)")
PYTHON_SCRIPT_NAME=$TOP/python/pyrogue_server.py
SETUP_SCRIPTS=$TOP/setup*.sh

# Usage message
usage() {
    echo ""
    echo "Start a PyRogue server to communicate with an FPGA."
    echo "This startup bash script set the enviroinment and calls the python script $PYTHON_SCRIPT_NAME"
    echo ""
    echo "Usage: $SCRIPT_NAME -t|--tar <pyrogue.tar.gz> [-h|--help] {extra arguments for $PYTHON_SCRIPT_NAME}"
    echo "    -t|--tar <pyrogue.tar.gz> : tarball file with pyrogue definitions."
    echo "    -h|--help                 : Show this message"
    echo ""
    echo "All other arguments are passed directly to $PYTHON_SCRIPT_NAME which usage is:"
    echo ""
    $PYTHON_SCRIPT_NAME -h
    exit
}

# Check for arguments
ARGS=""
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        -t|--tar)
            # Read the tarball file argument
            TAR_FILE="$2"
            shift
            ;;
        -h|--help)
            # Capture the help argument
            usage
            ;;
        *)
            # All other arguments are passed to the python script
            ARGS="$ARGS $1"
            #shift
            ;;
    esac
    shift
done

echo ""

# The tarball is required
if [ ! -f "$TAR_FILE" ]
then
    echo "Tar file not found!"
    exit
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

# Setup the environment
echo ""
echo "Setting the enviroment..."
for f in $SETUP_SCRIPTS; do
	[ -e "$f" ] && echo "Sourcing $f..." && source $f
done
export PYTHONPATH=$PYTHONPATH:$DIR/python

# Start the server
echo ""
echo "Starting the server..."
CMD="$PYTHON_SCRIPT_NAME $ARGS"
echo $CMD
$CMD
