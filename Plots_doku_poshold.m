%% Initialize workspace
clc;
clear variables;
close all;

addpath('/home/janick-dort/Dokumente/Studium_ZHAW/BA/bf_controller_tuning/lib/');
addpath(genpath('/home/janick-dort/Dokumente/Studium_ZHAW/BA/bf_controller_tuning'));
addpath('../bf_controller_tuning/lib/');

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

log_folder    = '../bf_controller_tuning/logs';
flight_folder = '20260529';

log_name1 = 'poshold-default.csv';
log_name2 = 'poshold-tuned.csv';

file_path1 = fullfile(log_folder, flight_folder, log_name1);
file_path2 = fullfile(log_folder, flight_folder, log_name2);

axis = 1;   % roll = 1, pitch = 2

%% Load and process header information
[para1, Nheader1, ind1, ind_cntr1] = extract_header_information(file_path1);
[para2, Nheader2, ind2, ind_cntr2] = extract_header_information(file_path2);

%% Load data from CSV or cached MAT file
[~, base1, ~] = fileparts(file_path1);
mat_path1 = [base1 '.mat'];  % Speichert direkt im aktuellen Arbeitsverzeichnis

[~, base2, ~] = fileparts(file_path2);
mat_path2 = [base2 '.mat'];  % Speichert direkt im aktuellen Arbeitsverzeichnis

% Case names for the unified GoF / step legends (match the Results tables)
name_base    = 'baseline';   % poshold-default.csv was flown at the baseline gains
name_compare = 'proposed';   % poshold-tuned.csv was flown at the proposed gains

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
I_f1 = 50;
D_f1 = 42;
A_f1 = 19;
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

P_f2 = P_f1;
I_f2 = I_f1;
D_f2 = D_f1;
A_f2 = A_f1;
fc_pt1_f2 = fc_pt1_f1;


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
legend(sprintf('Calculated %s', name_compare), sprintf('Measured %s', name_base), sprintf('Measured %s', name_compare), 'Location','best');
grid on;

ax(2) = subplot(2,2,2);
bodemag(ax(2), CL_f1.S, CL_f2.S, omega_bode, opt);
title('Sensitivity S')
legend(sprintf('Calculated %s', name_base), sprintf('Calculated %s', name_compare), 'Location','best')
grid on

ax(3) = subplot(2,2,3);
bodemag(ax(3), CL_f1.SC, CL_f2.SC, omega_bode, opt);
title('Controller Effort SC');
legend(sprintf('Calculated %s', name_base), sprintf('Calculated %s', name_compare), 'Location','best');
grid on;

ax(4) = subplot(2,2,4);
bodemag(ax(4), CL_f1.SP, CL_f2.SP, omega_bode, opt);
title('Compliance SP');
legend(sprintf('Calculated %s', name_base), sprintf('Calculated %s', name_compare), 'Location','best');
grid on;

linkaxes(ax,'x');
xlim(ax(1), [3e-2 10]);
sgt = sgtitle('Gang of Four - Position Hold');

style_doku_fig(gcf, 16, 12, 16, 1.2);
xlim([0.07 4])
set(sgt, 'FontWeight', 'bold', 'FontSize', 20);   % overall title: bold, larger than base

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
plot(step_time, step_resp)
grid on
ylabel('Position [cm]')
xlabel('Time [s]')
title('Step Response Position Hold')
legend(sprintf('Measured %s', name_compare), sprintf('Calculated %s', name_compare), sprintf('Measured %s', name_base), ...
       'Location', 'best')
ylim([-0.2 1.6]); xlim([0 frame/2]);

style_doku_fig(gcf, 16, 7, 16, 1.2);


%% Shared labels and chirp-window time vectors
label_base    = base1;
label_compare = base2;

t_m1 = time1(idx1) - time1(idx1(1));
t_m2 = time2(idx2) - time2(idx2(1));

