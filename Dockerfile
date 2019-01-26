FROM tidair/rogue:v3.1.1

# Install the specified (using --build-arg) tagged version of pyrogue-control-server.
# Defaults to master is the tag version is not specified
ARG TAG=master
WORKDIR /usr/local/src
RUN git clone https://github.com/slaclab/pyrogue-control-server.git
WORKDIR pyrogue-control-server
RUN git checkout ${TAG}

# Run the control server using the user arguments
CMD ./start_server.sh ${SERVER_ARGS}

# Ports used by the EPICS server
EXPOSE 5064 5065 5064/udp 5065/udp
