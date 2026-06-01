%% Initialize workspace
clc;
clear variables;
close all;

% addpath('/home/janick-dort/Dokumente/Studium_ZHAW/BA/bf_controller_tuning/lib/');
% addpath(genpath('/home/janick-dort/Dokumente/Studium_ZHAW/BA/bf_controller_tuning'));

addpath('../bf_controller_tuning/lib/');

%% File paths

log_folder    = '../bf_controller_tuning/logs';
flight_folder = 'angle';

log_name1 = 'P_50_flipmini.csv'; % default
log_name2 = 'P_80_flipmini.csv'; % tuned
log_name3 = 'P_100_flipmini.csv'; % more tuned

base = 2;
compare = 3;
switch base
  case 1
    file_path1 = fullfile(log_folder, flight_folder, log_name1);
  case 2
    file_path1 = fullfile(log_folder, flight_folder, log_name2);
  case 3
    file_path1 = fullfile(log_folder, flight_folder, log_name3);
  otherwise
    disp("invalid base")
end

switch compare
  case 1
    file_path2 = fullfile(log_folder, flight_folder, log_name1);
    C_P_Angle = 50;                                % Betaflight gain, scaled by 0.1
  case 2
    file_path2 = fullfile(log_folder, flight_folder, log_name2);
    C_P_Angle = 80;                                % Betaflight gain, scaled by 0.1
  case 3
    file_path2 = fullfile(log_folder, flight_folder, log_name3);
    C_P_Angle = 100;                                % Betaflight gain, scaled by 0.1
  otherwise
    disp("invalid compare")
end

%% Gain labels (for plot legends / metrics)
gains_all    = [50, 80, 100];   % maps log_name1/2/3 -> Betaflight angle P gain
gain_base    = gains_all(base);
gain_compare = C_P_Angle;       % gain of the compare flight

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

%% Sampling times
Ts      = para1.looptime * 1.0e-6;                 % Gyro loop
Ts_cntr = para1.pid_process_denom * Ts;            % Control loop
Ts_log  = para1.frameIntervalPDenom * Ts_cntr;     % Logging loop

%% Time vector
time1 = (flight1(:, ind1.time) - flight1(1, ind1.time)) * 1.0e-6;
time2 = (flight2(:, ind2.time) - flight2(1, ind2.time)) * 1.0e-6;

%% Define axis
axis = 1;   % roll = 1, pitch = 2

%% Debug indices
sinarg1       = ind1.debug(1);
currentAngle1 = [ind1.debug(5), ind1.debug(7)];
angleTarget1  = [ind1.debug(6), ind1.debug(8)];

sinarg2       = ind2.debug(1);
currentAngle2 = [ind2.debug(5), ind2.debug(7)];
angleTarget2  = [ind2.debug(6), ind2.debug(8)];

%% Scale flight 1 data
flight1(:, sinarg1)              = flight1(:, sinarg1) / 5e3;
flight1(:, currentAngle1(axis))  = flight1(:, currentAngle1(axis)) * 0.1;
flight1(:, ind1.setpoint(axis))  = flight1(:, ind1.setpoint(axis)) * 0.1;
flight1(:, angleTarget1(axis))   = flight1(:, angleTarget1(axis)) * 0.1;
flight1(:, ind1.heading(axis))   = flight1(:, ind1.heading(axis)) * 100;
flight1(:, ind1.gyroADC(axis))   = flight1(:, ind1.gyroADC(axis)) * 0.1;

%% Scale flight 2 data
flight2(:, sinarg2)              = flight2(:, sinarg2) / 5e3;
flight2(:, currentAngle2(axis))  = flight2(:, currentAngle2(axis)) * 0.1;
flight2(:, ind2.setpoint(axis))  = flight2(:, ind2.setpoint(axis)) * 0.1;
flight2(:, angleTarget2(axis))   = flight2(:, angleTarget2(axis)) * 0.1;
flight2(:, ind2.heading(axis))   = flight2(:, ind2.heading(axis)) * 100;
flight2(:, ind2.gyroADC(axis))   = flight2(:, ind2.gyroADC(axis)) * 0.1;

%% Evaluation masks
ind_eval1 = get_ind_eval(flight1(:, sinarg1), flight1(:, ind1.gyroADC(axis)));
ind_eval2 = get_ind_eval(flight2(:, sinarg2), flight2(:, ind2.gyroADC(axis)));

sinarg_ax1 = flight1(:, sinarg1);
sinarg_ax1(~ind_eval1) = 0;

sinarg_ax2 = flight2(:, sinarg2);
sinarg_ax2(~ind_eval2) = 0;

idx1 = find(ind_eval1);
idx2 = find(ind_eval2);

