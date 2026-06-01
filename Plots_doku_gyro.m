%% Initialize workspace
clc;
clear variables;
close all;

addpath('../bf_controller_tuning/lib/');

do_compensate_iterm = true;

%% File paths
log_folder = '../bf_controller_tuning/logs/gyro/';

% Each gyro log (path relative to log_folder) with the gains it was flown at:
log_name1 = 'Tuned_flipmini.csv';                       % tuned     P=46, I=74, D=30
log_name2 = 'Moderate_flipmini.csv';   % moderate  P=46, I=66, D=32
log_name3 = 'Bad_flipmini.csv';  % bad       P=30, I=60, D=30

base    = 2;   % flight whose plant is identified (the baseline)
compare = 1;   % measured target flight to predict and compare against
%   case 1 = tuned, 2 = moderate, 3 = bad

switch base
  case 1
    file_path1 = fullfile(log_folder, log_name1);
  case 2
    file_path1 = fullfile(log_folder, log_name2);
  case 3
    file_path1 = fullfile(log_folder, log_name3);
  otherwise
    disp("invalid base")
end

switch compare
  case 1
    file_path2 = fullfile(log_folder, log_name1);
    P_new =46 ; I_new = 74; D_new = 30;
  case 2
    file_path2 = fullfile(log_folder, log_name2);
    P_new = 46; I_new = 66; D_new = 32;
  case 3
    file_path2 = fullfile(log_folder, log_name3);
    P_new = 30; I_new = 60; D_new = 30;
  otherwise
    disp("invalid compare")
end

%% Case labels (for plot legends / metrics)
case_names   = {'Tuned', 'Moderate', 'Bad'};
name_base    = case_names{base};
name_compare = case_names{compare};

%% Load and process header information
[para1, Nheader1, ind1, ind_cntr1] = extract_header_information(file_path1);
[para2, Nheader2, ind2, ind_cntr2] = extract_header_information(file_path2);

%% Load data from CSV or cached MAT file
[folder1, base1, ~] = fileparts(file_path1);
mat_path1 = fullfile(folder1, [base1 '.mat']);

[folder2, base2, ~] = fileparts(file_path2);
mat_path2 = fullfile(folder2, [base2 '.mat']);

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

%% Sampling times
Ts      = para1.looptime * 1.0e-6;
Ts_cntr = para1.pid_process_denom * Ts;
Ts_log  = para1.frameIntervalPDenom * Ts_cntr;

%% Time vector
time1 = (flight1(:, ind1.time) - flight1(1, ind1.time)) * 1.0e-6;
time2 = (flight2(:, ind2.time) - flight2(1, ind2.time)) * 1.0e-6;

%% Define axis
ind_ax = 1;   % roll = 1, pitch = 2, yaw = 3

%% Scaling
if para1.blackbox_high_resolution
    blackbox_high_resolution_scale = 10.0;
    ind_bb_high_res = [ind1.gyroADC, ind1.gyroUnfilt, ind1.rcCommand, ind1.setpoint(1:3)];
    flight1(:, ind_bb_high_res) = flight1(:, ind_bb_high_res) / blackbox_high_resolution_scale;
end

if para2.blackbox_high_resolution
    blackbox_high_resolution_scale = 10.0;
    ind_bb_high_res = [ind2.gyroADC, ind2.gyroUnfilt, ind2.rcCommand, ind2.setpoint(1:3)];
    flight2(:, ind_bb_high_res) = flight2(:, ind_bb_high_res) / blackbox_high_resolution_scale;
end

%% Expand indices
ind1.axisSumPI = ind_cntr1 + (1:3);
ind1.sinarg    = ind1.debug(1);

ind2.axisSumPI = ind_cntr2 + (1:3);
ind2.sinarg    = ind2.debug(1);

%% Unscale and remap sinarg
sinargScale = 5.0e3;

flight1(:,ind1.sinarg) = flight1(:,ind1.sinarg) / sinargScale;
flight2(:,ind2.sinarg) = flight2(:,ind2.sinarg) / sinargScale;

