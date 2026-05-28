%% Initialize workspace
clc;
clear variables;
close all;

addpath('/home/janick-dort/Dokumente/Studium_ZHAW/BA/bf_controller_tuning/lib/');
addpath(genpath('/home/janick-dort/Dokumente/Studium_ZHAW/BA/bf_controller_tuning'));


%% Plotsettings

set(cstprefs.tbxprefs, 'MagnitudeUnits', 'dB');
set(cstprefs.tbxprefs, 'FrequencyUnits', 'Hz');
set(cstprefs.tbxprefs, 'PhaseUnits',     'deg');
set(cstprefs.tbxprefs, 'UnwrapPhase',    'Off');
set(cstprefs.tbxprefs, 'Grid',           'On');

opt = bodeoptions('cstprefs');
opt.MagScale      = 'linear';
opt.PhaseWrapping = 'on';

%% File paths

log_folder    = 'logs';
flight_folder1 = '20260528';
flight_folder2 = '20260528';

log_name1 = '20260526_6_inch.csv';
log_name2 = '20260527_6_inch_1.csv';

file_path1 = fullfile(log_folder, flight_folder1, log_name1);
file_path2 = fullfile(log_folder, flight_folder2, log_name2);

axis = 1;   % roll = 1, pitch = 2

%% Load and process header information
[para1, Nheader1, ind1, ind_cntr1] = extract_header_information(file_path1);
[para2, Nheader2, ind2, ind_cntr2] = extract_header_information(file_path2);

%% Load data from CSV or cached MAT file
[~, base1, ~] = fileparts(file_path1);
mat_path1 = [base1 '.mat'];  % Speichert direkt im aktuellen Arbeitsverzeichnis

[~, base2, ~] = fileparts(file_path2);
mat_path2 = [base2 '.mat'];  % Speichert direkt im aktuellen Arbeitsverzeichnis

try
    S = load(mat_path1);
    if isfield(S, 'flight1')
        flight1 = S.flight1;
    elseif isfield(S, 'data')
        flight1 = S.data;
    else
        error('No valid variable found in MAT file for flight1.');
    end
catch
    flight1 = readmatrix(file_path1, 'NumHeaderLines', Nheader1);
    save(mat_path1, 'flight1');
end

try
    S = load(mat_path2);
    if isfield(S, 'flight2')
        flight2 = S.flight2;
    elseif isfield(S, 'data')
        flight2 = S.data;
    else
        error('No valid variable found in MAT file for flight2.');
    end
catch
    flight2 = readmatrix(file_path2, 'NumHeaderLines', Nheader2);
    save(mat_path2, 'flight2');
end

% Decimate the full matrix once (blackbox runs at the FC loop rate; althold
% debug values update at 100 Hz, so 200:1 brings the effective rate to ~10 Hz
% while keeping a single decimation factor in one place).
Ts_log_raw = para1.looptime * 1e-6 * para1.pid_process_denom * para1.frameIntervalPDenom;
dec        = round((1/Ts_log_raw) / 10);
flight1       = flight1(1:dec:end, :);
flight2       = flight2(1:dec:end, :);
Ts_log     = Ts_log_raw * dec;
Ts_cntr    = Ts_log;   % althold control loop runs at logging rate

% ind.time column is in microseconds (Betaflight blackbox convention).
time1 = (flight1(:, ind1.time) - flight1(1, ind1.time)) * 1e-6;
time2 = (flight2(:, ind2.time) - flight2(1, ind2.time)) * 1e-6;

%% Debug indices
gps_error1       = flight1(:,ind1.debug(1)) / 10;    % gps error
angle_target1    = flight1(:,ind1.debug(2)) / 10;    % target angle
chirp1           = flight1(:,ind1.debug(3)) / 10;    % cm (injected position setpoint)
current_angle1   = flight1(:,ind1.debug(4)) / 10;    % current angle in BF [deg]
pid_sum_EF1      = flight1(:,ind1.debug(5)) / 10;    % PID_sum Earth Frame
sinarg1          = flight1(:,ind1.debug(6)) / 5e3;   % Injected Chirp Signal
active_axis1     = flight1(:,ind1.debug(7)) * 2;     % Low = LON/ROLL, High = LAT/PITCH
pidDA_limit1     = flight1(:,ind1.debug(8)) / 10;    % deg

gps_error2       = flight2(:,ind2.debug(1)) / 10;    % gps error
angle_target2    = flight2(:,ind2.debug(2)) / 10;    % target angle
chirp2           = flight2(:,ind2.debug(3)) / 10;    % cm (injected position setpoint)
current_angle2   = flight2(:,ind2.debug(4)) / 10;    % current angle in BF [deg]
pid_sum_EF2      = flight2(:,ind2.debug(5)) / 10;    % PID_sum Earth Frame
sinarg2          = flight2(:,ind2.debug(6)) / 5e3;   % Injected Chirp Signal
active_axis2     = flight2(:,ind2.debug(7)) * 2;     % Low = LON/ROLL, High = LAT/PITCH
pidDA_limit2     = flight2(:,ind2.debug(8)) / 10;    % deg

%% calculate current and target position from gps error and chirp
target_position1  = chirp1;
current_position1 = chirp1 - gps_error1;

target_position2  = chirp2;
current_position2 = chirp2 - gps_error2;

%% Evaluation masks
ind_eval1 = get_ind_eval(sinarg1, chirp1);
ind_eval2 = get_ind_eval(sinarg2, chirp2);

sinarg_ax1 = sinarg1;
sinarg_ax1(~ind_eval1) = 0;