%% Frequency response estimation settings
Nest     = round(2 / Ts_log);          % Window length in samples
Noverlap = floor(0.9 * Nest);          % Overlap
window   = hann(Nest, 'periodic');     % Hann window

%% Excitation filter
Dlp = sqrt(3) / 2;                     % Damping ratio
wlp = 2 * pi * 10;                     % Cutoff frequency [rad/s]

Glp = c2d(tf(wlp^2, [1 2*Dlp*wlp wlp^2]), Ts_log, 'tustin');

%% =========================
%% Flight 1
%% =========================

% Closed loop transfer function
w1   = flight1(:, angleTarget1(axis));
inp1 = apply_rotfiltfilt(Glp, sinarg_ax1, w1);

y1   = flight1(:, currentAngle1(axis));
out1 = apply_rotfiltfilt(Glp, sinarg_ax1, y1);

[T_ax1, C_T_ax1] = estimate_frequency_response(inp1(idx1), out1(idx1), ...
    window, Noverlap, Nest, Ts_log);

% Plant
v1     = flight1(:, ind1.gyroADC(axis));
out_v1 = apply_rotfiltfilt(Glp, sinarg_ax1, v1);

[G_wv1, C_G_wv1] = estimate_frequency_response(inp1(idx1), out_v1(idx1), ...
    window, Noverlap, Nest, Ts_log);

P_angle1 = T_ax1 / G_wv1;

% Controller
c1     = flight1(:, ind1.setpoint(axis));
out_c1 = apply_rotfiltfilt(Glp, sinarg_ax1, c1);

[G_wc1, C_G_wc1] = estimate_frequency_response(inp1(idx1), out_c1(idx1), ...
    window, Noverlap, Nest, Ts_log);

Cp_ax1 = G_wc1 / (1 - T_ax1);

% Gyro loop transfer function
T_gy1 = G_wv1 / G_wc1;

[T_gy1, C_G_wc1] = estimate_frequency_response(out_c1(idx1), out_v1(idx1), ...
    window, Noverlap, Nest, Ts_log);

%% =========================
%% Flight 2
%% =========================

% Closed loop transfer function
w2   = flight2(:, angleTarget2(axis));
inp2 = apply_rotfiltfilt(Glp, sinarg_ax2, w2);

y2   = flight2(:, currentAngle2(axis));
out2 = apply_rotfiltfilt(Glp, sinarg_ax2, y2);

[T_ax2, C_T_ax2] = estimate_frequency_response(inp2(idx2), out2(idx2), ...
    window, Noverlap, Nest, Ts_log);

% Plant
v2     = flight2(:, ind2.gyroADC(axis));
out_v2 = apply_rotfiltfilt(Glp, sinarg_ax2, v2);

[G_wv2, C_G_wv2] = estimate_frequency_response(inp2(idx2), out_v2(idx2), ...
    window, Noverlap, Nest, Ts_log);

P_angle2 = T_ax2 / G_wv2;

% Controller
c2     = flight2(:, ind2.setpoint(axis));
out_c2 = apply_rotfiltfilt(Glp, sinarg_ax2, c2);

[G_wc2, C_G_wc2] = estimate_frequency_response(inp2(idx2), out_c2(idx2), ...
    window, Noverlap, Nest, Ts_log);

Cp_ax2 = G_wc2 / (1 - T_ax2);

% Gyro loop transfer function
T_gy2 = G_wv2 / G_wc2;

%% Analytical transfer function
f = T_ax1.Frequency * 2 * pi;                  % Angular frequency [rad/s]

C_P_Angle_frd = frd(C_P_Angle * 0.1 * ones(size(f)), f, Ts_cntr);

fc = 50;                                       % Hz
Gf_ana = get_filter('pt3', fc, Ts_cntr);

C_Angle_ana = C_P_Angle_frd * Gf_ana;
C_Angle_ana = downsample_frd(C_Angle_ana, Ts_log, T_ax1.Frequency);

% Analytical closed-loop TF based on flight 1
T_ana1 = (C_Angle_ana * T_gy1 * P_angle1) / (1 + C_Angle_ana * T_gy1 * P_angle1);
T_ana2 = (C_Angle_ana * T_gy2 * P_angle2) / (1 + C_Angle_ana * T_gy2 * P_angle2);

%% Tuning
P_new = C_P_Angle;               % New gain
angle_lpf_hz = 50;         % New cutoff frequency

C_P_Angle_new_frd = frd(P_new * 0.1 * ones(size(f)), f, Ts_cntr);
Gf_new = get_filter('pt3', angle_lpf_hz, Ts_cntr);

C_Angle_new = C_P_Angle_new_frd * Gf_new;
C_Angle_new = downsample_frd(C_Angle_new, Ts_log, T_ax1.Frequency);

