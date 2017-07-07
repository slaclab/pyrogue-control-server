% readAll sends a command to read all register to the pyrogue server
%   Registers must upated in order to PVs to update. 
%
%   This call is necesary to read register with pollIntervale=0.

function readAll
    % Global variables define by setEnv
    global readAllPV

    disp('Sending command to read all registers...')
    lcaPut(readAllPV, 1);
    pause(5)
    disp('Done')
    disp (' ')
