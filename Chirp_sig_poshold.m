%% Chirp signal simulation for thesis figures
clear; clc; close all;

%% Parameters
f0 = 0.05;        % start frequency [Hz]
f1 = 5;      % end frequency [Hz]
T  = 75;       % duration [s]
fs = 2000;     % sampling frequency [Hz]
A = 275;
A_old = 70;

t = 0:1/fs:T;

%% Exponential chirp (Betaflight style)
fe = f0 * (f1/f0).^(t/T);

arge = (2*pi*T*f0/log(f1/f0)) * ((f1/f0).^(t/T) - 1);

x_e = A*sin(arge);
x_e_old = A_old*sin(arge);
arge_wrapped = mod(arge, 2*pi);

%% Lag filter (Betaflight style)

wp_old = 2*pi*1.3;
wz_old = 2*pi*4.8;

wp = 2*pi*0.1;    % pole frequency [rad/s] % 1.3Hz
wz = 2*pi*1.4;   % zero frequency [rad/s] % 4.8Hz

s = tf('s');

H = (1 + s/wz) / (1 + s/wp);
H_old = (1 + s/wz_old) / (1 + s/wp_old);

Hd = c2d(H,1/fs,'tustin');   % discretize filter
Hd_old = c2d(H_old,1/fs,'tustin');   % discretize filter


%% Implementation of Lag filter on Chirp

x_e_f = lsim(Hd,x_e,t);   % filtered chirp
x_e_f_old = lsim(Hd_old,x_e_old,t);   % filtered chirp

figure(1)
plot(t, x_e_f)
xlabel('Time [s]');
ylabel('Amplitude [deg/s]');

figure(2)
plot(t, x_e_f_old)
xlabel('Time [s]');
ylabel('Amplitude [deg/s]');

%% Velocity (derivative)

v_e_f     = gradient(x_e_f, t);
v_e_f_old = gradient(x_e_f_old, t);

figure(3)
plot(t, v_e_f)
xlabel('Time [s]');
ylabel('Velocity [cm/s]');
title('Derivative of filtered chirp')

figure(4)
plot(t, v_e_f_old)
xlabel('Time [s]');
ylabel('Velocity [cm/s]');
title('Derivative of filtered chirp (old)')

%% Acceleration

a_e_f     = gradient(v_e_f, t);
a_e_f_old = gradient(v_e_f_old, t);

figure(5)
plot(t, a_e_f)
xlabel('Time [s]');
ylabel('Velocity [cm/s^2]');
title('Acceleration of filtered chirp')

figure(6)
plot(t, a_e_f_old)
xlabel('Time [s]');
ylabel('Velocity [cm/s^2]');
title('Acceleration of filtered chirp (old)')