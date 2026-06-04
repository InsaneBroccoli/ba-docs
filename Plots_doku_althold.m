%% Initialize workspace
clc;
clear variables;
close all;

% addpath('/home/janick-dort/Dokumente/Studium_ZHAW/BA/bf_controller_tuning/lib/');
% addpath(genpath('/home/janick-dort/Dokumente/Studium_ZHAW/BA/bf_controller_tuning'));

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

% log_folder    = 'logs';
% flight_folder1 = '20260528';
% flight_folder2 = '20260528';
%
% log_name1 = 'althold-default.csv';
% log_name2 = 'althold-tuned.csv';

log_folder = '../bf_controller_tuning/logs/';
flight_folder = '20260528';

log_name1 = 'althold-default.csv'; % 1
log_name2 = 'althold-tuned.csv';   % 2
log_name3 = 'althold-medium.csv';  % 3
log_name4 = 'althold-bad.csv';     % 4

base    = 1; % base flight
compare = 2; % flight to compare base against

switch base
  case 1
    file_path1 = fullfile(log_folder, flight_folder, log_name1);
  case 2
    file_path1 = fullfile(log_folder, flight_folder, log_name2);
  case 3
    file_path1 = fullfile(log_folder, flight_folder, log_name3);
  case 4
    file_path1 = fullfile(log_folder, flight_folder, log_name4);
  otherwise
    disp("invalid base")
end

switch compare
  case 1
    file_path2 = fullfile(log_folder, flight_folder, log_name1);
    % Analytical PI + D (current tune)
    P_f1 = 15;
    I_f1 = 15;
    D_f1 = 15;
  case 2
    file_path2 = fullfile(log_folder, flight_folder, log_name2);
    % Analytical PI + D (current tune)
    P_f1 = 18;
    I_f1 = 16;
    D_f1 = 16;
  case 3
    file_path2 = fullfile(log_folder, flight_folder, log_name3);
    % Analytical PI + D (current tune)
    P_f1 = 13;
    I_f1 = 13;
    D_f1 = 13;
  case 4
    file_path2 = fullfile(log_folder, flight_folder, log_name4);
    % Analytical PI + D (current tune)
    P_f1 = 10;
    I_f1 = 10;
    D_f1 = 10;
  otherwise
    disp("invalid compare")
end

%% Load and process header information
[para1, Nheader1, ind1, ind_cntr1] = extract_header_information(file_path1);
[para2, Nheader2, ind2, ind_cntr2] = extract_header_information(file_path2);

%% Load data from CSV or cached MAT file
[~, base1, ~] = fileparts(file_path1);
mat_path1 = [base1 '.mat'];  % Speichert direkt im aktuellen Arbeitsverzeichnis

[~, base2, ~] = fileparts(file_path2);
mat_path2 = [base2 '.mat'];  % Speichert direkt im aktuellen Arbeitsverzeichnis

% Case names for the unified GoF / step legends (match the Results tables: default/tuned/medium/bad)
name_base    = erase(base1, 'althold-');
name_compare = erase(base2, 'althold-');

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

%% Get log Time
% Derive sample times from the log header. Blackbox frame period is
% looptime * pid_process_denom * frameIntervalPDenom; althold updates at
% 100 Hz, so we decimate down to that rate and run the controller analysis
% at the same Ts.
Ts_log_raw = para1.looptime * 1e-6 * para1.pid_process_denom * para1.frameIntervalPDenom;
dec        = round((1/Ts_log_raw) / 100);
flight1       = flight1(1:dec:end, :);
flight2       = flight2(1:dec:end, :);
Ts_log     = Ts_log_raw * dec;
Ts_cntr    = Ts_log;   % althold control loop runs at logging rate

% ind.time column is in microseconds (Betaflight blackbox convention).
time1 = (flight1(:, ind1.time) - flight1(1, ind1.time)) * 1e-6;
time2 = (flight2(:, ind2.time) - flight2(1, ind2.time)) * 1e-6;

