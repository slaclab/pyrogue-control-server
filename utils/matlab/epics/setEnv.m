% setEnv sets up the environment for communicate with the EPICS server
%     setEnv(prefix) must be call before calling any of the others functions.
%
%     prefix is the PV name prefix used to launch.
%
%     EXAMPLES:
%         setEnv('my_pv_prefix')

function setEnv(prefix)   
    % Set enviroment for labCA
    addpath /afs/slac/g/reseng/epics/labCA_R3.16/bin/linux-x86_64/labca
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    %%% Set environmental variables, used by other functions %%%
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    disp('Setting enviromental variables...')
    
    % Global variables which will be visible inside other functions
    global PVNamePrefix
    global DMIndex
    global ReadAllPV
    global setDefaulstPV              
    global buildStampPV           
    global gitHashPV
    global fpgaVersionPV
    global upTimeCntPV
    global DMTriggerPV
    global DMBufferSizePV
    global DMInputDataValidPV
    global DMInputMuxSelPV
    global WEBStartAddrPV
    global WEBEndAddrPV
    global streamPV
    global cmdJesdRst
    
    % PV name prefix
    PVNamePrefix = prefix;
    disp(['Using the EPICS PV name prefix: ' PVNamePrefix])
    
    % DaqMuxV2 index to be used
    DMIndex = 0;
    
    % Setup PVs
    ReadAllPV              = [PVNamePrefix ':AMCc:ReadAll'];
    setDefaulstPV          = [PVNamePrefix ':AMCc:setDefaults'];
    buildStampPV           = [PVNamePrefix ':AMCc:FpgaTopLevel:AmcCarrierCore:AxiVersion:BuildStamp'];
    gitHashPV              = [PVNamePrefix ':AMCc:FpgaTopLevel:AmcCarrierCore:AxiVersion:GitHash'];
    fpgaVersionPV          = [PVNamePrefix ':AMCc:FpgaTopLevel:AmcCarrierCore:AxiVersion:FpgaVersion'];
    upTimeCntPV            = [PVNamePrefix ':AMCc:FpgaTopLevel:AmcCarrierCore:AxiVersion:UpTimeCnt'];
    DMTriggerPV            = [PVNamePrefix ':AMCc:FpgaTopLevel:AppTop:DaqMuxV2[' num2str(DMIndex) ']:TriggerDaq'];
    DMBufferSizePV         = [PVNamePrefix ':AMCc:FpgaTopLevel:AppTop:DaqMuxV2[' num2str(DMIndex) ']:DataBufferSize'];
    cmdJesdRst             = [PVNamePrefix ':AMCc:FpgaTopLevel:AppTop:JesdReset'];
    
    DMInputMuxSelPV    = {''};
    DMInputDataValidPV = {''};
    WEBStartAddrPV     = {''};
    WEBEndAddrPV       = {''};
    for i = 0:3
    	DMInputMuxSelPV(i+1)    = {[PVNamePrefix ':AMCc:FpgaTopLevel:AppTop:DaqMuxV2[' num2str(DMIndex) ']:InputMuxSel[' num2str(i) ']']};
        DMInputDataValidPV(i+1) = {[PVNamePrefix ':AMCc:FpgaTopLevel:AppTop:DaqMuxV2[' num2str(DMIndex) ']:InputDataValid[' num2str(i) ']']};
    	WEBStartAddrPV(i+1)     = {[PVNamePrefix ':AMCc:FpgaTopLevel:AmcCarrierCore:AmcCarrierBsa:BsaWaveformEngine[' num2str(DMIndex) ']:WaveformEngineBuffers:StartAddr[' num2str(i) ']']};
    	WEBEndAddrPV(i+1)       = {[PVNamePrefix ':AMCc:FpgaTopLevel:AmcCarrierCore:AmcCarrierBsa:BsaWaveformEngine[' num2str(DMIndex) ']:WaveformEngineBuffers:EndAddr[' num2str(i) ']']};
    end
    
    streamPV = {''};
    for i =0:7
    	streamPV(i+1) = {[PVNamePrefix ':AMCc:Stream' num2str(i)]};
    end
    
    disp('Done setting enviroment.')
    disp(' ')
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    %%% End of setting environmental variables               %%%
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    % Send read All command
    ReadAll

    % Set default configuration
    setDefaults

    % Send ReadAll command
    ReadAll

    % Print Build information
    disp('Firmware image information:')
    disp('==================================================')
    disp(['Build Stamp     = ' char(lcaGet(buildStampPV))])
    disp(['FPGA Version    = ' num2str(lcaGet(fpgaVersionPV))])
    disp(['Git Hash        = ' num2str(lcaGet(gitHashPV))])
    disp(['Up Time Counter = ' num2str(lcaGet(upTimeCntPV))])