%% Plant identification (Bode magnitude / phase / coherence) - base flight
% Mirrors the althold plant-ID figure. Plant = T / G_uw, so the reliability of
% the estimate depends on both factor coherences -> joint coherence below.
f_plant     = squeeze(Plant_f1.Frequency);
P_id        = squeeze(Plant_f1.ResponseData);
C_P         = squeeze(C_uw_f1.ResponseData) .* squeeze(C_T_f1.ResponseData);
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
title('Position-hold plant identification')

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
xlim(axp(1), [min(f_bode) 10])

%% Numerical metrics for thesis Results section (Position Hold)
% Mirrors the althold metric suite (Plots_doku_althold.m). Set the two flight
% logs and the analytical PIDA gains above, run, and copy the console block
% into the LaTeX draft so the Results section reports measured numbers rather
% than eyeballed plot readings. Flight1 = baseline (plant identified here);
% Flight2 = measured proposed tuning; CL_f1.T = predicted proposed tuning.

fprintf('\n========================================\n');
fprintf('POSHOLD METRICS  axis=%d (1=roll/LON, 2=pitch/LAT)\n', axis);
fprintf('  Flight1 PIDA: P=%d I=%d D=%d A=%d  (fc_pt1=%.2f Hz)\n', P_f1, I_f1, D_f1, A_f1, fc_pt1_f1);
fprintf('  Flight2 PIDA: P=%d I=%d D=%d A=%d  (fc_pt1=%.2f Hz)\n', P_f2, I_f2, D_f2, A_f2, fc_pt1_f2);
fprintf('  Chirp window  F1: %.2f s (%d samples)   F2: %.2f s (%d samples)   Ts=%.4f s\n', ...
    t_m1(end), numel(t_m1), t_m2(end), numel(t_m2), Ts_log);
fprintf('========================================\n');

% --- Step response metrics (rise / settle / overshoot) ---
% step_resp columns (see step-response section above): [Measured F2, Calculated F1, Measured F1]
labels_step = {'MeasuredF2', 'CalculatedF1', 'MeasuredF1'};
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
    fprintf('     %-13s  t_rise=%.3f s  t_settle=%.3f s  overshoot=%.1f %%\n', ...
        labels_step{k}, t_rise, t_settle, overshoot_pct);
end

% --- Gang of Four peaks (linear magnitude evaluated at omega_bode) ---
% Restrict the peak search to the excited band: the chirp ends at 3 Hz and the
% GPS feedback is Nyquist-limited near 5 Hz, so above ~3 Hz the FRD is noise and
% would otherwise yield spurious high-frequency peaks (e.g. the ~4.7 Hz artifact).
f_peak_max = 3;
mask       = f_bode <= f_peak_max;
fb         = f_bode(mask);

ev      = @(sys) abs(squeeze(freqresp(sys, omega_bode(mask))));
peak_db = @(mag) 20*log10(max(mag));
peak_f  = @(mag) fb(find(mag == max(mag), 1));

mag_T_calc1 = ev(CL_f1.T);   mag_T_calc2 = ev(CL_f2.T);
mag_S_calc1 = ev(CL_f1.S);   mag_S_calc2 = ev(CL_f2.S);
mag_SC_c1   = ev(CL_f1.SC);  mag_SC_c2   = ev(CL_f2.SC);
mag_SP_c1   = ev(CL_f1.SP);  mag_SP_c2   = ev(CL_f2.SP);

T_meas1_full = abs(squeeze(T_f1.ResponseData));
T_meas2_full = abs(squeeze(T_f2.ResponseData));
mag_T_meas1  = T_meas1_full(mask);
mag_T_meas2  = T_meas2_full(mask);

