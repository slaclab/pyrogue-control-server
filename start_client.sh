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

usage() {
    echo ""
    echo "Start a PyRogue client to communicate with a pyrogue server runing in a remote (or local) host"
    echo ""
    echo "usage: $SCRIPT_NAME [-g group_name] [-h]"
    echo "    -h                  : Show this message"
    echo "    -g <group_name>     : Pyro4 group name used for remote clients (default \"pyrogue_test\")"
    echo ""
    exit
}

ARGS=""

while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        -g)
            ARGS="$ARGS -g $2"
            shift
            ;;
        -h)
            usage
            ;;
        *)
            # unknow option
            echo "Uknown option"
            usage
            ;;
    esac
    shift
done

echo ""

echo "Setting the enviroment..."
source setup_rogue.sh

# Start the client
echo "Starting the client..."
CMD="./python/pyrogue_client.py $ARGS"
echo $CMD
$CMD