%% Assign negative sign for pid error
flight1(:,ind1.axisError) = -flight1(:,ind1.axisError);
flight2(:,ind2.axisError) = -flight2(:,ind2.axisError);

%% Create additional entry for PI sum
flight1 = [flight1, flight1(:,ind1.axisP) + flight1(:,ind1.axisI)];
flight2 = [flight2, flight2(:,ind2.axisP) + flight2(:,ind2.axisI)];

%% Evaluation masks
ind_eval1 = get_ind_eval(flight1(:, ind1.sinarg), flight1(:, ind1.gyroADC(ind_ax)));
ind_eval2 = get_ind_eval(flight2(:, ind2.sinarg), flight2(:, ind2.gyroADC(ind_ax)));

flight1(~ind_eval1, ind1.sinarg) = 0.0;
flight2(~ind_eval2, ind2.sinarg) = 0.0;

%% Average throttle
throttle_avg1 = median(flight1(ind_eval1,ind1.setpoint(4))) / 1.0e3;
throttle_avg2 = median(flight2(ind_eval2,ind2.setpoint(4))) / 1.0e3;

%% Frequency response estimation

Nest     = round(2.5 / Ts_log);
koverlap = 0.9;
Noverlap = floor(koverlap * Nest);
window   = hann(Nest, 'periodic');

Dlp = sqrt(3) / 2;
wlp = 2 * pi * 10;
Glp = c2d(tf(wlp^2, [1 2*Dlp*wlp wlp^2]), Ts_log, 'tustin');

%% Filtered signals flight 1
inp1 = apply_rotfiltfilt(Glp, flight1(:,ind1.sinarg), flight1(:,ind1.setpoint(ind_ax)));
y1   = apply_rotfiltfilt(Glp, flight1(:,ind1.sinarg), flight1(:,ind1.gyroADC(ind_ax)));
u1   = apply_rotfiltfilt(Glp, flight1(:,ind1.sinarg), flight1(:,ind1.axisSum(ind_ax)));
v1   = apply_rotfiltfilt(Glp, flight1(:,ind1.sinarg), flight1(:,ind1.axisSumPI(ind_ax)));

%% Filtered signals flight 2
inp2 = apply_rotfiltfilt(Glp, flight2(:,ind2.sinarg), flight2(:,ind2.setpoint(ind_ax)));
y2   = apply_rotfiltfilt(Glp, flight2(:,ind2.sinarg), flight2(:,ind2.gyroADC(ind_ax)));
u2   = apply_rotfiltfilt(Glp, flight2(:,ind2.sinarg), flight2(:,ind2.axisSum(ind_ax)));
v2   = apply_rotfiltfilt(Glp, flight2(:,ind2.sinarg), flight2(:,ind2.axisSumPI(ind_ax)));

%% Transfer function estimation

% T: w -> y
[T1, C_T1] = estimate_frequency_response(inp1(ind_eval1), y1(ind_eval1), window, Noverlap, Nest, Ts_log);
[T2, C_T2] = estimate_frequency_response(inp2(ind_eval2), y2(ind_eval2), window, Noverlap, Nest, Ts_log);

% Guw: w -> u, kompletter Controller-Output axisSum
[Guw1, C_Guw1] = estimate_frequency_response(inp1(ind_eval1), u1(ind_eval1), window, Noverlap, Nest, Ts_log);
[Guw2, C_Guw2] = estimate_frequency_response(inp2(ind_eval2), u2(ind_eval2), window, Noverlap, Nest, Ts_log);

% Gvw: w -> v, nur PI-Anteil axisSumPI
[Gvw1, C_Gvw1] = estimate_frequency_response(inp1(ind_eval1), v1(ind_eval1), window, Noverlap, Nest, Ts_log);
[Gvw2, C_Gvw2] = estimate_frequency_response(inp2(ind_eval2), v2(ind_eval2), window, Noverlap, Nest, Ts_log);

%% Plant and measured controller estimates
P1 = T1 / Guw1;
P2 = T2 / Guw2;

Cpi1 = Gvw1 / (1 - T1);
Cd1  = Guw1 * Gvw1 / T1 * (1 / Guw1 - 1 / Gvw1);

