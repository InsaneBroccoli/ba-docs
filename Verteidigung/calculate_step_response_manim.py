from manim import *
import numpy as np


config.background_color = "#F6EEE1"
config.frame_width = 16
config.frame_height = 9


INK = "#111827"
MUTED = "#6B7280"
BLUE = "#2563EB"
ORANGE = "#F97316"
GREEN = "#16A34A"
PURPLE = "#7C3AED"
RED = "#DC2626"


class StepResponseFromFRDBase:
    def make_step_title(self, text, color=INK):
        return Text(text, font_size=34, color=color).to_edge(UP, buff=0.35)

    def graph_from_data(self, axes, x, y, color=BLUE, stroke_width=3):
        graph = VMobject(color=color, stroke_width=stroke_width)
        points = [axes.c2p(float(xi), float(yi)) for xi, yi in zip(x, y)]
        graph.set_points_as_corners(points)
        return graph

    def stem_plot(self, axes, x, y, color=PURPLE, max_stems=80):
        stems = VGroup()

        if len(x) > max_stems:
            sample = np.linspace(0, len(x) - 1, max_stems).astype(int)
            x = x[sample]
            y = y[sample]

        max_y = max(float(np.max(np.abs(y))), 1e-9)

        for xi, yi in zip(x, y):
            ratio = min(abs(float(yi)) / max_y, 1.0)
            opacity = 0.18 + 0.75 * ratio
            width = 1.0 + 2.8 * ratio

            stem = Line(
                axes.c2p(float(xi), 0),
                axes.c2p(float(xi), float(yi)),
                color=color,
                stroke_width=width,
            )
            stem.set_opacity(opacity)

            dot = Dot(
                axes.c2p(float(xi), float(yi)),
                color=color,
                radius=0.018 + 0.025 * ratio,
                fill_opacity=opacity,
                stroke_width=0,
            )
            stems.add(stem, dot)

        return stems

    def example_frequency_response(self):
        freq = np.linspace(0, 40, 129)
        omega = 2 * np.pi * freq

        natural_frequency = 2 * np.pi * 7.0
        damping = 0.32
        delay = 0.012

        s = 1j * omega
        response = natural_frequency**2 / (s**2 + 2 * damping * natural_frequency * s + natural_frequency**2)
        response *= np.exp(-s * delay)

        response_with_missing_dc = response.copy()
        response_with_missing_dc[0] = np.nan + 1j * np.nan

        return freq, response, response_with_missing_dc

    def calculate_step_response(self, freq, response, cutoff_frequency):
        processed_response = response.copy()

        if np.isnan(abs(processed_response[0])):
            processed_response[0] = processed_response[1]

        truncated_response = processed_response.copy()
        truncated_response[freq > cutoff_frequency] = 0

        full_spectrum = np.concatenate(
            [truncated_response, np.conj(truncated_response[-2:0:-1])]
        )
        impulse_response = np.real(np.fft.ifft(full_spectrum))
        step_response = np.cumsum(impulse_response)

        if abs(step_response[-1]) > 1e-9:
            impulse_response = impulse_response / step_response[-1]
            step_response = step_response / step_response[-1]

        return processed_response, truncated_response, full_spectrum, impulse_response, step_response

    def get_data(self):
        freq, true_response, response_with_missing_dc = self.example_frequency_response()
        cutoff_frequency = 18.0
        processed_response, truncated_response, full_spectrum, impulse_response, step_response = (
            self.calculate_step_response(freq, response_with_missing_dc, cutoff_frequency)
        )

        return {
            "freq": freq,
            "true_response": true_response,
            "response_with_missing_dc": response_with_missing_dc,
            "cutoff_frequency": cutoff_frequency,
            "processed_response": processed_response,
            "truncated_response": truncated_response,
            "full_spectrum": full_spectrum,
            "impulse_response": impulse_response,
            "step_response": step_response,
        }


