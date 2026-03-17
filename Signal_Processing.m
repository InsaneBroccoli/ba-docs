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
ylabel('Amplitude [deg/s]')

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
ylabel('Amplitude [deg/s]')

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
noise_std = 2;                      % standard deviation
noise = noise_std * randn(size(t)); % white Gaussian noise

% Measured output
y_meas = y_ideal + noise;


%% Transferfunction through direct measurement

u = x_e_f(:);      % force column vector
y = y_meas(:);     % force column vector

U = fft(u);
Y = fft(y);

G_est = Y ./ U;

N = length(U);
f = (0:N-1)*(fs/N);

% only positive frequencies
idx = 1:floor(N/2);

figure(4)
subplot(2,1,1)
semilogx(f(idx),20*log10(abs(G_est(idx))))
grid on
ylabel('Magnitude [dB]')
title('Direct Transfer Function Estimate')

subplot(2,1,2)
semilogx(f(idx),angle(G_est(idx))*180/pi)
grid on
ylabel('Phase [deg]')
xlabel('Frequency [Hz]')