fprintf('  -- Gang of Four peak magnitudes (peak search restricted to f <= %.1f Hz) --\n', f_peak_max);
fprintf('     T  calc %-10s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_T_calc1), peak_f(mag_T_calc1));
fprintf('     T  calc %-10s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_T_calc2), peak_f(mag_T_calc2));
fprintf('     T  meas %-10s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_T_meas1), peak_f(mag_T_meas1));
fprintf('     T  meas %-10s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_T_meas2), peak_f(mag_T_meas2));
fprintf('     S  calc %-10s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_S_calc1), peak_f(mag_S_calc1));
fprintf('     S  calc %-10s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_S_calc2), peak_f(mag_S_calc2));
fprintf('     SC calc %-10s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_SC_c1),   peak_f(mag_SC_c1));
fprintf('     SC calc %-10s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_SC_c2),   peak_f(mag_SC_c2));
fprintf('     SP calc %-10s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_SP_c1),   peak_f(mag_SP_c1));
fprintf('     SP calc %-10s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_SP_c2),   peak_f(mag_SP_c2));

% --- Plant identification (base flight only) ---
f_p   = squeeze(Plant_f1.Frequency);
P_lin = abs(squeeze(Plant_f1.ResponseData));
P_dB  = 20*log10(P_lin);
P_ph  = angle(squeeze(Plant_f1.ResponseData)) * 180/pi;
% Joint coherence: Plant = T / G_uw, reliability depends on both factors.
coh_p = squeeze(C_uw_f1.ResponseData) .* squeeze(C_T_f1.ResponseData);

ref_freqs = [0.1, 0.3, 1.0, 3.0];
fprintf('  -- Plant magnitude / phase / coherence at reference frequencies --\n');
for fr = ref_freqs
    [~, ii] = min(abs(f_p - fr));
    fprintf('     |P| @ %.2f Hz: %+6.2f dB   phase %+6.1f deg   coherence %.3f\n', ...
        f_p(ii), P_dB(ii), P_ph(ii), coh_p(ii));
end

% Slope estimate between 0.1 and 1.0 Hz (descriptive only)
[~, i1] = min(abs(f_p - 0.1));
[~, i2] = min(abs(f_p - 1.0));
slope = (P_dB(i2) - P_dB(i1)) / log10(f_p(i2) / f_p(i1));
fprintf('     Plant slope between 0.1 and 1.0 Hz: %.1f dB/decade\n', slope);

% Coherence band: contiguous low-frequency band where coherence > 0.8
coh_thresh = 0.8;
above = coh_p > coh_thresh;
if above(1)
    drop = find(~above, 1, 'first');
    if isempty(drop)
        f_coh_hi = f_p(end);
    else
        f_coh_hi = f_p(drop - 1);
    end
    fprintf('     Coherence > %.2f from %.3f Hz up to %.3f Hz\n', coh_thresh, f_p(1), f_coh_hi);
else
    fprintf('     Coherence does not start above %.2f at lowest bin (%.3f Hz, coh=%.3f)\n', ...
        coh_thresh, f_p(1), coh_p(1));
end

fprintf('========================================\n\n');


%% Local functions

function style_doku_fig(figh, w_cm, h_cm, fs, lw)
% Unified styling for the documentation figures (Gang of Four + step response).
% Pins the figure size (cm) and the font / line sizes so the manually exported
% PNGs come out at identical dimensions across all Plots_doku_* scripts.
% Call as the last statement of a figure block (after bodemag/linkaxes/sgtitle).
    set(figh, 'Units', 'centimeters');
    p = get(figh, 'Position');
    set(figh, 'Position', [p(1) p(2) w_cm h_cm]);
    set(findall(figh, 'Type', 'line'), 'LineWidth', lw);          % bodemag curves + plot() lines
    set(findall(figh, '-property', 'FontSize'), 'FontSize', fs);  % base font: axes, labels, legend

    % Subplot titles: bold and slightly larger than the base font. bodemag can
    % leave uneven title-to-plot gaps between panels, so after styling we pull
    % every title up to the largest gap, giving identical spacing on all axes.
    axs = findall(figh, 'Type', 'axes');
    set([axs.Title], 'FontWeight', 'bold', 'FontSize', fs + 1, 'Units', 'normalized');
    ytitle = arrayfun(@(a) a.Title.Position(2), axs);
    for k = 1:numel(axs)
        axs(k).Title.Position(2) = max(ytitle);
    end
end
