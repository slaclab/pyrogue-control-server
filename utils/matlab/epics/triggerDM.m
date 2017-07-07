% triggerDM sends a triiger command to the DaqMux.
%     After calling this function call plotData to plotData
%     teh received data.

function triggerDM
    % Global variables define by setEnv
    global DMTriggerPV    

    % Trigger DAQ
    lcaPut(DMTriggerPV, 1);
