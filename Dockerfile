FROM tidair/rogue:v3.1.1

# Install the SMURF PCIe card repository
WORKDIR /usr/local/src
RUN git clone https://github.com/slaclab/smurf-pcie.git
WORKDIR smurf-pcie
RUN sed -i -e 's|git@github.com:|https://github.com/|g' .gitmodules
RUN git submodule sync && git submodule update --init --recursive
ENV PYTHONPATH /usr/local/src/smurf-pcie/software/python:${PYTHONPATH}
ENV PYTHONPATH /usr/local/src/smurf-pcie/firmware/submodules/axi-pcie-core/python:${PYTHONPATH}

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
