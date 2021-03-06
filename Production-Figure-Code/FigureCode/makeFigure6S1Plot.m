function makeFigure6S1Plot(dataPath, savePath)
%% Plot figure 6---figure supplement 1

close all;
warning('off', 'MATLAB:print:FigureTooLargeForPage');
warning('off', 'MATLAB:MKDIR:DirectoryExists');
GEN_DATA_PATH = @(fname) fullfile(dataPath, fname);
GEN_SAVE_PATH = @(fname) fullfile(savePath, fname);

%% Load data
% Search for simulated data in the working directory
[snrErg, snrInf, RE_Erg, RE_Inf] = ...
    ProcessData(GEN_DATA_PATH('snr_sweep_sim/'));

%% Plot result
figure(1); clf;
set(gcf, ...
    'units','normalized','outerposition',[0 0 1 1], ...
    'PaperPositionMode','auto', ...
    'PaperOrientation','landscape', ...
    'PaperUnits', 'inches', ...
    'PaperSize', [30, 30]);
notBoxPlot(RE_Inf, snrInf, 'plotRawData', false, 'blendPatchColor', true)
hold on;
notBoxPlot(RE_Erg, snrErg, ...
    'plotColor', 'b', 'plotRawData', false, 'blendPatchColor', true);
xlabel('SNR');
ylabel('Relative Exploration');
baseLine = line([5, 56], [1, 1], 'LineStyle', '--', 'LineWidth', 2);
hPatch = findobj(gca,'Type','patch');
legend([hPatch(1), hPatch(end), baseLine], ...
    {'Ergodic Harvesting', 'Infotaxis', 'Baseline'});
opt = [];
opt.BoxDim = [8,5] * 0.7;
opt.ShowBox = 'off';
opt.XMinorTick = 'off';
opt.YMinorTick = 'off'; 
opt.XTick = [10:10:50];
opt.YTick = [0:0.5:2.5];
opt.XLim = [9, 57];
opt.YLim = [0, 2.5];
opt.FontName = 'Helvetica';
opt.FontSize = 14;
opt.IgnoreLines = 1;
setAxesProp(opt, gca);
baseLine.LineStyle = '--';
legend('off');
set(gca, 'units', 'normalized');
axesPosition = get(gca, 'Position');
axesPosition(1:2) = [0.2, 0.5];
set(gca, 'Position', axesPosition);

% Compute correlation coefficient and its 95% confidence interval
[Rerg, ~, RLerg, RUerg] = corrcoef(double(snrErg), RE_Erg);
[Rinf, ~, RLinf, RUinf] = corrcoef(double(snrInf), RE_Inf);
axes; hold on;
errorbar(Rerg(2),1,RLerg(2)-Rerg(2),RUerg(2)-Rerg(2), ...
    'Horizontal', '.', 'LineWidth', 4, 'MarkerSize', 50, ...
    'Color', 'k', 'CapSize', 20); 
errorbar(Rinf(2),2,RLinf(2)-Rinf(2),RUinf(2)-Rinf(2), ...
    'Horizontal', '.', 'LineWidth', 4, 'MarkerSize', 50, ...
    'Color', 'k', 'CapSize', 20);
ylim([0.5, 2.5]);
set(gca, 'YTick', [1,2]);
set(gca, 'YTickLabel', {'Ergodic Harvesting', 'Infotaxis'});
xlabel('Correlation Coefficient');
opt = [];
opt.BoxDim = [8,5] * 0.7;
opt.ShowBox = 'off';
opt.XMinorTick = 'off';
opt.YMinorTick = 'off'; 
opt.XTick = [-1:0.2:0.6];
opt.XLim = [-1, 0.6];
opt.FontName = 'Helvetica';
opt.FontSize = 14;
opt.IgnoreLines = 1;
setAxesProp(opt, gca);
legend(gca, 'off');
ytickangle(90);
set(gca, 'units', 'normalized');
axesPosition = get(gca, 'Position');
axesPosition(1:2) = [0.6, 0.5];
set(gca, 'Position', axesPosition);
drawnow;
print(gcf, GEN_SAVE_PATH('fig6s1.pdf'), '-dpdf');
fprintf('Figure panels created at %s\n', GEN_SAVE_PATH(''));


function [snrErg, snrInf, RE_Erg, RE_Inf] = ProcessData(dataPath)

warning('off', 'MATLAB:print:FigureTooLargeForPage');
warning('off', 'MATLAB:MKDIR:DirectoryExists');
GEN_DATA_PATH = @(fname) fullfile(dataPath, fname);
%% Load data
eihTrials = dir(GEN_DATA_PATH('*EIH*.mat'));
ifTrials = dir(GEN_DATA_PATH('*Infotaxis*.mat'));
if isempty(eihTrials) || isempty(ifTrials)
    error('Cannot found simulation data, please make sure local simulation has finished or use USE_PREV_DATASET = 1');
end

%% Process data
[ifData, ~] = mProcessData(ifTrials, 0);
[eihData, ~] = mProcessData(eihTrials, 1);

