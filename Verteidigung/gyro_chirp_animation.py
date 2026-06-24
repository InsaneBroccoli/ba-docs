from pathlib import Path

from manim import *
import numpy as np


# ---------------------------------------------------------------------------
# Render settings
# ---------------------------------------------------------------------------
config.background_color = WHITE
config.frame_width = 16
config.frame_height = 9
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_rate = 30

# Chirp parameters
START_FREQUENCY = 1.0       # Hz
END_FREQUENCY = 600.0       # Hz
CHIRP_DURATION = 20.0       # s
CHIRP_AMPLITUDE = 3.0       # overall amplitude of the injected gyro chirp
MAX_TILT_DEGREES = 20.0     # maximum displayed drone inclination

# Low-frequency scaling followed by a lag filter.
LOW_FREQUENCY_START_SCALE = 0.25  # reduced amplitude at 1 Hz
LOW_FREQUENCY_FULL_SCALE = 3.0    # Hz: low-frequency scaling ends
LAG_POLE_FREQUENCY = 3.0          # Hz
LAG_ZERO_FREQUENCY = 30.0         # Hz

# Example bandwidth of the gyro/rate loop. Adapt this to the measured system.
GYRO_BANDWIDTH = 100.0      # Hz

# Animation timing
CHIRP_RUN_TIME = 20.0
INTRO_WAIT = 2.0
FINAL_WAIT = 3.0

# Visual style
INK = "#111827"
MUTED = "#6B7280"
GRID = "#D1D5DB"
BLUE = "#2563EB"
ORANGE = "#F97316"
GREEN = "#16A34A"
PURPLE = "#7C3AED"
RED = "#DC2626"


