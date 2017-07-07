% plotData plots the data received from the DaqMux
%     triggerDM should be call before calling this function,
%     so new data is available to be plotted. 

function plotData
    % Global variables define by setEnv
    global DMBufferSizePV
    global DMIndex
    global streamPV

    % Get the size of the DaqMux
    stm_size = lcaGet(DMBufferSizePV)*2;

    % Create a new canvas
    figure(1)
    set(gcf, 'Position', [100, 100, 1400, 1200])

    % Plot the data from the 4 stream channel of this DaqMux
    for i = 0:3
        % Prepare the plot area
        stmNum = 4 * DMIndex + i;
        subplot(2,2,i+1)

        % Read the data
        y = lcaGet(streamPV(stmNum + 1), stm_size);

        % Build the X-axis
        x = 1:min(stm_size,length(y));
        
        % Plot the data
        plot(x,y)
        title(['Stream' num2str(stmNum)])
    end