%% Debug Scaling
% Undo firmware-side debug scaling so all signals are in physical units.
% Firmware logs (alt_hold_multirotor.c, autopilot_multirotor.c)
sinarg1          = flight1(:,ind1.debug(1)) / 5e3;
meas_alt1        = flight1(:,ind1.debug(2));
set_alt1         = flight1(:,ind1.debug(3));
meas_pi1         = flight1(:,ind1.debug(4));
throttle_out1    = flight1(:,ind1.debug(6)) / 1e3;   % normalised throttle 0..1
vertical_v1      = flight1(:,ind1.debug(7)) / 10;    % cm/s
throttle_offset1 = flight1(:,ind1.debug(8));         % PWM units

sinarg2          = flight2(:,ind2.debug(1)) / 5e3;
meas_alt2        = flight2(:,ind2.debug(2));
set_alt2         = flight2(:,ind2.debug(3));
meas_pi2         = flight2(:,ind2.debug(4));
throttle_out2    = flight2(:,ind2.debug(6)) / 1e3;   % normalised throttle 0..1
vertical_v2      = flight2(:,ind2.debug(7)) / 10;    % cm/s
throttle_offset2 = flight2(:,ind2.debug(8));         % PWM units

%% Estimate Transfer Functions

% Welch parameters
frame    = 15;
Nest     = round(frame / (Ts_log));
Noverlap = floor(0.9 * Nest);
window   = hann(Nest, 'periodic');

% Low-pass filter for rotating-frame filtering
Dlp = sqrt(3) / 2;
wlp = 2 * pi * 10;
Glp = c2d(tf(wlp^2, [1 2*Dlp*wlp wlp^2]), Ts_log, 'tustin');

% Get only chirp signal
sinarg1 = fix_signal(sinarg1);
idx1 = get_ind_eval(sinarg1, meas_alt1);

sinarg2 = fix_signal(sinarg2);
idx2 = get_ind_eval(sinarg2, meas_alt2);

% Build sinarg mask (zero outside chirp window)
sinarg_ax1 = sinarg1;
sinarg_ax1(~idx1) = 0;

sinarg_ax2 = sinarg2;
sinarg_ax2(~idx2) = 0;

%% Filter Signals

inp1   = apply_rotfiltfilt(Glp, sinarg_ax1, set_alt1);
out_y1 = apply_rotfiltfilt(Glp, sinarg_ax1, meas_alt1);
out_u1 = apply_rotfiltfilt(Glp, sinarg_ax1, throttle_offset1);

inp2   = apply_rotfiltfilt(Glp, sinarg_ax2, set_alt2);
out_y2 = apply_rotfiltfilt(Glp, sinarg_ax2, meas_alt2);
out_u2 = apply_rotfiltfilt(Glp, sinarg_ax2, throttle_offset2);

%% Estimation Transferfunction T

[T_f1, C_T_f1] = estimate_frequency_response(inp1(idx1), out_y1(idx1), ...
  window, Noverlap, Nest, Ts_log);

[T_f2, C_T_f2] = estimate_frequency_response(inp2(idx2), out_y2(idx2), ...
  window, Noverlap, Nest, Ts_log);

f_bode = squeeze(C_T_f1.Frequency);
omega_bode = 2*pi*f_bode;

%% Estimation Plant

[Guw_f1, C_uw_f1] = estimate_frequency_response(inp1(idx1), out_u1(idx1), ...
  window, Noverlap, Nest, Ts_log);

[Guw_f2, C_uw_f2] = estimate_frequency_response(inp2(idx2), out_u2(idx2), ...
  window, Noverlap, Nest, Ts_log);

Plant_f1 = T_f1 / Guw_f1;
Plant_f2 = T_f2 / Guw_f2;

%% Controller Settings Flight 1

fc_pt2_f1 = 1;
[Cpi_f1, Cd_f1] = calculate_althold_controllers( ...
  P_f1,...
  I_f1,...
  D_f1,...
  fc_pt2_f1,...
  Ts_cntr,...
  Ts_log,...
  Plant_f1.Frequency);

%% Controller Settings Flight 2

P_f2 = P_f1;
I_f2 = I_f1;
D_f2 = D_f1;
fc_pt2_f2 = 1;

[Cpi_f2, Cd_f2] = calculate_althold_controllers( ...
  P_f2,...
  I_f2,...
  D_f2,...
  fc_pt2_f2,...
  Ts_cntr,...
  Ts_log,...
  Plant_f2.Frequency);

