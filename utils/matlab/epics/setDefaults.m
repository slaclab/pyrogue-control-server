% setDefaults sends a command to load the default configuration

function setDefaults
    % Global variables define by setEnv
    global setDefaulstPV

    disp('Sending command to load default configuration...')
    lcaPut(setDefaulstPV, 1);
    pause(5)
    disp('Done')
    disp (' ')
