%% Chirp signal simulation for thesis figures
clear; clc; close all;

%% Parameters
f0 = 1;        % start frequency [Hz]
f1 = 600;      % end frequency [Hz]
T  = 20;       % duration [s]
fs = 2000;     % sampling frequency [Hz]
A = 230;

t = 0:1/fs:T;

%% Linear chirp
k = (f1 - f0)/ T;

fl = f0 + k * t;

argl = 2*pi*(f0*t+0.5*k*t.^2);

x_l = A*sin(argl);

argl_wrapped = mod(argl, 2*pi);

%% Plot linar chirp

figure(1)
subplot(311)
plot(t,x_l);

title('Chrip Signal');

subplot(312)
plot(t, fl);
title('Frequency');
ylabel('Frequency [Hz]')

subplot(313)
plot(t, argl_wrapped);
title('Wrappt Phase');
ylabel('arg(t) [rad]')
xlabel('Time [s]')


%% Exponential chirp (Betaflight style)
fe = f0 * (f1/f0).^(t/T);

arge = (2*pi*T*f0/log(f1/f0)) * ((f1/f0).^(t/T) - 1);

x_e = A*sin(arge);
arge_wrapped = mod(arge, 2*pi);

%% Plot exponential chirp

figure(2)
subplot(311)
plot(t,x_e);

title('Chrip Signal');

subplot(312)
plot(t, fe);
title('Frequency');
ylabel('Frequency [Hz]')

subplot(313)
plot(t, arge_wrapped);
title('Wrappt Phase');
ylabel('arg(t) [rad]')
xlabel('Time [s]')

%% Lag filter (Betaflight style)

wp = 2*pi*3;    % pole frequency [rad/s]
wz = 2*pi*30;   % zero frequency [rad/s]

s = tf('s');

H = (1 + s/wz) / (1 + s/wp);

Hd = c2d(H,1/fs,'tustin');   % discretize filter

%% Implementation of Lag filter on Chirp

x_e_f = lsim(Hd,x_e,t);   % filtered chirp

figure(3)
plot(t, x_e_f)
xlabel('Time [s]');
ylabel('Amplitude [deg/s]');

%% Transferfunction
% Relevant frequencies
 w2 = 13*2*pi();
 w1 = 16*2*pi();
 wt = 60*2*pi();
        
 % Transfer functions estimated
 G1 = 1 / (s/w1);
 G2 = 1 / (1 + (s/w2));
 Gt = exp(-s * (1/wt));     % dead time
 Gges = G1*G2*Gt;          % total transfer function

%% Disturbance

% Ideal output of the system
y_ideal = lsim(Gges, x_e_f, t);

% Disturbance / measurement noise
noise_std = 20;                          
noise = noise_std * randn(size(y_ideal));   % gleiche Größe wie y_ideal

% Measured output
y_meas = y_ideal + noise;

%% Transfer function through spectral quantities + coherence
U = fft(x_e_f);
Y = fft(y_meas);

Suu = U .* conj(U);
Syu = Y .* conj(U);

G_spec = Syu ./ Suu;

N = length(U);
f = (0:N-1)*(fs/N);

idx = 2:floor(N/2);
idx = idx(f(idx) <= 600);

G_spec = frd(G_spec(idx), 2*pi*f(idx));

figure(5)
bode(Gges, G_spec)
grid on
legend('Real Plant', 'Measured')
xlim([1 600])

%% Apply Rotfiltfilt

fc_lp = 10;                  
[b,a] = butter(2, fc_lp/(fs/2));

y = y_meas(:) - mean(y_meas(:));   % Spaltenvektor
p = exp(1i * arge(:));             % Spaltenvektor

yR = y .* p;
yQ = y .* conj(p);

yR = filtfilt(b, a, yR);
yQ = filtfilt(b, a, yQ);

y_filt = real(0.5 * (yR .* conj(p) + yQ .* p));

Y = fft(y_filt);
Syu = Y .* conj(U);

G_filt = Syu ./ Suu;

G_filt = frd(G_filt(idx), 2*pi*f(idx));

figure(66)
subplot(2,1,1)
plot(t, y, t, y_ideal-mean(y_ideal), LineWidth=1);
title('Unfiltert Signal')
legend('Signal','Real Chirp');


subplot(2,1,2)
plot(t, y_filt, t, y_ideal-mean(y_ideal), LineWidth=1);
title('Filtert Signal')
xlabel('Time [s]')
xlim([0 10])

figure(6)
bode(Gges, G_filt)
grid on
legend('Real Plant', 'Measured')
xlim([1 600])


%% Welch
u = x_e_f(:) - mean(x_e_f);
y = y_filt(:) - mean(y_filt);

Nseg = 1024*4;
Noverlap = round(Nseg * 0.9);

step = Nseg - Noverlap;
win = hann(Nseg);
Nfreq = Nseg/2 + 1;

Suu = zeros(Nfreq,1);
Syu = zeros(Nfreq,1);
Syy = zeros(Nfreq,1);
K = 0;

for k = 1:step:(length(u)-Nseg+1)
    idx = k:k+Nseg-1;
    
    U = fft(u(idx).*win);
    Y = fft(y(idx).*win);
    
    U = U(1:Nfreq);
    Y = Y(1:Nfreq);
    
    Suu = Suu + U .* conj(U);
    Syu = Syu + Y .* conj(U);
    Syy = Syy + Y .* conj(Y);
    
    K = K + 1;
end

Suu = Suu / K;
Syu = Syu / K;
Syy = Syy / K;

G_welch = Syu ./ Suu;
Coh_welch = abs(Syu).^2 ./ (Suu .* Syy);
f = (0:Nseg/2)' * fs / Nseg;

idx = f > 0 & f <= 600;

G_welch_frd = frd(G_welch(idx), f(idx), 'Units', 'Hz');

figure(7)
bode(Gges, G_welch_frd)
grid on
legend('Real Plant', 'Welch Estimate')
xlim([1 600])

figure(8)
plot(f(idx), Coh_welch(idx))
grid on
xlabel('Frequency [Hz]')
ylabel('Coherence [-]')
xlim([0 600])
ylim([0 1.05])