class StepResponseFromFRDPart1(Scene, StepResponseFromFRDBase):
    def construct(self):
        data = self.get_data()

        freq = data["freq"]
        true_response = data["true_response"]
        processed_response = data["processed_response"]
        truncated_response = data["truncated_response"]
        cutoff_frequency = data["cutoff_frequency"]

        FAST_TIME = 1.2
        TRANSITION_TIME = 2.3
        DRAW_TIME = 3.2
        WAIT_TIME = 1.8
        LONG_WAIT = 4.5

        magnitude = np.abs(true_response)
        processed_magnitude = np.abs(processed_response)
        truncated_magnitude = np.abs(truncated_response)

        step_title = self.make_step_title("Step 1: Extract frequency response data", BLUE)

        freq_axes = Axes(
            x_range=[0, 40, 10],
            y_range=[0, 1.7, 0.5],
            x_length=9.2,
            y_length=3.0,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).move_to(ORIGIN).shift(UP * 0.35)
        freq_axes.add_coordinates(font_size=16, num_decimal_places=0)

        freq_label = Text("Frequency response magnitude", font_size=24, color=INK)
        freq_label.next_to(freq_axes, UP, buff=0.18)
        x_freq_label = Text("frequency [Hz]", font_size=19, color=INK).next_to(freq_axes, DOWN, buff=0.18)

        magnitude_graph = self.graph_from_data(freq_axes, freq, magnitude, BLUE, 3)
        missing_dc_dot = Dot(freq_axes.c2p(0, 0.0), color=RED, radius=0.08)
        missing_dc_text = Text("missing direct-current\nsample", font_size=19, color=RED)
        missing_dc_text.next_to(missing_dc_dot, UP + LEFT, buff=0.18)

        bottom_text = Text("The complex frequency response is sampled on an equally spaced grid", font_size=22, color=INK)
        bottom_text.to_edge(DOWN, buff=0.65)

        self.play(
            FadeIn(step_title, shift=DOWN * 0.15),
            FadeIn(freq_axes),
            FadeIn(freq_label),
            FadeIn(x_freq_label),
            run_time=FAST_TIME,
        )
        self.play(Create(magnitude_graph), FadeIn(bottom_text), run_time=DRAW_TIME)
        self.wait(WAIT_TIME)
        self.play(FadeIn(missing_dc_dot), FadeIn(missing_dc_text), run_time=TRANSITION_TIME)

        fixed_dc_dot = Dot(freq_axes.c2p(0, processed_magnitude[0]), color=GREEN, radius=0.08)
        fixed_dc_text = Text("replace with next\nfrequency point", font_size=19, color=GREEN)
        fixed_dc_text.next_to(fixed_dc_dot, UP + LEFT, buff=0.18)
        processed_graph = self.graph_from_data(freq_axes, freq, processed_magnitude, BLUE, 3)

        self.play(
            Transform(step_title, self.make_step_title("Step 2: Replace missing direct-current value", ORANGE)),
            ReplacementTransform(missing_dc_dot, fixed_dc_dot),
            ReplacementTransform(missing_dc_text, fixed_dc_text),
            Transform(magnitude_graph, processed_graph),
            Transform(
                bottom_text,
                Text("If the direct-current value is missing, the next point is used", font_size=22, color=ORANGE).to_edge(DOWN, buff=0.65),
            ),
            run_time=TRANSITION_TIME,
        )
        self.wait(WAIT_TIME)

        cutoff_line = DashedLine(
            freq_axes.c2p(cutoff_frequency, 0),
            freq_axes.c2p(cutoff_frequency, 1.55),
            color=RED,
            stroke_width=3,
            dash_length=0.12,
        )
        cutoff_label = Text("cutoff frequency", font_size=21, color=RED)
        cutoff_label.next_to(cutoff_line, UP, buff=0.12)
        truncated_graph = self.graph_from_data(freq_axes, freq, truncated_magnitude, GREEN, 3)

        self.play(
            Transform(step_title, self.make_step_title("Step 3: Remove high-frequency content", GREEN)),
            FadeIn(cutoff_line),
            FadeIn(cutoff_label),
            Transform(magnitude_graph, truncated_graph),
            FadeOut(fixed_dc_text),
            FadeOut(fixed_dc_dot),
            Transform(
                bottom_text,
                Text("Frequencies above the cutoff are set to zero", font_size=22, color=GREEN).to_edge(DOWN, buff=0.65),
            ),
            run_time=TRANSITION_TIME,
        )
        self.wait(LONG_WAIT)