sinarg_ax2 = sinarg2;
sinarg_ax2(~ind_eval2) = 0;

idx1 = find(ind_eval1);
idx2 = find(ind_eval2);

%% Estimate Transfer Functions

% Welch parameters
frame = 15;
Nest     = round(frame / (Ts_log));
Noverlap = floor(0.9 * Nest);
window   = hann(Nest, 'periodic');

% Low-pass filter for rotating-frame filtering
Dlp = sqrt(3) / 2;
wlp = 2 * pi * 1;
Glp = c2d(tf(wlp^2, [1 2*Dlp*wlp wlp^2]), Ts_log, 'tustin');

%% Apply Rotfiltfilt
inp1   = apply_rotfiltfilt(Glp, sinarg_ax1, target_position1);
out_u1 = apply_rotfiltfilt(Glp, sinarg_ax1, pid_sum_EF1);
out_y1 = apply_rotfiltfilt(Glp, sinarg_ax1, current_position1);

inp2   = apply_rotfiltfilt(Glp, sinarg_ax2, target_position2);
out_u2 = apply_rotfiltfilt(Glp, sinarg_ax2, pid_sum_EF2);
out_y2 = apply_rotfiltfilt(Glp, sinarg_ax2, current_position2);

%% Estimate Transfer function

[T_f1, C_T_f1] = estimate_frequency_response(inp1(idx1), out_y1(idx1), ...
  window, Noverlap, Nest, Ts_log);

f_bode = squeeze(C_T_f1.Frequency);
omega_bode = 2*pi*f_bode;

[T_f2, C_T_f2] = estimate_frequency_response(inp2(idx2), out_y2(idx2), ...
  window, Noverlap, Nest, Ts_log);

%% Estimation Plant

[G_uw_f1, C_uw_f1] = estimate_frequency_response(inp1(idx1), out_u1(idx1), ...
  window, Noverlap, Nest, Ts_log);

[G_uw_f2, C_uw_f2] = estimate_frequency_response(inp2(idx2), out_u2(idx2), ...
  window, Noverlap, Nest, Ts_log);

Plant_f1 = T_f1 / G_uw_f1;

Plant_f2 = T_f2 / G_uw_f2;

%% Flight 1 PIDA Values
freq_vector1 = G_uw_f1.Frequency;

% Analytical PID (standard parameters)
P_f1 = 42;
I_f1 = 80;
D_f1 = 55;
A_f1 = 10;
fc_pt1_f1 = 0.8;

[Cpid_f1] = calculate_poshold_controller( ...
  P_f1,...
  I_f1,...
  D_f1,...
  A_f1,...
  fc_pt1_f1,...
  Ts_cntr,...
  Ts_log,...
  freq_vector1);

%% Flight 2 PIDA Values

freq_vector2 = G_uw_f2.Frequency;

P_f2 = 42;
I_f2 = 80;
D_f2 = 55;
A_f2 = 10;
fc_pt1_f2 = 0.8;


[Cpid_f2] = calculate_poshold_controller( ...
  P_f2,...
  I_f2,...
  D_f2,...
  A_f2,...
  fc_pt1_f2,...
  Ts_cntr,...
  Ts_log,...
  freq_vector2);

%% Get Closed Loop Data

CL_f1 = calculate_closed_loop(Cpid_f1, tf(1,1,Ts_log), Plant_f1, tf(1,1,Ts_log), tf(0,1));

CL_f2 = calculate_closed_loop(Cpid_f2, tf(1,1,Ts_log), Plant_f2, tf(1,1,Ts_log), tf(0,1));

%% Gang of Four Plot

figure(1)
ax(1) = subplot(2,2,1);
bodemag(ax(1), CL_f1.T, T_f1, T_f2, omega_bode, opt);
title('Tracking T');
legend('Calculated Flight1','Measured Flight1','Measured Flight2','Location','best');
grid on;

ax(2) = subplot(2,2,2);
bodemag(ax(2), CL_f1.S, CL_f2.S, omega_bode, opt);
title('Sensitivity S')
legend('Calculated Flight1','Calculated Flight2','Location','best')
grid on

ax(3) = subplot(2,2,3);
bodemag(ax(3), CL_f1.SC, CL_f2.SC, omega_bode, opt);
title('Controller Effort SC');
legend('Calculated Flight1','Calculated Flight2','Location','best');
grid on;

ax(4) = subplot(2,2,4);
bodemag(ax(4), CL_f1.SP, CL_f2.SP, omega_bode, opt);
title('Compliance SP');
legend('Calculated Flight1','Calculated Flight2','Location','best');
grid on;

linkaxes(ax,'x');
xlim(ax(1), [3e-2 10]);
sgtitle('Gang of Four - Position Hold');

%% Step Response

fmax = 2.5;

step_time = (0:Nest-1) .* Ts_log;
T_mean = 0.1 * [-1, 1] + (Nest * Ts_log) / 2;

step_resp = [ ...
    calculate_step_response_from_frd(T_f2,  fmax), ...
    calculate_step_response_from_frd(CL_f1.T, fmax), ...
    calculate_step_response_from_frd(T_f1, fmax)];

% Auf stationären Wert normieren
step_resp_mean = mean(step_resp(step_time > T_mean(1) & step_time < T_mean(2),:), 1);
step_resp = step_resp ./ step_resp_mean;

figure(2)
plot(step_time, step_resp), grid on, ylabel('Altitude (cm)')
title('Step Response Position Hold')
legend('Measured Flight2', 'Calculated Flight1', 'Measured Flight1', 'location', 'best')
ylim([-0.1 1.4]); xlim([0 frame/2]);