Cpi2 = Gvw2 / (1 - T2);
Cd2  = Guw2 * Gvw2 / T2 * (1 / Guw2 - 1 / Gvw2);

%% Analytical transfer functions

[Cpi_ana1, Cd_ana1, Gf_ana1, PID1, para_used1] = ...
    calculate_transfer_functions(para1, ind_ax, throttle_avg1, Ts_cntr);

if Gf_ana1.Ts < Ts_log
    Gf_ana1  = downsample_frd(Gf_ana1 , Ts_log, P1.Frequency);
    Cpi_ana1 = downsample_frd(Cpi_ana1, Ts_log, P1.Frequency);
    Cd_ana1  = downsample_frd(Cd_ana1 , Ts_log, P1.Frequency);
end

[Cpi_ana2, Cd_ana2, Gf_ana2, PID2, para_used2] = ...
    calculate_transfer_functions(para2, ind_ax, throttle_avg2, Ts_cntr);

if Gf_ana2.Ts < Ts_log
    Gf_ana2  = downsample_frd(Gf_ana2 , Ts_log, P2.Frequency);
    Cpi_ana2 = downsample_frd(Cpi_ana2, Ts_log, P2.Frequency);
    Cd_ana2  = downsample_frd(Cd_ana2 , Ts_log, P2.Frequency);
end

%% New PID

pid_axis = {'rollPID', 'pitchPID', 'yawPID'};

% P_new / I_new / D_new are set per `compare` case in the File paths section.

pid_scale = [get_pid_scale(ind_ax), 1];

PID_new(1) = P_new * pid_scale(1);

% I wie im Original über fI-Verhältnis berechnen
fI = PID1(2) / (2*pi*PID1(1));
I_ratio_new = I_new / para1.(pid_axis{ind_ax})(2);
fI_new = fI * I_ratio_new;

PID_new(2) = 2*pi*PID_new(1)*fI_new;
PID_new(3) = D_new * pid_scale(3);
PID_new(4) = 0;

para1_new = para1;

para1_new.(pid_axis{ind_ax}) = round(PID_new ./ pid_scale);

% Betaflight-Format: [P I D D_min FF]
para1_new.(pid_axis{ind_ax}) = [para1_new.(pid_axis{ind_ax})(1:3), ...
                                para1_new.(pid_axis{ind_ax})(3), ...
                                para1_new.(pid_axis{ind_ax})(4)];

%% New analytical transfer functions

[Cpi_ana_new, Cd_ana_new, Gf_ana_new, PID_new, para_used_new] = ...
    calculate_transfer_functions(para1_new, ind_ax, throttle_avg1, Ts_cntr);

if Gf_ana_new.Ts < Ts_log
    Gf_ana_new  = downsample_frd(Gf_ana_new , Ts_log, P1.Frequency);
    Cpi_ana_new = downsample_frd(Cpi_ana_new, Ts_log, P1.Frequency);
    Cd_ana_new  = downsample_frd(Cd_ana_new , Ts_log, P1.Frequency);
end

%% Closed loop

CL_ana = calculate_closed_loop(Cpi_ana1, tf(1,1,Ts_log), ...
    P1 / Gf_ana1, Gf_ana1, Cd_ana1);

CL_ana_new = calculate_closed_loop(Cpi_ana_new, tf(1,1,Ts_log), ...
    P1 / Gf_ana1, Gf_ana_new, Cd_ana_new);

%% Optional I-term compensation

if do_compensate_iterm
    Cpi_com = Cpi1 / Cpi_ana1;

    CL_ana_comp = calculate_closed_loop(Cpi_ana1 * Cpi_com, tf(1,1,Ts_log), ...
        P1 / Gf_ana1, Gf_ana1, Cd_ana1);

    CL_ana_new_comp = calculate_closed_loop(Cpi_ana_new * Cpi_com, tf(1,1,Ts_log), ...
        P1 / Gf_ana1, Gf_ana_new, Cd_ana_new);

    CL_ana.T     = CL_ana_comp.T;
    CL_ana_new.T = CL_ana_new_comp.T;