class StepResponseFromFRDPart2(Scene, StepResponseFromFRDBase):
    def construct(self):
        data = self.get_data()

        freq = data["freq"]
        full_spectrum = data["full_spectrum"]
        impulse_response = data["impulse_response"]
        step_response = data["step_response"]

        FAST_TIME = 1.2
        TRANSITION_TIME = 2.3
        DRAW_TIME = 3.2
        SLOW_DRAW_TIME = 4.8
        WAIT_TIME = 1.8
        LONG_WAIT = 4.5

        full_freq = np.fft.fftfreq(len(full_spectrum), d=1 / (2 * freq[-1]))
        full_freq = np.fft.fftshift(full_freq)
        full_mag = np.fft.fftshift(np.abs(full_spectrum))

        step_title = self.make_step_title("Step 4: Build a symmetric spectrum", PURPLE)

        sym_axes = Axes(
            x_range=[-40, 40, 20],
            y_range=[0, 1.7, 0.5],
            x_length=9.2,
            y_length=3.0,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).move_to(ORIGIN).shift(UP * 0.35)
        sym_axes.add_coordinates(font_size=16, num_decimal_places=0)

        sym_label = Text("Symmetric spectrum for a real time signal", font_size=24, color=INK)
        sym_label.next_to(sym_axes, UP, buff=0.18)
        x_sym_label = Text("frequency [Hz]", font_size=19, color=INK).next_to(sym_axes, DOWN, buff=0.18)
        sym_graph = self.stem_plot(sym_axes, full_freq, full_mag, PURPLE, max_stems=90)

        bottom_text = Text("Positive frequencies are mirrored with complex conjugates", font_size=22, color=PURPLE)
        bottom_text.to_edge(DOWN, buff=0.65)

        self.play(
            FadeIn(step_title, shift=DOWN * 0.15),
            FadeIn(sym_axes),
            FadeIn(sym_label),
            FadeIn(x_sym_label),
            run_time=FAST_TIME,
        )
        self.play(FadeIn(sym_graph), FadeIn(bottom_text), run_time=DRAW_TIME)
        self.wait(LONG_WAIT)

        time = np.arange(len(impulse_response))
        show_n = 120
        time = time[:show_n]
        impulse_show = impulse_response[:show_n]
        step_show = step_response[:show_n]

        impulse_axes = Axes(
            x_range=[0, show_n, 30],
            y_range=[-0.08, 0.18, 0.08],
            x_length=4.9,
            y_length=2.0,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).to_edge(LEFT, buff=0.9).shift(UP * 0.45)
        step_axes = Axes(
            x_range=[0, show_n, 30],
            y_range=[-0.15, 1.15, 0.5],
            x_length=6.9,
            y_length=2.85,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).to_edge(RIGHT, buff=0.75).shift(UP * 0.45)
        plot_group = VGroup(impulse_axes, step_axes)

        impulse_label = Text("Impulse response", font_size=21, color=INK)
        impulse_label.next_to(impulse_axes, UP, buff=0.12)
        step_label = Text("Step response", font_size=23, color=INK)
        step_label.next_to(step_axes, UP, buff=0.12)

        formula = Text(
            "step response[k] = Σ impulse response[i],  i = 0 ... k",
            font_size=24,
            color=INK,
        ).to_edge(DOWN, buff=1.35)

        initial_n = 6
        impulse_graph = self.graph_from_data(impulse_axes, time[:initial_n], impulse_show[:initial_n], ORANGE, 3)
        step_graph = self.graph_from_data(step_axes, time[:initial_n], step_show[:initial_n], BLUE, 3)

        impulse_marker = Dot(
            impulse_axes.c2p(time[initial_n - 1], impulse_show[initial_n - 1]),
            color=ORANGE,
            radius=0.055,
        )
        step_marker = Dot(
            step_axes.c2p(time[initial_n - 1], step_show[initial_n - 1]),
            color=BLUE,
            radius=0.055,
        )

        sample_counter = Text(f"k = {initial_n - 1}", font_size=20, color=MUTED)
        sample_counter.next_to(plot_group, DOWN, buff=0.22)

        self.play(
            Transform(step_title, self.make_step_title("Step 5: Transform back to time domain", RED)),
            FadeOut(sym_axes),
            FadeOut(sym_label),
            FadeOut(x_sym_label),
            FadeOut(sym_graph),
            FadeIn(impulse_axes),
            FadeIn(impulse_label),
            FadeIn(step_axes),
            FadeIn(step_label),
            FadeIn(formula),
            Transform(
                bottom_text,
                Text("Inverse Fourier transform gives the impulse response", font_size=22, color=ORANGE).to_edge(DOWN, buff=0.65),
            ),
            run_time=TRANSITION_TIME,
        )
        self.wait(WAIT_TIME)
        self.play(Create(impulse_graph), FadeIn(impulse_marker), run_time=DRAW_TIME)
        self.wait(WAIT_TIME)
        self.play(
            Create(step_graph),
            FadeIn(step_marker),
            FadeIn(sample_counter),
            Transform(
                bottom_text,
                Text("The step response is built as a running cumulative sum", font_size=22, color=BLUE).to_edge(DOWN, buff=0.65),
            ),
            run_time=SLOW_DRAW_TIME,
        )
        self.wait(WAIT_TIME)

        for n in [14, 24, 38, 58, 82, 120]:
            new_impulse = self.graph_from_data(impulse_axes, time[:n], impulse_show[:n], ORANGE, 3)
            new_step = self.graph_from_data(step_axes, time[:n], step_show[:n], BLUE, 3)
            new_counter = Text(f"k = {n - 1}", font_size=20, color=MUTED)
            new_counter.next_to(plot_group, DOWN, buff=0.22)

            self.play(
                Transform(impulse_graph, new_impulse),
                Transform(step_graph, new_step),
                impulse_marker.animate.move_to(impulse_axes.c2p(time[n - 1], impulse_show[n - 1])),
                step_marker.animate.move_to(step_axes.c2p(time[n - 1], step_show[n - 1])),
                Transform(sample_counter, new_counter),
                Transform(
                    bottom_text,
                    Text("Each new impulse sample is added to the running step response", font_size=22, color=BLUE).to_edge(DOWN, buff=0.65),
                ),
                run_time=1.15,
            )

        self.wait(LONG_WAIT)

        final = VGroup(
            Text("Algorithm overview", font_size=30, color=INK),
            Text("1. Read complex frequency response samples", font_size=23, color=INK),
            Text("2. Replace a missing direct-current value", font_size=23, color=INK),
            Text("3. Set frequencies above the cutoff to zero", font_size=23, color=INK),
            Text("4. Mirror the spectrum with complex conjugates", font_size=23, color=INK),
            Text("5. Inverse Fourier transform → impulse response", font_size=23, color=INK),
            Text("6. Cumulative sum → step response", font_size=24, color=BLUE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        final.move_to(ORIGIN).shift(DOWN * 0.1)

        self.play(
            Transform(step_title, self.make_step_title("Overview: Step response from frequency response", INK)),
            FadeOut(impulse_axes),
            FadeOut(impulse_label),
            FadeOut(impulse_graph),
            FadeOut(step_axes),
            FadeOut(step_label),
            FadeOut(step_graph),
            FadeOut(impulse_marker),
            FadeOut(step_marker),
            FadeOut(sample_counter),
            FadeOut(formula),
            FadeOut(bottom_text),
            FadeIn(final, shift=RIGHT * 0.2),
            run_time=TRANSITION_TIME,
        )
        self.wait(LONG_WAIT)


class StepResponseFromFRD(StepResponseFromFRDPart1):
    pass
