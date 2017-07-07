% Process the data from pyrogue strema interfaces
% data is a multidimensiona matrix with the process data
% Its dimentions are data(A,B,C) where:
%  A : number of samples take during each acquition cycle
%  B : number of acquisitions cycles
%  C : number of stram channels (set to 4 in this case)
%        
%   data(:,:,N) is the data comming from channel N. It containst all
%   acquisition blocks done in that channel
%
%   data(:,M,N) is the block of data of acquisiton number M on channel N
%
% To plot, for example, the data acquire on channel 2 during the 6th
% acquisition cycle:
%
%   plot(data(:,6,2))
%
function data = processData(file, buffSize)

    % Number of stream channels
    numChannels = 4
    
    % Number of 16-bits samples
    numSamples = buffSize*2;
    
    % Size of the header (8 bytes in 16-bit words)
    headerSize = 4;
    
    % Read input file
    fileID = fopen(file,'r');
    x = fread(fileID,'uint16');
    fclose(fileID);
    
    % How many data blocks were taken
    numBlocks =  length(x) / (numSamples + headerSize)
    
    % Create empty data matrix
    data = zeros(numSamples,1,numChannels);
    
    % Acquisition index for each channel
    indexs = ones(4,1);
    
    % Copy raw data into its respective vector 
    for i = 1:numBlocks
        % First and last data index in the raw data vector
        firstIndex = (i - 1) * (numSamples + headerSize) + headerSize + 1;
        lastIndex = firstIndex + numSamples -1;

	% This value holds the stream channel
        chN = x(firstIndex - 1) / 256 + 1;
        
        % Copy the data
        data(:,indexs(chN), chN) = x(firstIndex:lastIndex);   
        
        % Increase the respective index 
        indexs(chN) = indexs(chN) +1;
        
    end
end