end

%% Step responses

f_max = min([para1.dyn_notch_min_hz, para1.gyro_rpm_notch_min]);

T_mean   = 0.1 * [-1, 1] + (Nest * Ts_log) / 2;
step_time = (0:Nest-1).' * Ts_log;

step_resp = [ ...
    calculate_step_response_from_frd(T1, f_max), ...
    calculate_step_response_from_frd(CL_ana_new.T, f_max), ...
    calculate_step_response_from_frd(T2, f_max)];

step_resp_mean = mean(step_resp(step_time > T_mean(1) & step_time < T_mean(2), :));
step_resp = step_resp ./ step_resp_mean;

%% Plot

figure(1)
plot(step_time, step_resp, 'LineWidth', 1.5)
grid on
ylabel('Gyro (deg/sec)')
xlabel('Time (sec)')
title('Tracking T')
legend(sprintf('Measured %s', name_base), ...
       sprintf('Calculated %s', name_compare), ...
       sprintf('Measured %s', name_compare), ...
       'Location', 'best')
xlim([0 0.5])
ylim([0 1.3])


%% Numerical metrics for thesis Results section (Gyro)
% Set base/compare at the top and re-run once per baseline to fill the gyro
% step-response table (tab:gyro_step) in the thesis:
%   - moderate change: base=2 (P=46, I=66, D=32), compare=3 (target)
%   - large change:    base=1 (P=30, I=60, D=30), compare=3 (target)
% The target flight (compare) and its gains stay fixed across both runs. Copy
% each console block into the LaTeX draft so the Results section reports
% measured numbers rather than eyeballed plot readings.

pid1 = para1.(pid_axis{ind_ax});
pid2 = para2.(pid_axis{ind_ax});

fprintf('\n========================================\n');
fprintf('GYRO METRICS  axis=%d (1=roll, 2=pitch, 3=yaw)\n', ind_ax);
fprintf('  baseline Flight 1 gains:  P=%d  I=%d  D=%d\n', pid1(1), pid1(2), pid1(3));
fprintf('  target (calculated new):  P=%d  I=%d  D=%d\n', P_new, I_new, D_new);
fprintf('  measured Flight 2 gains:  P=%d  I=%d  D=%d\n', pid2(1), pid2(2), pid2(3));
fprintf('  eval window  F1: %.2f s (%d samples)   F2: %.2f s (%d samples)   Ts=%.4f s\n', ...
    nnz(ind_eval1)*Ts_log, nnz(ind_eval1), nnz(ind_eval2)*Ts_log, nnz(ind_eval2), Ts_log);
fprintf('========================================\n');

% step_resp columns (see step-response section above):
%   [Measured 1 (baseline), Calculated new (predicted target), Measured 2 (target)]
labels_step = {sprintf('Measured %s', name_base), ...
               sprintf('Calculated %s', name_compare), ...
               sprintf('Measured %s', name_compare)};
fprintf('  -- Step response (normalised to steady state = 1.0) --\n');
for k = 1:size(step_resp, 2)
    y = step_resp(:, k);
    t = step_time(:);
    y_final = 1.0;
    idx_10 = find(y >= 0.10 * y_final, 1, 'first');
    idx_90 = find(y >= 0.90 * y_final, 1, 'first');
    if ~isempty(idx_10) && ~isempty(idx_90) && idx_90 > idx_10
        t_rise = t(idx_90) - t(idx_10);
    else
        t_rise = NaN;
    end
    outside  = abs(y - y_final) > 0.05;
    last_out = find(outside, 1, 'last');
    if isempty(last_out)
        t_settle = 0;
    elseif last_out >= length(t)
        t_settle = NaN;
    else
        t_settle = t(last_out + 1);
    end
    overshoot_pct = 100 * (max(y) - y_final) / y_final;
    fprintf('     %-20s  t_rise=%.3f s  t_settle=%.3f s  overshoot=%.1f %%\n', ...
        labels_step{k}, t_rise, t_settle, overshoot_pct);
end
fprintf('========================================\n\n');
