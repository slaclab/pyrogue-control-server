% setBufferSize sets the size of the DaqMux data buffer
%     setBufferSize(size) will also set the size of the
%     WaveformEngineeBuffer  accordingly. 
%
%     The maximum size number is 0xFFFFFFFF.
%
%     EXAMPLES:
%         setBufferSize(1000)             sets the buffer size to 1000
%         setBufferSize(hex2dec('2000'))  sets the buffer size to 0x2000

function setBufferSize(size) 
    % Global variables define by setEnv
    global DMBufferSizePV
    global WEBStartAddrPV
    global WEBEndAddrPV

    % Check size
    if size > hex2dec('FFFFFFFF')
        disp('Size number not valid. It mus tbe less than 0xFFFFFFFF.')
    else
        % Change DaqMux Data buffer size
        lcaPut(DMBufferSizePV, size)
        
        % Change Waveform Enginee Buffer size
        sa = typecast(int32(lcaGet([WEBStartAddrPV'])),'uint32');
        ea = sa + 4*size;
        lcaPut([WEBEndAddrPV'], double(typecast(uint32(ea), 'int32')))
        
        % Show current sizes:
        disp('New DaqMux Data Buffer Size (hex):')
        disp(dec2hex(lcaGet(DMBufferSizePV)))
        disp(' ')
        disp('New Waveform Engine Buffer Start Addrs (hex):')
        disp(dec2hex(typecast(int32(lcaGet([WEBStartAddrPV'])),'uint32')))
        disp(' ')
        disp('New Waveform Engine Buffer End Addrs (hex):')
        disp(dec2hex(typecast(int32(lcaGet([WEBEndAddrPV'])),'uint32')))
        disp(' ')
    end