%% Return result
snrErg = double(eihData.SNR);
snrInf = double(ifData.SNR);
RE_Erg = eihData.RE;
RE_Inf = ifData.RE;

function Perf = mEvalPerf(dat, evalErg)
% Estimate target position using mean belief
if size(dat.pB, 2) == 1
    % InfoMax
    dat.pB(:,1,1) = dat.pB(:,1,1) / sum(dat.pB(:,1,1));
    posEstimate = squeeze([sum(dat.pB .* linspace(0,1,101)')])';  
else
    % Ergodic Harvesting
    posEstimate = [];
    for i = 1:size(dat.pB, 3)
        posEstimate = [posEstimate, squeeze([sum(dat.pB(:,:,i) .* linspace(0,1,101)')])];
    end
end

errEstimate = abs(posEstimate(1:length(dat.oTrajList)) - dat.oTrajList);
absPosErr = dat.sTrajList(1:length(dat.oTrajList)) - dat.oTrajList;
Perf.rmsEstErr = rms(errEstimate);
Perf.meanEstErr = mean(errEstimate);
Perf.varEstErr = var(errEstimate);
binEdgesErr = linspace(-0.4, 0.4, 21);
binEdges = linspace(0.2, 0.8, 21);
[Perf.posErrHist.N, Perf.posErrHist.edges] = histcounts(absPosErr, binEdgesErr);
[Perf.posHistSensor.N, Perf.posHistSensor.edges] = histcounts(dat.sTrajList, binEdges);
[Perf.posHistTarget.N, Perf.posHistTarget.edges] = histcounts(dat.oTrajList, binEdges);
% FFT
% dat.sTrajList = movmean(dat.sTrajList, 5);
dat.sTrajList = LPF(dat.sTrajList, 1/dat.dt, 2);
Perf.RE = sum(abs(diff(dat.sTrajList))) / sum(abs(diff(dat.oTrajList)));
% Evaluate ergodicity
if evalErg
    Perf.meanErg = mean(dat.ergList(2:end-1));
    Perf.varErg = var(dat.ergList(2:end-1));
end


function [snrData, snrStruct] = mProcessData(trials, evalErg)
snrData.SNR = [];
snrData.rmsEstErr = [];
snrData.meanEstErr = [];
snrData.varEstErr = [];
snrData.meanEntropy = [];
snrData.rmsEntropy = [];
snrData.varEntropy = [];
snrData.posErrHist = [];
snrData.posErrHistData = [];
snrData.posHistSensor = [];
snrData.posHistSensorData = [];
snrData.posHistTarget = [];
snrData.posHistTargetData = [];
snrData.pcentStill = [];
snrData.RE = [];
for i = 1:length(trials)
    dat = load([trials(i).folder, '/', trials(i).name]);
    fprintf('processing %s ...\n', trials(i).name);
    
    % Evaluate tracking performance
    Perf = mEvalPerf(dat, evalErg);
    
    % Append data
    snrData.SNR = [snrData.SNR, dat.SNR];
    snrData.rmsEstErr = [snrData.rmsEstErr, Perf.rmsEstErr];
    snrData.meanEstErr = [snrData.meanEstErr, Perf.meanEstErr];
    snrData.varEstErr = [snrData.varEstErr, Perf.varEstErr];
    snrData.posErrHist = [snrData.posErrHist, Perf.posErrHist];
    snrData.posErrHistData = [snrData.posErrHistData; Perf.posErrHist.N];
    snrData.posHistSensor = [snrData.posHistSensor, Perf.posHistSensor];
    snrData.posHistSensorData = [snrData.posHistSensorData; Perf.posHistSensor.N];
    snrData.posHistTarget = [snrData.posHistTarget, Perf.posHistTarget];
    snrData.posHistTargetData = [snrData.posHistTargetData; Perf.posHistTarget.N];
    snrData.pcentStill = [snrData.pcentStill, calcPcentStationary(dat.sTrajList)];
    snrData.RE = [snrData.RE, Perf.RE];
    if size(dat.pB, 2) == 1
        % InfoMax trial
        snrData.meanEntropy = [snrData.meanEntropy, mean(dat.enpList(1:end-1))];
        snrData.rmsEntropy = [snrData.rmsEntropy, rms(dat.enpList(1:end-1))];
        snrData.varEntropy = [snrData.varEntropy, var(dat.enpList(1:end-1))];
    else
        % ErgInfo trial
        if ~isfield(dat, 'enpList')
            dat.enpList = zeros(1, size(dat.pB, 2) * (size(dat.pB, 3)-1));
            idx = 1;
            for iter = 1:(size(dat.pB, 3)-1)
                for samp = 1:size(dat.pB, 2)
                    dat.enpList(idx) = entropydist(dat.pB(:, samp, iter));
                    idx = idx + 1;
                end
            end
        end
        snrData.meanEntropy = [snrData.meanEntropy, mean(dat.enpList(2:end))];
        snrData.rmsEntropy = [snrData.rmsEntropy, rms(dat.enpList(2:end))];
        snrData.varEntropy = [snrData.varEntropy, var(dat.enpList(2:end))];   
        if evalErg
            if ~isfield(snrData, 'meanErg')
                snrData.meanErg = [];
                snrData.varErg = [];
            end
            snrData.meanErg = [snrData.meanErg, Perf.meanErg];
            snrData.varErg = [snrData.varErg, Perf.varErg];
        end
    end
end

% Summarize SNR conditions if there are more than 1 samples per SNR
% condition
SNRsamps = unique(snrData.SNR);
nSamps = length(SNRsamps);
snrStruct(nSamps).SNR = [];
snrStruct(nSamps).rmsEstErr = [];
snrStruct(nSamps).meanEstErr = [];
snrStruct(nSamps).varEstErr = [];
snrStruct(nSamps).meanEntropy = [];
snrStruct(nSamps).rmsEntropy = [];
snrStruct(nSamps).varEntropy = [];
snrStruct(nSamps).posErrHist = [];
snrStruct(nSamps).posErrHistData = [];
snrStruct(nSamps).posErrHistDataMean = [];
snrStruct(nSamps).posHistSensorData = [];
snrStruct(nSamps).posHistSensorDataMean = [];
snrStruct(nSamps).posHistTargetData = [];
snrStruct(nSamps).posHistTargetDataMean = [];
snrStruct(nSamps).pcentStill = [];
snrStruct(nSamps).RE = [];

for i = 1:nSamps
    snrStruct(i).SNR = SNRsamps(i);
    snrStruct(i).rmsEstErr = snrData.rmsEstErr(snrData.SNR == SNRsamps(i));
    snrStruct(i).meanEstErr = snrData.meanEstErr(snrData.SNR == SNRsamps(i));
    snrStruct(i).varEstErr = snrData.varEstErr(snrData.SNR == SNRsamps(i));
    snrStruct(i).meanEntropy = snrData.meanEntropy(snrData.SNR == SNRsamps(i));
    snrStruct(i).rmsEntropy = snrData.rmsEntropy(snrData.SNR == SNRsamps(i));
    snrStruct(i).varEntropy = snrData.varEntropy(snrData.SNR == SNRsamps(i));
    snrStruct(i).posErrHist = snrData.posErrHist(snrData.SNR == SNRsamps(i));
    snrStruct(i).posErrHistData = snrData.posErrHistData(snrData.SNR == SNRsamps(i),:);
    snrStruct(i).pcentStill = snrData.pcentStill(snrData.SNR == SNRsamps(i));
    snrStruct(i).RE = snrData.RE(snrData.SNR == SNRsamps(i));
    if size(snrData.posErrHistData(snrData.SNR == SNRsamps(i),:),1) > 1
        snrStruct(i).posErrHistDataMean = mean(snrData.posErrHistData(snrData.SNR == SNRsamps(i),:));
    else
        snrStruct(i).posErrHistDataMean = snrData.posErrHistData(snrData.SNR == SNRsamps(i),:);
    end
    if size(snrData.posHistSensorData(snrData.SNR == SNRsamps(i),:),1) > 1
        snrStruct(i).posHistSensorDataMean = mean(snrData.posHistSensorData(snrData.SNR == SNRsamps(i),:));
    else
        snrStruct(i).posHistSensorDataMean = snrData.posHistSensorData(snrData.SNR == SNRsamps(i),:);
    end
    if size(snrData.posHistTargetData(snrData.SNR == SNRsamps(i),:),1) > 1
        snrStruct(i).posHistTargetDataMean = mean(snrData.posHistTargetData(snrData.SNR == SNRsamps(i),:));
    else
        snrStruct(i).posHistTargetDataMean = snrData.posHistTargetData(snrData.SNR == SNRsamps(i),:);
    end

end

function ps = calcPcentStationary(traj)
%% Compute percentage stationary for infotaxis trials
debug = 0;
% filter trajectory using moving average filter
filtTraj = movmean(traj,6);
% Find consecutive stationary moves
sMoves = abs(diff(filtTraj)) < 1e-12;
% Find the length of each consecutive stationary moves
strIdx = strfind([0,sMoves==1],[0 1]);
endIdx = strfind([sMoves==1,0],[1 0]);
sLength = endIdx - strIdx + 1;
% Filter short stationary moves (those last no more than 2 iterations)
validIdx = sLength > 2;
sLength = sLength(validIdx);
% Compute the overall number of iterations that the sensor is stationary
sCount = sum(sLength);
% Compute percentage of moves that are qualified as stationary
ps = 100.0 * sCount / length(filtTraj);

%% for debug - plot
if debug
    figure(2); clf;
    plot(traj); hold on;
    plot(filtTraj, 'LineWidth', 2);
    pltIdx = zeros(1, length(filtTraj));
    for i = 1:length(strIdx)
        if validIdx(i)
            pltIdx(strIdx(i):endIdx(i)) = 1;
        end
    end
    filtTraj(~pltIdx) = NaN;
    plot(filtTraj, '.');
    legend('Traj', 'Filtered', 'Stationary');
    pause(0.1);
end