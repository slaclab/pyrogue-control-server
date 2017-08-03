% continusPlot send continuos trigger commands
%     to the DaqMux and plots the data.
%
%     continuosPlot(num, poll) sends a trigger command every
%     'poll' seconds and plots the data received 
%     from channel number 'num' (0 to 3). 'poll' must be at least 1 seconds.
%
%     The plot windows will have a 'break' button on the bottom left
%     corner. Press the button to break the loop.
%
%     EXMAPLES:
%         continuosPlot(0, 2) plots the channel input 0 every 2 seconds

function continuosPlot(num, poll)
    % Global variables define by setEnv
    global DMTriggerPV  
    global DMBufferSizePV
    global DMIndex
    global streamPV

    if num > 3 | num < 0
        disp('Channel number not valid. Must be between 0 and 3.')
    else

        if poll < 0.1
            disp('poll must at least 0.1 second')
        else
            % Get the size of the DaqMux
            stm_size = lcaGet(DMBufferSizePV)*2;
            
            % Create a new canvas with a break button to stop the loop
            dialogBox = uicontrol('Style', 'PushButton', 'String', 'Break','Callback', 'delete(gcbf)');
            set(gcf, 'Position', [100, 100, 1400, 1200]);
            title(['Stream' num2str(num)]);

            i = 0;
            while (ishandle(dialogBox))
                
                % Read the data
                [y, t] = lcaGet(streamPV(num + 1), stm_size);

                % Get timestamp
                timeStamp = real(t) + imag(t)*1e-9;

                % Build the X-axis
                x = 1:min(stm_size,length(y));
                
                % Plot the data
                plot(x,y);
                title(['Stream' num2str(num) '. (Shot ' num2str(i) '). [Time Stamp: ' num2str(timeStamp) ' s]']);
                i = i + 1;

                % Trigger the DaqMux
                triggerDM

                % Wait fot poll seconds
                pause(poll);
            end
        end
    end