T_new1 = (C_Angle_new * T_gy1 * P_angle1) / (1 + C_Angle_new * T_gy1 * P_angle1);
T_new2 = (C_Angle_new * T_gy2 * P_angle2) / (1 + C_Angle_new * T_gy2 * P_angle2);

%% Step responses
fmax = 400;

step_time = (0:Nest-1) .* Ts_log;
T_mean = 0.1 * [-1, 1] + (Nest * Ts_log) / 2;

step_resp = [ ...
    calculate_step_response_from_frd(T_ax1,  fmax), ...   % measured base
    calculate_step_response_from_frd(T_ana1, fmax), ...   % predicted compare (base plant, compare gain)
    calculate_step_response_from_frd(T_ax2,  fmax)];      % measured compare

step_resp_mean = mean(step_resp(step_time > T_mean(1) & step_time < T_mean(2), :), 1);
step_resp_meas = step_resp ./ step_resp_mean;

%% Plot
figure(1);
plot(step_time, step_resp_meas, 'LineWidth', 1.2);
grid on;
title('Angle step response');
xlim([0 1])
xlabel('Time [s]');
ylabel('Angle [deg]');
legend(sprintf('Measured P=%d', gain_base), ...
       sprintf('Calculated P=%d', gain_compare), ...
       sprintf('Measured P=%d', gain_compare), ...
    'Location', 'best');

figure(2)
bode(Cp_ax1,C_Angle_ana, C_Angle_new);

%% Plant identification (Bode magnitude / phase / coherence) - base flight
% Mirrors the althold plant-ID figure. The identified angle plant
% P_angle1 = T_ax1 / G_wv1, so the reliability of the estimate depends on the
% coherence of both factor estimates -> joint coherence = C_T_ax1 .* C_G_wv1.
f_plant     = squeeze(P_angle1.Frequency);
P_id        = squeeze(P_angle1.ResponseData);
C_P         = squeeze(C_T_ax1.ResponseData) .* squeeze(C_G_wv1.ResponseData);
mag_plant   = 20 * log10(abs(P_id));
phase_plant = angle(P_id) * 180/pi;

pos_bode = [0.13, 0.58, 0.78, 0.32; ...
            0.13, 0.32, 0.78, 0.22; ...
            0.13, 0.10, 0.78, 0.16];

figure(3)

axp(1) = subplot('Position', pos_bode(1, :));
semilogx(f_plant, mag_plant, 'LineWidth', 1.5);
grid on
ylabel('Magnitude [dB]')
title(sprintf('Angle plant identification (base P=%d)', gain_base))

axp(2) = subplot('Position', pos_bode(2, :));
semilogx(f_plant, phase_plant, 'LineWidth', 1.5);
grid on
ylabel('Phase [deg]')

axp(3) = subplot('Position', pos_bode(3, :));
semilogx(f_plant, C_P, 'LineWidth', 1.5);
grid on
ylabel('Coherence [-]')
xlabel('Frequency [Hz]')
ylim([0 1])

linkaxes(axp, 'x')
xlim(axp(1), [1 100])   % adjust to the angle chirp band if needed


%% Numerical metrics for thesis Results section (Angle)
% Set base/compare at the top of the script and re-run once per case to fill
% the angle step-response table (tab:angle_step):
%   - moderate change: base=2 (P=80), compare=3 (P=100)
%   - larger change:   base=2 (P=80), compare=1 (P=50)
% Copy each console block into the LaTeX draft so the Results section reports
% measured numbers rather than eyeballed plot readings.
%
% step_resp_meas columns (see step-response section above):
%   col1 = T_ax1  -> Measured base    (base flight, gain_base)
%   col2 = T_ana1 -> Calculated       (predicted at gain_compare from the base plant)
%   col3 = T_ax2  -> Measured compare (compare flight, gain_compare)

fprintf('\n========================================\n');
fprintf('ANGLE METRICS  axis=%d (1=roll, 2=pitch)\n', axis);
fprintf('  base P=%d   compare P=%d   angle LPF=%d Hz\n', gain_base, gain_compare, angle_lpf_hz);
fprintf('  eval window  base: %.2f s (%d samples)   compare: %.2f s (%d samples)   Ts=%.4f s\n', ...
    nnz(ind_eval1)*Ts_log, nnz(ind_eval1), nnz(ind_eval2)*Ts_log, nnz(ind_eval2), Ts_log);
fprintf('========================================\n');

labels_step = {'MeasuredBase', 'Calculated', 'MeasuredCompare'};
fprintf('  -- Step response (normalised to steady state = 1.0) --\n');
for k = 1:size(step_resp_meas, 2)
    y = step_resp_meas(:, k);
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
    fprintf('     %-16s  t_rise=%.3f s  t_settle=%.3f s  overshoot=%.1f %%\n', ...
        labels_step{k}, t_rise, t_settle, overshoot_pct);
end
fprintf('========================================\n\n');