class GyroChirp(Scene):
    """Visualise a shaped 1...600 Hz chirp acting on the gyro/rate loop."""

    def construct(self):
        # ------------------------------------------------------------------
        # Exponential chirp and frequency-dependent amplitudes
        # ------------------------------------------------------------------
        sample_rate = 5000.0
        time = np.arange(0, CHIRP_DURATION + 1 / sample_rate, 1 / sample_rate)
        ratio = END_FREQUENCY / START_FREQUENCY
        frequency = START_FREQUENCY * ratio ** (time / CHIRP_DURATION)
        phase = (
            2 * np.pi * START_FREQUENCY * CHIRP_DURATION
            / np.log(ratio)
            * (ratio ** (time / CHIRP_DURATION) - 1)
        )

        # First scale down the very low frequencies. The scaling rises smoothly
        # from LOW_FREQUENCY_START_SCALE at 1 Hz to one at 3 Hz.
        low_frequency_progress = np.clip(
            np.log(frequency / START_FREQUENCY)
            / np.log(LOW_FREQUENCY_FULL_SCALE / START_FREQUENCY),
            0,
            1,
        )
        low_frequency_scaling = (
            LOW_FREQUENCY_START_SCALE
            + (1 - LOW_FREQUENCY_START_SCALE) * low_frequency_progress
        )

        # Lag filter: pole at 3 Hz and zero at 30 Hz.
        # H(s) = (1 + s/wz) / (1 + s/wp)
        lag_magnitude = np.sqrt(
            (1 + (frequency / LAG_ZERO_FREQUENCY) ** 2)
            / (1 + (frequency / LAG_POLE_FREQUENCY) ** 2)
        )
        lag_phase = (
            np.arctan(frequency / LAG_ZERO_FREQUENCY)
            - np.arctan(frequency / LAG_POLE_FREQUENCY)
        )
        shaped_magnitude = CHIRP_AMPLITUDE * low_frequency_scaling * lag_magnitude

        # First-order approximation of the closed gyro/rate loop.
        loop_magnitude = 1 / np.sqrt(1 + (frequency / GYRO_BANDWIDTH) ** 2)
        loop_phase = -np.arctan(frequency / GYRO_BANDWIDTH)

        shaped_command = shaped_magnitude * np.sin(phase + lag_phase)
        gyro_response = (
            shaped_magnitude
            * loop_magnitude
            * np.sin(phase + lag_phase + loop_phase)
        )

        # The drone picture represents attitude, not angular rate. Integration
        # introduces an additional 1/f factor, so very fast motion becomes small.
        attitude_envelope = shaped_magnitude * loop_magnitude / frequency
        attitude_envelope /= max(np.max(attitude_envelope), 1e-12)
        attitude_phase = phase + lag_phase + loop_phase - np.pi / 2
        attitude_phase = attitude_phase - attitude_phase[0]
        visual_attitude = (
            np.deg2rad(MAX_TILT_DEGREES)
            * attitude_envelope
            * np.sin(attitude_phase)
        )

        def value_at(values, actual_time):
            return float(np.interp(actual_time, time, values))

        def frequency_at(actual_time):
            return float(START_FREQUENCY * ratio ** (actual_time / CHIRP_DURATION))

        def shaping_at(current_frequency):
            progress = np.clip(
                np.log(current_frequency / START_FREQUENCY)
                / np.log(LOW_FREQUENCY_FULL_SCALE / START_FREQUENCY),
                0,
                1,
            )
            low_scale = (
                LOW_FREQUENCY_START_SCALE
                + (1 - LOW_FREQUENCY_START_SCALE) * progress
            )
            lag_gain = np.sqrt(
                (1 + (current_frequency / LAG_ZERO_FREQUENCY) ** 2)
                / (1 + (current_frequency / LAG_POLE_FREQUENCY) ** 2)
            )
            return float(CHIRP_AMPLITUDE * low_scale * lag_gain)

        def loop_at(current_frequency):
            return float(1 / np.sqrt(1 + (current_frequency / GYRO_BANDWIDTH) ** 2))

        # ------------------------------------------------------------------
        # Static layout
        # ------------------------------------------------------------------
        title = Text(
            "Gyro-loop chirp: from 1 Hz to 600 Hz",
            font_size=34,
            color=INK,
            weight="SEMIBOLD",
        ).to_edge(UP, buff=0.25)

        parameter_text = VGroup(
            Text("Low-frequency scaling: 1–3 Hz", font_size=20, color=GREEN),
            Text("Lag filter: pole 3 Hz, zero 30 Hz", font_size=20, color=PURPLE),
            Text("Example gyro-loop bandwidth: 100 Hz", font_size=20, color=ORANGE),
            Text("Chirp duration: 20 s", font_size=20, color=INK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
        parameter_text.to_corner(UR, buff=0.55).shift(DOWN * 0.65)

        # Log-frequency plot: this stays readable across the 1...600 Hz range.
        log_frequency = np.log10(frequency)
        plot_frequency = np.geomspace(START_FREQUENCY, END_FREQUENCY, 700)
        plot_x = np.log10(plot_frequency)
        plot_progress = np.clip(
            np.log(plot_frequency / START_FREQUENCY)
            / np.log(LOW_FREQUENCY_FULL_SCALE / START_FREQUENCY),
            0,
            1,
        )
        plot_low_scale = (
            LOW_FREQUENCY_START_SCALE
            + (1 - LOW_FREQUENCY_START_SCALE) * plot_progress
        )
        plot_lag_gain = np.sqrt(
            (1 + (plot_frequency / LAG_ZERO_FREQUENCY) ** 2)
            / (1 + (plot_frequency / LAG_POLE_FREQUENCY) ** 2)
        )
        shaping_curve = CHIRP_AMPLITUDE * plot_low_scale * plot_lag_gain
        response_curve = shaping_curve / np.sqrt(
            1 + (plot_frequency / GYRO_BANDWIDTH) ** 2
        )

        plot_y_max = 1.12 * max(1.0, CHIRP_AMPLITUDE)

        axes = Axes(
            x_range=[0, np.log10(END_FREQUENCY), 0.5],
            y_range=[0, plot_y_max, plot_y_max / 4],
            x_length=12.2,
            y_length=2.15,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 1.7},
        ).to_edge(DOWN, buff=0.52)

        shaping_graph = self.graph(axes, plot_x, shaping_curve, BLUE, 3.0)
        response_graph = self.graph(axes, plot_x, response_curve, ORANGE, 3.2)

        frequency_ticks = VGroup()
        for tick in [1, 3, 10, 30, 100, 300, 600]:
            mark = Line(
                axes.c2p(np.log10(tick), 0) + DOWN * 0.06,
                axes.c2p(np.log10(tick), 0) + UP * 0.06,
                color=MUTED,
                stroke_width=1.5,
            )
            label = Text(str(tick), font_size=15, color=MUTED).next_to(mark, DOWN, buff=0.08)
            frequency_ticks.add(mark, label)
        frequency_label = MathTex(r"f\,[\mathrm{Hz}]", font_size=25, color=INK).next_to(axes, DOWN, buff=0.25)

        legend = VGroup(
            VGroup(Line(ORIGIN, RIGHT * 0.45, color=BLUE, stroke_width=4), Text("Shaped chirp amplitude", font_size=18, color=BLUE)).arrange(RIGHT, buff=0.12),
            VGroup(Line(ORIGIN, RIGHT * 0.45, color=ORANGE, stroke_width=4), Text("Gyro response amplitude", font_size=18, color=ORANGE)).arrange(RIGHT, buff=0.12),
        ).arrange(RIGHT, buff=0.65).next_to(axes, UP, buff=0.10)

        # Corner-frequency markers.
        pole_line = DashedLine(
            axes.c2p(np.log10(LAG_POLE_FREQUENCY), 0),
            axes.c2p(np.log10(LAG_POLE_FREQUENCY), 0.94 * plot_y_max),
            color=GREEN,
            stroke_width=2,
            dash_length=0.08,
        )
        zero_line = DashedLine(
            axes.c2p(np.log10(LAG_ZERO_FREQUENCY), 0),
            axes.c2p(np.log10(LAG_ZERO_FREQUENCY), 0.94 * plot_y_max),
            color=PURPLE,
            stroke_width=2,
            dash_length=0.08,
        )
        bandwidth_line = DashedLine(
            axes.c2p(np.log10(GYRO_BANDWIDTH), 0),
            axes.c2p(np.log10(GYRO_BANDWIDTH), 0.94 * plot_y_max),
            color=ORANGE,
            stroke_width=2,
            dash_length=0.08,
        )
        marker_labels = VGroup(
            Text("lag pole: 3 Hz", font_size=16, color=GREEN).next_to(pole_line, UP, buff=0.05),
            Text("lag zero: 30 Hz", font_size=16, color=PURPLE).next_to(zero_line, UP, buff=0.05),
            Text("bandwidth", font_size=16, color=ORANGE).next_to(bandwidth_line, UP, buff=0.05),
        )

        # Drone rotates around its centre according to the integrated rate.
        drone = ImageMobject(str(Path(__file__).with_name("drone_clean.png")))
        drone.set_width(5.0)
        drone.move_to(UP * 0.65 + LEFT * 0.55)
        drone.current_visual_angle = 0.0

        tracker = ValueTracker(0.0)

        def update_drone(mob):
            target_angle = value_at(visual_attitude, tracker.get_value())
            mob.rotate(target_angle - mob.current_visual_angle)
            mob.current_visual_angle = target_angle

        drone.add_updater(update_drone)

        dynamic_readout = always_redraw(
            lambda: VGroup(
                Text(f"Time: {tracker.get_value():4.1f} s", font_size=21, color=INK),
                Text(
                    f"Current frequency: {frequency_at(tracker.get_value()):6.1f} Hz",
                    font_size=21,
                    color=self.frequency_color(frequency_at(tracker.get_value())),
                ),
                Text(
                    f"Current chirp amplitude: {shaping_at(frequency_at(tracker.get_value())):.2f}",
                    font_size=21,
                    color=BLUE,
                ),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).to_corner(UL, buff=0.55).shift(DOWN * 0.70)
        )

        status = always_redraw(
            lambda: self.make_status(frequency_at(tracker.get_value()))
        )

        frequency_marker = always_redraw(
            lambda: DashedLine(
                axes.c2p(np.log10(frequency_at(tracker.get_value())), 0),
                axes.c2p(np.log10(frequency_at(tracker.get_value())), 0.97 * plot_y_max),
                color=INK,
                stroke_width=1.6,
                dash_length=0.07,
            )
        )
        shaping_dot = always_redraw(
            lambda: Dot(
                axes.c2p(
                    np.log10(frequency_at(tracker.get_value())),
                    shaping_at(frequency_at(tracker.get_value())),
                ),
                radius=0.06,
                color=BLUE,
            )
        )
        response_dot = always_redraw(
            lambda: Dot(
                axes.c2p(
                    np.log10(frequency_at(tracker.get_value())),
                    shaping_at(frequency_at(tracker.get_value()))
                    * loop_at(frequency_at(tracker.get_value())),
                ),
                radius=0.06,
                color=ORANGE,
            )
        )

        # Scaling and lag-filter explanation without relying on a formula.
        shaping_explanation = VGroup(
            Text("Below 3 Hz", font_size=19, color=GREEN, weight="SEMIBOLD"),
            Text("Reduced amplitude rises towards full scale", font_size=18, color=INK),
            Text("Between 3 Hz and 30 Hz", font_size=19, color=PURPLE, weight="SEMIBOLD"),
            Text("The lag filter increasingly attenuates the chirp", font_size=18, color=INK),
            Text("Above 30 Hz", font_size=19, color=BLUE, weight="SEMIBOLD"),
            Text("The lag-filter gain approaches one tenth", font_size=18, color=INK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.07)
        shaping_explanation.to_corner(UR, buff=0.55).shift(DOWN * 2.15)
        explanation_box = RoundedRectangle(
            width=4.55,
            height=2.15,
            corner_radius=0.16,
            stroke_color=GRID,
            stroke_width=1.5,
            fill_color=WHITE,
            fill_opacity=0.94,
        ).move_to(shaping_explanation)

        # ------------------------------------------------------------------
        # Animation
        # ------------------------------------------------------------------
        self.play(FadeIn(title), FadeIn(parameter_text), run_time=1.2)
        self.play(
            FadeIn(drone), FadeIn(dynamic_readout), FadeIn(status),
            FadeIn(axes), FadeIn(frequency_ticks), FadeIn(frequency_label), FadeIn(legend),
            run_time=1.5,
        )
        self.play(
            Create(shaping_graph), Create(response_graph),
            Create(pole_line), Create(zero_line), Create(bandwidth_line),
            FadeIn(marker_labels),
            run_time=2.0,
        )
        self.play(FadeIn(explanation_box), FadeIn(shaping_explanation), run_time=1.2)
        self.wait(INTRO_WAIT)

        self.add(frequency_marker, shaping_dot, response_dot)
        self.play(
            tracker.animate.set_value(CHIRP_DURATION),
            run_time=CHIRP_RUN_TIME,
            rate_func=linear,
        )

        drone.clear_updaters()
        self.play(
            Rotate(drone, angle=-drone.current_visual_angle, about_point=drone.get_center()),
            run_time=0.6,
        )
        drone.current_visual_angle = 0.0
        self.wait(FINAL_WAIT)

    def graph(self, axes, x, y, color, width):
        points = [axes.c2p(float(xi), float(yi)) for xi, yi in zip(x, y)]
        return VMobject(color=color, stroke_width=width).set_points_as_corners(points)

    def frequency_color(self, current_frequency):
        if current_frequency < LAG_POLE_FREQUENCY:
            return GREEN
        if current_frequency < LAG_ZERO_FREQUENCY:
            return PURPLE
        if current_frequency < GYRO_BANDWIDTH:
            return BLUE
        return RED

    def make_status(self, current_frequency):
        if current_frequency < LAG_POLE_FREQUENCY:
            text = "Low-frequency chirp: amplitude scaling"
            color = GREEN
        elif current_frequency < LAG_ZERO_FREQUENCY:
            text = "Lag-filter transition: amplitude decreases"
            color = PURPLE
        elif current_frequency < GYRO_BANDWIDTH:
            text = "Lag-filtered excitation within the gyro bandwidth"
            color = BLUE
        else:
            text = "Above the bandwidth: gyro response is attenuated"
            color = RED

        box = RoundedRectangle(
            width=5.55,
            height=0.58,
            corner_radius=0.14,
            stroke_color=color,
            stroke_width=1.8,
            fill_color=WHITE,
            fill_opacity=0.92,
        )
        label = Text(text, font_size=18, color=color).move_to(box)
        return VGroup(box, label).move_to(UP * 2.65 + LEFT * 0.35)
