% setDMInput Send the DaqMux Input channel
%     setDMInput(num, ch) were num is the channel 
%     number (0 to 3) and ch is the channel to be selected by name 
%     (['Disabled', 'Test', 'Ch(0:29)']) or by the index number (0 to 32).
%
%     num can also be a range, in that case ch will be assigned to all of them.
%
%     EXAMPLES:
%         setDMInput(0, 'Disabled')  disables input 0
%         setDMInput(2, '3')         sets Input 2 to channel 'Ch0', (using 'Ch0' index)
%         setDMInput((0:3), 'Test')  set all inputs to channel 'Test'

function setDMInput(num, ch)
    % Global variables define by setEnv
    global DMInputMuxSelPV

    if max(num) > 3 | min(num) < 0
        disp('Input number not valid. Must be between 0 and 3.')
    else
        % Create a vector with the same size of 
        % num, and fill with the ch value
        val = cell(length(num),1);
        val = {ch};

        % Write the selected PVs
        lcaPut(DMInputMuxSelPV(num + 1)', val);

        % Print the new configuration
        disp('New configuration (Inputs 0 to 3):')
        disp(lcaGet(DMInputMuxSelPV'))
        disp(' ')
    end
