% ReadAll sends a command to read all register to the pyrogue server
%   Registers must upated in order to PVs to update. 
%
%   This call is necesary to read register with pollIntervale=0.

function ReadAll
    % Global variables define by setEnv
    global ReadAllPV

    disp('Sending command to read all registers...')
    lcaPut(ReadAllPV, 1);
    pause(5)
    disp('Done')
    disp (' ')
