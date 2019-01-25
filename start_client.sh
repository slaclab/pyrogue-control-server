#!/usr/bin/env bash
#-----------------------------------------------------------------------------
# Title      : PyRogue Client Startup Script
#-----------------------------------------------------------------------------
# File       : start_client.sh
# Created    : 2017-06-20
#-----------------------------------------------------------------------------
# Description:
# Bash script wrapper to start a PyRogue Client
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
TOP=$(dirname -- "$(readlink -f $0)")
PYTHON_SCRIPT_NAME=$TOP/python/pyrogue_client.py
SETUP_SCRIPTS=$TOP/setup*.sh

# Setup the environment
echo ""
echo "Setting the environment..."
for f in $SETUP_SCRIPTS; do
    [ -e "$f" ] && echo "Sourcing $f..." && source $f
done

# Usage message
usage() {
    echo ""
    echo "Start a PyRogue client to communicate with a pyrogue server runing in a remote (or local) host"
    echo "This startup bash script set the enviroinment and calls the python script $PYTHON_SCRIPT_NAME"
    echo ""
    echo "usage: $SCRIPT_NAME [-h|--help] {extra arguments for $PYTHON_SCRIPT_NAME}"
    echo "    -h                  : Show this message"
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
        -h|--help)
            # Capture the help argument
            usage
            ;;
        *)
            # All other arguemnts are passed to the pyton script
            ARGS="$ARGS $1"
            ;;
    esac
    shift
done

# Start the client
echo "Starting the client..."
CMD="$PYTHON_SCRIPT_NAME $ARGS"
echo $CMD
$CMD