%% Get Closed Loop Data

CL_f1 = calculate_closed_loop(Cpi_f1, tf(1,1,Ts_log), Plant_f1, tf(1,1,Ts_log), Cd_f1);
CL_f2 = calculate_closed_loop(Cpi_f2, tf(1,1,Ts_log), Plant_f2, tf(1,1,Ts_log), Cd_f2);

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
ylim([-10 7])
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
xlim(ax(1), [min(f_bode) 10])
sgt = sgtitle('Gang of Four - Altitude Hold');

style_doku_fig(gcf, 16, 12, 16, 1.2);
set(sgt, 'FontWeight', 'bold', 'FontSize', 20);   % overall title: bold, larger than base


%% Step responses
fmax = 3;

step_time = (0:Nest-1) .* Ts_log;
T_mean = 0.1 * [-1, 1] + (Nest * Ts_log) / 2;

step_resp = [ ...
    calculate_step_response_from_frd(T_f2,  fmax), ...
    calculate_step_response_from_frd(CL_f1.T, fmax), ...
    calculate_step_response_from_frd(T_f1, fmax)];

step_resp_mean = mean(step_resp(step_time > T_mean(1) & step_time < T_mean(2),:));
step_resp = step_resp ./ step_resp_mean;

figure(2)
plot(step_time, step_resp)
grid on
ylabel('Altitude [cm]')
xlabel('Time [s]')
title('Step Response Altitude Hold')
legend(sprintf('Measured %s', name_compare), sprintf('Calculated %s', name_compare), sprintf('Measured %s', name_base), ...
       'Location', 'best')
ylim([-0.1 1.25]); xlim([0 frame/2]);

style_doku_fig(gcf, 16, 7, 16, 1.2);


%% Plant identification (Bode magnitude / phase / coherence) - base flight

f_plant     = squeeze(Plant_f1.Frequency);
P           = squeeze(Plant_f1.ResponseData);
% Joint coherence (matches the convention in altitude_hold_tuning.m):
% reliability of P = T / Guw depends on both factor coherences.
C_P         = squeeze(C_uw_f1.ResponseData) .* squeeze(C_T_f1.ResponseData);
mag_plant   = 20 * log10(abs(P));
phase_plant = angle(P) * 180/pi;

label_base = erase(base1, 'althold-');

pos_bode = [0.13, 0.58, 0.78, 0.32; ...
            0.13, 0.32, 0.78, 0.22; ...
            0.13, 0.10, 0.78, 0.16];

figure(3)

axp(1) = subplot('Position', pos_bode(1, :));
semilogx(f_plant, mag_plant, 'LineWidth', 1.5);
grid on
ylabel('Magnitude [dB]')
title(['Altitude-Hold Plant Identification (' label_base ')'])

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


%% Time-domain altitude trace (base on top, compare on bottom)

label_compare = erase(base2, 'althold-');

t0_1 = time1(find(idx1, 1, 'first'));
t_m1 = time1(idx1) - t0_1;

t0_2 = time2(find(idx2, 1, 'first'));
t_m2 = time2(idx2) - t0_2;

figure(4)

axa(1) = subplot(2, 1, 1);
plot(t_m1, set_alt1(idx1),  'LineWidth', 1.2); hold on
plot(t_m1, meas_alt1(idx1), 'LineWidth', 1.2); hold off
grid on
ylabel('Altitude [cm]')
title(label_base)
legend('Setpoint', 'Measured', 'Location', 'best')

axa(2) = subplot(2, 1, 2);
plot(t_m2, set_alt2(idx2),  'LineWidth', 1.2); hold on
plot(t_m2, meas_alt2(idx2), 'LineWidth', 1.2); hold off
grid on
ylabel('Altitude [cm]')
xlabel('Time [s]')
title(label_compare)
legend('Setpoint', 'Measured', 'Location', 'best')

linkaxes(axa, 'x')
sgtitle('Altitude tracking over chirp window')


%% Control-effort trace (base + compare overlaid)

