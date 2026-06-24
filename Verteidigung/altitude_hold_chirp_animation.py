from pathlib import Path

from manim import *
import numpy as np


# ---------------------------------------------------------------------------
# Render settings
# ---------------------------------------------------------------------------
config.background_color = "#F6EEE1"
config.frame_width = 16
config.frame_height = 9
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_rate = 30

# Chirp parameters: change these values to adapt the experiment.
START_FREQUENCY = 0.05       # Hz
END_FREQUENCY = 3.0         # Hz
CHIRP_DURATION = 75.0       # s
DRONE_BANDWIDTH = 1.0       # Hz (-3 dB bandwidth of the example model)
CHIRP_AMPLITUDE = 1.0

# Animation timing. Keeping this equal to CHIRP_DURATION shows the chirp in
# real time. A smaller value speeds up the video without changing the data.
CHIRP_RUN_TIME = 37.5
INTRO_WAIT = 2.0
FINAL_WAIT = 3.0

# Visual style
INK = "#111827"
MUTED = "#6B7280"
GRID = "#D1D5DB"
BLUE = "#2563EB"
ORANGE = "#F97316"
GREEN = "#16A34A"
RED = "#DC2626"


class AltitudeHoldChirp(Scene):
    """Visualise an altitude-hold chirp and the bandwidth-limited response."""

    def construct(self):
        # ------------------------------------------------------------------
        # Generate an exponential chirp from 0.1 Hz to 3 Hz.
        # ------------------------------------------------------------------
        sample_rate = 200.0
        time = np.arange(0, CHIRP_DURATION + 1 / sample_rate, 1 / sample_rate)
        frequency_ratio = END_FREQUENCY / START_FREQUENCY

        instantaneous_frequency = START_FREQUENCY * frequency_ratio ** (time / CHIRP_DURATION)
        phase = (
            2 * np.pi * START_FREQUENCY * CHIRP_DURATION
            / np.log(frequency_ratio)
            * (frequency_ratio ** (time / CHIRP_DURATION) - 1)
        )
        altitude_command = CHIRP_AMPLITUDE * np.sin(phase)

        # First-order closed-loop model with approximately 1 Hz bandwidth.
        # dy/dt = 2*pi*bandwidth*(command - y)
        response = np.zeros_like(altitude_command)
        dt = 1 / sample_rate
        pole = 2 * np.pi * DRONE_BANDWIDTH
        alpha = 1 - np.exp(-pole * dt)
        for k in range(1, len(response)):
            response[k] = response[k - 1] + alpha * (altitude_command[k] - response[k - 1])

        def value_at(values, actual_time):
            return float(np.interp(actual_time, time, values))

        def frequency_at(actual_time):
            return float(
                START_FREQUENCY
                * frequency_ratio ** (actual_time / CHIRP_DURATION)
            )

        # ------------------------------------------------------------------
        # Static layout
        # ------------------------------------------------------------------
        title = Text(
            "Altitude-hold chirp: effect of increasing frequency",
            font_size=34,
            color=INK,
            weight="SEMIBOLD",
        ).to_edge(UP, buff=0.25)

        parameter_text = VGroup(
            Text("Start frequency: 0.05 Hz", font_size=20, color=BLUE),
            Text("Drone bandwidth: approximately 1 Hz", font_size=20, color=ORANGE),
            Text("Final frequency: 3 Hz", font_size=20, color=RED),
            Text("Chirp duration: 75 s", font_size=20, color=INK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
        parameter_text.to_corner(UR, buff=0.55).shift(DOWN * 0.65)

        # The lower plot displays the complete command and drone response.
        axes = Axes(
            x_range=[0, CHIRP_DURATION, 5],
            y_range=[-1.2, 1.2, 0.5],
            x_length=12.2,
            y_length=2.05,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 1.7},
        ).to_edge(DOWN, buff=0.45)
        #axes.add_coordinates(font_size=15, color=MUTED)
        time_label = MathTex(r"t\,[\mathrm{s}]", font_size=25, color=INK).next_to(axes, DOWN, buff=0.12)

        command_label = VGroup(
            Line(ORIGIN, RIGHT * 0.45, color=BLUE, stroke_width=4),
            Text("Altitude command", font_size=18, color=BLUE),
        ).arrange(RIGHT, buff=0.12)
        response_label = VGroup(
            Line(ORIGIN, RIGHT * 0.45, color=ORANGE, stroke_width=4),
            Text("Drone altitude", font_size=18, color=ORANGE),
        ).arrange(RIGHT, buff=0.12)
        plot_legend = VGroup(command_label, response_label).arrange(RIGHT, buff=0.65)
        plot_legend.next_to(axes, UP, buff=0.10)

        command_graph = axes.plot_line_graph(
            x_values=time,
            y_values=altitude_command,
            add_vertex_dots=False,
            line_color=BLUE,
            stroke_width=2.6,
        )
        response_graph = axes.plot_line_graph(
            x_values=time,
            y_values=response,
            add_vertex_dots=False,
            line_color=ORANGE,
            stroke_width=3.2,
        )

        # Drone and moving commanded-altitude reference.
        asset_path = Path(__file__).with_name("drone_clean.png")
        drone = ImageMobject(str(asset_path))
        drone.set_width(5.0)
        drone_base = UP * 0.65 + LEFT * 0.8
        drone.move_to(drone_base)

        altitude_scale = 1.05
        tracker = ValueTracker(0.0)

        reference_line = always_redraw(
            lambda: DashedLine(
                LEFT * 3.85 + UP * (0.65 + altitude_scale * value_at(altitude_command, tracker.get_value())),
                RIGHT * 2.25 + UP * (0.65 + altitude_scale * value_at(altitude_command, tracker.get_value())),
                color=BLUE,
                stroke_width=2.2,
                dash_length=0.12,
            )
        )
        reference_label = always_redraw(
            lambda: Text("commanded altitude", font_size=17, color=BLUE).next_to(
                reference_line, LEFT, buff=0.12
            )
        )

        drone.add_updater(
            lambda mob: mob.move_to(
                drone_base
                + UP * altitude_scale * value_at(response, tracker.get_value())
            )
        )

        # Dynamic time/frequency display.
        dynamic_readout = always_redraw(
            lambda: VGroup(
                Text(
                    f"Time: {2*tracker.get_value():4.1f} s",
                    font_size=18,
                    color=INK,
                ),
                Text(
                    f"Current chirp frequency: {frequency_at(tracker.get_value()):.2f} Hz",
                    font_size=18,
                    color=(
                        GREEN
                        if frequency_at(tracker.get_value()) < 0.7 * DRONE_BANDWIDTH
                        else ORANGE
                        if frequency_at(tracker.get_value()) <= 1.3 * DRONE_BANDWIDTH
                        else RED
                    ),
                ),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.10).to_corner(UL, buff=0.55).shift(DOWN * 0.70)
        )

        status = always_redraw(lambda: self.make_status(frequency_at(tracker.get_value())))

        # A moving marker connects the live animation to the lower plot.
        time_marker = always_redraw(
            lambda: DashedLine(
                axes.c2p(tracker.get_value(), -1.15),
                axes.c2p(tracker.get_value(), 1.15),
                color=INK,
                stroke_width=1.6,
                dash_length=0.08,
            )
        )
        command_dot = always_redraw(
            lambda: Dot(
                axes.c2p(
                    tracker.get_value(),
                    value_at(altitude_command, tracker.get_value()),
                ),
                radius=0.055,
                color=BLUE,
            )
        )
        response_dot = always_redraw(
            lambda: Dot(
                axes.c2p(
                    tracker.get_value(),
                    value_at(response, tracker.get_value()),
                ),
                radius=0.060,
                color=ORANGE,
            )
        )

        # ------------------------------------------------------------------
        # Animation
        # ------------------------------------------------------------------
        self.play(FadeIn(title), FadeIn(parameter_text), run_time=1.2)
        self.play(
            FadeIn(axes), FadeIn(time_label), FadeIn(plot_legend),
            FadeIn(reference_line), FadeIn(reference_label), FadeIn(drone),
            FadeIn(dynamic_readout), FadeIn(status),
            run_time=1.6,
        )
        self.wait(INTRO_WAIT)

        self.add(time_marker, command_dot, response_dot)
        self.play(
            Create(command_graph),
            Create(response_graph),
            tracker.animate.set_value(CHIRP_DURATION),
            run_time=CHIRP_RUN_TIME,
            rate_func=linear,
        )

        drone.clear_updaters()
        self.wait(0.8)

        conclusion = VGroup(
            Text("Below the bandwidth", font_size=16, color=GREEN, weight="SEMIBOLD"),
            Text("The drone follows the altitude command.", font_size=16, color=INK),
            Text("Above the bandwidth", font_size=14, color=RED, weight="SEMIBOLD"),
            Text("The motion is attenuated and delayed.", font_size=16, color=INK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
        conclusion.to_corner(UR, buff=0.55).shift(DOWN * 2.65)
        background = RoundedRectangle(
            width=4.4,
            height=1.75,
            corner_radius=0.16,
            stroke_color=GRID,
            stroke_width=1.5,
            fill_color=WHITE,
            fill_opacity=0.94,
        ).move_to(conclusion)
        self.play(FadeIn(background), FadeIn(conclusion, shift=LEFT * 0.15), run_time=1.3)
        self.wait(FINAL_WAIT)

    def make_status(self, current_frequency):
        if current_frequency < 0.7 * DRONE_BANDWIDTH:
            text = "The drone closely follows the command"
            color = GREEN
        elif current_frequency <= 1.3 * DRONE_BANDWIDTH:
            text = "Near the bandwidth: attenuation and phase lag"
            color = ORANGE
        else:
            text = "Above the bandwidth: motion is strongly attenuated"
            color = RED

        box = RoundedRectangle(
            width=5.3,
            height=0.58,
            corner_radius=0.14,
            stroke_color=color,
            stroke_width=1.8,
            fill_color=WHITE,
            fill_opacity=0.92,
        )
        label = Text(text, font_size=14, color=color).move_to(box)
        return VGroup(box, label).move_to(UP * 2.65 + LEFT * 0.4)

