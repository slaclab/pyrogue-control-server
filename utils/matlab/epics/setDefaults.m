% setDefaults sends a command to load the default configuration
%   This command will be available only if a default file was pass 
%   as an argument to the EPICS server at startup
%

function setDefaults
    % Global variables define by setEnv
    global setDefaulstPV

    disp('Sending command to load default configuration...')
    lcaPut(setDefaulstPV, 1);
    pause(5)
    disp('Done')
    disp (' ')