figure(5)
plot(t_m1, throttle_offset1(idx1), 'LineWidth', 1.2); hold on
plot(t_m2, throttle_offset2(idx2), 'LineWidth', 1.2); hold off
grid on
xlabel('Time [s]')
ylabel('Throttle offset [PWM]')
title('Control effort over chirp window')
legend(label_base, label_compare, 'Location', 'best')


%% Numerical metrics for thesis Results section
% Run this script with compare = 2, then 3, then 4 (base stays = 1).
% Copy the console blocks into the LaTeX draft so the Results section
% reports measured numbers rather than eyeballed plot readings.

fprintf('\n========================================\n');
fprintf('METRICS  base=%s  compare=%s\n', label_base, label_compare);
fprintf('  (compare-flight controller gains: P=%d, I=%d, D=%d)\n', P_f1, I_f1, D_f1);
fprintf('========================================\n');

% --- Chirp window duration (reported once) ---
fprintf('  Chirp window (base):    %.2f s (%d samples @ Ts=%.4f s)\n', ...
    t_m1(end), numel(t_m1), Ts_log);
fprintf('  Chirp window (compare): %.2f s (%d samples @ Ts=%.4f s)\n', ...
    t_m2(end), numel(t_m2), Ts_log);

% --- Step response metrics (rise / settle / overshoot) ---
% step_resp columns (line 291-294): [Measured F2, Calculated F1, Measured F1]
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
    outside = abs(y - y_final) > 0.05;
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

% --- Time-domain tracking error and control effort ---
err1 = set_alt1(idx1) - meas_alt1(idx1);
err2 = set_alt2(idx2) - meas_alt2(idx2);
fprintf('  -- Time-domain tracking (chirp window only) --\n');
fprintf('     RMS tracking error      %-12s: %.2f cm\n', label_base,    sqrt(mean(err1.^2)));
fprintf('     RMS tracking error      %-12s: %.2f cm\n', label_compare, sqrt(mean(err2.^2)));
fprintf('     Peak |setpt - meas|     %-12s: %.1f cm\n', label_base,    max(abs(err1)));
fprintf('     Peak |setpt - meas|     %-12s: %.1f cm\n', label_compare, max(abs(err2)));
fprintf('     Peak throttle offset    %-12s: %.0f PWM\n', label_base,    max(abs(throttle_offset1(idx1))));
fprintf('     Peak throttle offset    %-12s: %.0f PWM\n', label_compare, max(abs(throttle_offset2(idx2))));

% --- Gang of Four peaks (linear magnitude evaluated at omega_bode) ---
% Restrict the peak search to the displayed band so we don't catch
% numerical-artifact peaks above the plot xlim (the Welch estimate runs
% out to Nyquist ~ 50 Hz, but the figure only shows up to 10 Hz).
f_peak_max = 10;
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
fprintf('     T  calc %-8s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_T_calc1), peak_f(mag_T_calc1));
fprintf('     T  calc %-8s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_T_calc2), peak_f(mag_T_calc2));
fprintf('     T  meas %-8s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_T_meas1), peak_f(mag_T_meas1));
fprintf('     T  meas %-8s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_T_meas2), peak_f(mag_T_meas2));
fprintf('     S  calc %-8s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_S_calc1), peak_f(mag_S_calc1));
fprintf('     S  calc %-8s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_S_calc2), peak_f(mag_S_calc2));
fprintf('     SC calc %-8s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_SC_c1),   peak_f(mag_SC_c1));
fprintf('     SC calc %-8s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_SC_c2),   peak_f(mag_SC_c2));
fprintf('     SP calc %-8s peak %+5.2f dB @ %.3f Hz\n', label_base,    peak_db(mag_SP_c1),   peak_f(mag_SP_c1));
fprintf('     SP calc %-8s peak %+5.2f dB @ %.3f Hz\n', label_compare, peak_db(mag_SP_c2),   peak_f(mag_SP_c2));

% --- Plant identification (base flight only; no compare-flight plant figure) ---
f_p   = squeeze(Plant_f1.Frequency);
P_lin = abs(squeeze(Plant_f1.ResponseData));
P_dB  = 20*log10(P_lin);
P_ph  = angle(squeeze(Plant_f1.ResponseData)) * 180/pi;
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
