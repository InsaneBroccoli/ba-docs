from manim import *
import theme  # sets URW Gothic as the default Text font
import numpy as np


config.background_color = "#F6EEE1"
config.frame_width = 16
config.frame_height = 9


INK = "#111827"
MUTED = "#6B7280"
GRID = "#D1D5DB"
BLUE = "#2563EB"
ORANGE = "#F97316"
GREEN = "#16A34A"
PURPLE = "#7C3AED"
RED = "#DC2626"

# Chirp and noise settings.
RANDOM_SEED = 8
SAMPLE_RATE_HZ = 80.0
CHIRP_DURATION_S = 12.0
CHIRP_START_HZ = 0.50
CHIRP_END_HZ = 3.00
CHIRP_BASE_AMPLITUDE = 0.72
CHIRP_AMPLITUDE_VARIATION = 0.16
AMPLITUDE_VARIATION_HZ = 0.075
NOISE_STANDARD_DEVIATION = 0.20
SIGNAL_OFFSET = 0.10

# Rotation-domain low-pass settings.
FILTER_CUTOFF_HZ = 0.15
FILTER_ORDER = 2


class RotFiltFiltBase(Scene):
    FAST_TIME = 1.2
    TRANSITION_TIME = 2.2
    DRAW_TIME = 3.5
    SLOW_DRAW_TIME = 5.0
    WAIT_TIME = 2.0
    LONG_WAIT = 4.0

    def make_step_title(self, text, color=INK):
        return Text(text, font_size=34, color=color).to_edge(UP, buff=0.35)

    def graph_from_data(self, axes, x, y, color=BLUE, stroke_width=3):
        graph = VMobject(color=color, stroke_width=stroke_width)
        points = [axes.c2p(float(xi), float(yi)) for xi, yi in zip(x, y)]
        graph.set_points_as_corners(points)
        return graph

    def signal_data(self):
        rng = np.random.default_rng(RANDOM_SEED)
        sample_rate = SAMPLE_RATE_HZ
        duration = CHIRP_DURATION_S
        time = np.arange(0.0, duration, 1.0 / sample_rate)

        start_frequency = CHIRP_START_HZ
        end_frequency = CHIRP_END_HZ
        if start_frequency <= 0 or end_frequency <= 0:
            raise ValueError("Exponential chirp frequencies must be positive.")
        if np.isclose(start_frequency, end_frequency):
            instantaneous_frequency = np.full_like(time, start_frequency)
            phase = 2.0 * np.pi * start_frequency * time
        else:
            growth = np.log(end_frequency / start_frequency) / duration
            instantaneous_frequency = start_frequency * np.exp(growth * time)
            phase = (
                2.0
                * np.pi
                * start_frequency
                * (np.exp(growth * time) - 1.0)
                / growth
            )

        amplitude = CHIRP_BASE_AMPLITUDE + CHIRP_AMPLITUDE_VARIATION * np.sin(
            2.0 * np.pi * AMPLITUDE_VARIATION_HZ * time + 0.4
        )
        clean_signal = amplitude * np.sin(phase)
        noise = NOISE_STANDARD_DEVIATION * rng.normal(size=time.size)
        noisy_signal = clean_signal + noise + SIGNAL_OFFSET

        return time, instantaneous_frequency, phase, clean_signal, noisy_signal

    def low_pass_zero_phase(
        self,
        values,
        sample_rate,
        cutoff_hz=FILTER_CUTOFF_HZ,
        order=FILTER_ORDER,
    ):
        frequencies = np.fft.fftfreq(values.size, d=1.0 / sample_rate)
        zero_phase_gain = 1.0 / (
            1.0 + (np.abs(frequencies) / cutoff_hz) ** (2 * order)
        )
        filtered = np.fft.ifft(np.fft.fft(values) * zero_phase_gain)
        return filtered.real if np.isrealobj(values) else filtered

    def make_signal_axes(self, center=UP * 1.25):
        time_tick = max(CHIRP_DURATION_S / 6.0, 0.1)
        amplitude_limit = (
            CHIRP_BASE_AMPLITUDE
            + abs(CHIRP_AMPLITUDE_VARIATION)
            + 3.0 * NOISE_STANDARD_DEVIATION
        )
        axes = Axes(
            x_range=[0, CHIRP_DURATION_S, time_tick],
            y_range=[-amplitude_limit, amplitude_limit, amplitude_limit / 2.0],
            x_length=12.2,
            y_length=2.55,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        )
        axes.move_to(center)
        return axes

    def make_frequency_axes(self, center=DOWN * 2.25):
        time_tick = max(CHIRP_DURATION_S / 6.0, 0.1)
        frequency_limit = 1.05 * CHIRP_END_HZ
        axes = Axes(
            x_range=[0, CHIRP_DURATION_S, time_tick],
            y_range=[0, frequency_limit, frequency_limit / 4.0],
            x_length=12.2,
            y_length=2.15,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        )
        axes.move_to(center)
        return axes


class ApplyRotFiltFiltPart1(RotFiltFiltBase):
    def construct(self):
        time, frequency, phase, clean_signal, noisy_signal = self.signal_data()

        step_title = self.make_step_title(
            "Step 1: Sensor data after chirp excitation", color=BLUE
        )
        signal_axes = self.make_signal_axes()
        frequency_axes = self.make_frequency_axes()

        signal_label = Text(
            "Amplitude-modulated exponential chirp",
            font_size=24,
            color=INK,
        ).next_to(signal_axes, UP, buff=0.12)
        frequency_label = Text(
            "Instantaneous frequency",
            font_size=23,
            color=INK,
        ).next_to(frequency_axes, UP, buff=0.10)
        time_label = Text("time [s]", font_size=19, color=INK).next_to(
            frequency_axes, DOWN, buff=0.10
        )
        frequency_axis_label = Text(
            "frequency [Hz]", font_size=19, color=INK
        ).next_to(frequency_axes, LEFT, buff=0.12).rotate(PI / 2)

        clean_graph = self.graph_from_data(
            signal_axes, time, clean_signal, BLUE, stroke_width=2.8
        )
        frequency_graph = self.graph_from_data(
            frequency_axes, time, frequency, ORANGE, stroke_width=3.2
        )

        self.play(
            FadeIn(step_title, shift=DOWN * 0.15),
            FadeIn(signal_axes),
            FadeIn(signal_label),
            run_time=self.TRANSITION_TIME,
        )
        self.play(Create(clean_graph), run_time=self.SLOW_DRAW_TIME)
        self.wait(self.WAIT_TIME)
        self.play(
            FadeIn(frequency_axes),
            FadeIn(frequency_label),
            FadeIn(time_label),
            FadeIn(frequency_axis_label),
            run_time=self.TRANSITION_TIME,
        )
        self.play(
            Create(frequency_graph),
            run_time=self.SLOW_DRAW_TIME,
        )
        self.wait(self.LONG_WAIT)

        noisy_graph = self.graph_from_data(
            signal_axes, time, noisy_signal, PURPLE, stroke_width=2.2
        )
        noisy_label = Text(
            "Chirp with additive noise",
            font_size=24,
            color=INK,
        ).move_to(signal_label)
        noise_text = Text(
            "measured signal = chirp + noise",
            font_size=23,
            color=PURPLE,
        ).next_to(frequency_axes, DOWN, buff=0.45)

        self.play(
            Transform(
                step_title,
                self.make_step_title("Step 2: Add measurement noise", PURPLE),
            ),
            Transform(signal_label, noisy_label),
            run_time=self.TRANSITION_TIME,
        )
        self.play(
            Transform(clean_graph, noisy_graph),
            FadeIn(noise_text),
            run_time=self.SLOW_DRAW_TIME,
        )
        self.wait(self.LONG_WAIT)


class ApplyRotFiltFiltPart2(RotFiltFiltBase):
    def construct(self):
        time, frequency, phase, clean_signal, noisy_signal = self.signal_data()
        centered_signal = noisy_signal - np.mean(noisy_signal)
        phasor = np.exp(1j * phase)
        rotated_positive = centered_signal * phasor
        rotated_negative = centered_signal * np.conj(phasor)
        sample_rate = 1.0 / (time[1] - time[0])

        filtered_positive = self.low_pass_zero_phase(
            rotated_positive, sample_rate
        )
        filtered_negative = self.low_pass_zero_phase(
            rotated_negative, sample_rate
        )
        reconstructed = np.real(
            filtered_positive * np.conj(phasor)
            + filtered_negative * phasor
        )
        

        # The full chirp excites a broad, symmetric frequency range.
        fft_frequency = np.fft.fftshift(
            np.fft.fftfreq(centered_signal.size, d=time[1] - time[0])
        )
        fft_magnitude = np.abs(
            np.fft.fftshift(np.fft.fft(centered_signal))
        ) / centered_signal.size
        spectrum_limit = max(3.0, 1.5 * CHIRP_END_HZ)
        spectrum_tick = max(spectrum_limit / 3.0, 0.5)
        visible = np.abs(fft_frequency) <= spectrum_limit
        spectrum_frequency = fft_frequency[visible]
        spectrum_magnitude = fft_magnitude[visible]
        spectrum_magnitude /= max(np.max(spectrum_magnitude), 1e-12)

        def spectrum_axes_at(position):
            axes = Axes(
                x_range=[-spectrum_limit, spectrum_limit, spectrum_tick],
                y_range=[0, 1.05, 0.5],
                x_length=11.5,
                y_length=2.55,
                tips=False,
                axis_config={"color": MUTED, "stroke_width": 2},
            )
            axes.move_to(position)
            return axes

        def local_spectrum(carrier_frequency):
            sample_frequency = np.linspace(
                -spectrum_limit, spectrum_limit, 401
            )
            noise_floor = (
                0.045
                + 0.018 * np.sin(8.3 * sample_frequency + 0.4) ** 2
                + 0.012 * np.sin(19.0 * sample_frequency) ** 2
            )
            peaks = 0.82 * (
                np.exp(-0.5 * ((sample_frequency - carrier_frequency) / 0.075) ** 2)
                + np.exp(-0.5 * ((sample_frequency + carrier_frequency) / 0.075) ** 2)
            )
            return sample_frequency, noise_floor + peaks

        step_title = self.make_step_title(
            "Step 3: Relate the chirp frequency to time", PURPLE
        )
        spectrum_axes = spectrum_axes_at(UP * 1.45)
        spectrum_label = Text(
            "Two-sided spectrum of the complete noisy chirp",
            font_size=24,
            color=INK,
        ).next_to(spectrum_axes, UP, buff=0.10)
        spectrum_x_label = Text(
            "frequency [Hz]", font_size=18, color=INK
        ).next_to(spectrum_axes, DOWN, buff=0.08)
        spectrum_graph = self.graph_from_data(
            spectrum_axes,
            spectrum_frequency,
            spectrum_magnitude,
            PURPLE,
            stroke_width=2.4,
        )

        frequency_axes = Axes(
            x_range=[
                0,
                CHIRP_DURATION_S,
                max(CHIRP_DURATION_S / 6.0, 0.1),
            ],
            y_range=[
                0,
                1.05 * CHIRP_END_HZ,
                max(CHIRP_END_HZ / 4.0, 0.05),
            ],
            x_length=11.5,
            y_length=2.15,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).move_to(DOWN * 2.05)
        frequency_graph = self.graph_from_data(
            frequency_axes, time, frequency, ORANGE, stroke_width=3.0
        )
        frequency_label = Text(
            "Instantaneous chirp frequency over time",
            font_size=23,
            color=INK,
        ).next_to(frequency_axes, UP, buff=0.10)
        time_axis_label = Text(
            "time [s]", font_size=18, color=INK
        ).next_to(frequency_axes, DOWN, buff=0.08)

        self.play(
            FadeIn(step_title, shift=DOWN * 0.15),
            FadeIn(spectrum_axes),
            FadeIn(spectrum_label),
            FadeIn(spectrum_x_label),
            run_time=self.TRANSITION_TIME,
        )
        self.play(Create(spectrum_graph), run_time=self.SLOW_DRAW_TIME)
        self.wait(self.WAIT_TIME)
        self.play(
            FadeIn(frequency_axes),
            FadeIn(frequency_label),
            FadeIn(time_axis_label),
            run_time=self.TRANSITION_TIME,
        )
        self.play(Create(frequency_graph), run_time=self.SLOW_DRAW_TIME)
        self.wait(self.LONG_WAIT)

        selected_times = [
            CHIRP_DURATION_S / 6.0,
            CHIRP_DURATION_S / 2.0,
            5.0 * CHIRP_DURATION_S / 6.0,
        ]
        current_marker = None
        current_time_text = None
        for index, selected_time in enumerate(selected_times):
            selected_frequency = float(np.interp(selected_time, time, frequency))
            marker = VGroup(
                DashedLine(
                    frequency_axes.c2p(selected_time, 0),
                    frequency_axes.c2p(selected_time, selected_frequency),
                    color=RED,
                    dash_length=0.10,
                    stroke_width=2.2,
                ),
                Dot(
                    frequency_axes.c2p(selected_time, selected_frequency),
                    radius=0.075,
                    color=RED,
                ),
            )
            local_frequency, local_magnitude = local_spectrum(selected_frequency)
            local_graph = self.graph_from_data(
                spectrum_axes,
                local_frequency,
                local_magnitude,
                PURPLE,
                stroke_width=2.8,
            )
            local_label = Text(
                f"Local spectrum at t = {selected_time:.0f} s",
                font_size=24,
                color=INK,
            ).move_to(spectrum_label)
            time_text = Text(
                f"f(t) = {selected_frequency:.2f} Hz  ->  peaks near +/-{selected_frequency:.2f} Hz",
                font_size=21,
                color=RED,
            ).to_edge(DOWN, buff=0.18)

            animations = [
                Transform(spectrum_graph, local_graph),
                Transform(spectrum_label, local_label),
            ]
            if index == 0:
                animations.extend([FadeIn(marker), FadeIn(time_text)])
            else:
                animations.extend(
                    [
                        ReplacementTransform(current_marker, marker),
                        ReplacementTransform(current_time_text, time_text),
                    ]
                )
            self.play(*animations, run_time=self.DRAW_TIME)
            self.wait(self.WAIT_TIME)
            current_marker = marker
            current_time_text = time_text

        self.wait(self.LONG_WAIT)

        # Demonstrate both conjugate rotation branches.
        carrier_frequency = float(
            np.interp(0.8 * CHIRP_DURATION_S, time, frequency)
        )
        shift_frequency = np.linspace(
            -spectrum_limit, spectrum_limit, 401
        )
        noise_floor = (
            0.05
            + 0.022 * np.sin(8.3 * shift_frequency + 0.4) ** 2
            + 0.014 * np.sin(19.0 * shift_frequency) ** 2
        )
        original_spectrum = noise_floor + 0.82 * (
            np.exp(-0.5 * ((shift_frequency - carrier_frequency) / 0.075) ** 2)
            + np.exp(-0.5 * ((shift_frequency + carrier_frequency) / 0.075) ** 2)
        )
        shifted_left = noise_floor + 0.82 * (
            np.exp(-0.5 * (shift_frequency / 0.075) ** 2)
            + np.exp(
                -0.5
                * ((shift_frequency + 2.0 * carrier_frequency) / 0.075) ** 2
            )
        )
        shifted_right = noise_floor + 0.82 * (
            np.exp(-0.5 * (shift_frequency / 0.075) ** 2)
            + np.exp(
                -0.5
                * ((shift_frequency - 2.0 * carrier_frequency) / 0.075) ** 2
            )
        )
        filtered_baseband = 0.82 * np.exp(
            -0.5 * (shift_frequency / 0.075) ** 2
        )
        returned_positive = 0.82 * np.exp(
            -0.5
            * ((shift_frequency - carrier_frequency) / 0.075) ** 2
        )
        returned_negative = 0.82 * np.exp(
            -0.5
            * ((shift_frequency + carrier_frequency) / 0.075) ** 2
        )

        branch_axes_top = Axes(
            x_range=[-spectrum_limit, spectrum_limit, spectrum_tick],
            y_range=[0, 1.05, 0.5],
            x_length=11.2,
            y_length=2.0,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).move_to(UP * 1.35)
        branch_axes_bottom = branch_axes_top.copy().move_to(DOWN * 1.55)
        branch_x_label = Text(
            "frequency [Hz]", font_size=19, color=INK
        ).next_to(branch_axes_bottom, DOWN, buff=0.08)
        branch_top_label = Text(
            "Branch A: multiply by exp(-j phase)",
            font_size=22,
            color=BLUE,
        ).next_to(branch_axes_top, UP, buff=0.08)
        branch_bottom_label = Text(
            "Branch B: multiply by exp(+j phase)",
            font_size=22,
            color=ORANGE,
        ).next_to(branch_axes_bottom, UP, buff=0.08)
        branch_top_graph = self.graph_from_data(
            branch_axes_top, shift_frequency, original_spectrum, PURPLE, 2.5
        )
        branch_bottom_graph = self.graph_from_data(
            branch_axes_bottom, shift_frequency, original_spectrum, PURPLE, 2.5
        )
        shift_explanation = Text(
            "The two conjugate rotations move opposite frequency peaks to 0 Hz",
            font_size=22,
            color=INK,
        ).to_edge(DOWN, buff=0.22)

        self.play(
            Transform(
                step_title,
                self.make_step_title(
                    "Step 4: Shift both frequency sides to zero", BLUE
                ),
            ),
            FadeOut(frequency_axes),
            FadeOut(frequency_graph),
            FadeOut(frequency_label),
            FadeOut(time_axis_label),
            FadeOut(current_marker),
            FadeOut(current_time_text),
            FadeOut(spectrum_axes),
            FadeOut(spectrum_x_label),
            FadeOut(spectrum_graph),
            FadeOut(spectrum_label),
            FadeIn(branch_axes_top),
            FadeIn(branch_axes_bottom),
            FadeIn(branch_x_label),
            FadeIn(branch_top_label),
            FadeIn(branch_bottom_label),
            FadeIn(branch_top_graph),
            FadeIn(branch_bottom_graph),
            run_time=self.TRANSITION_TIME,
        )
        self.wait(self.WAIT_TIME)

        shifted_top_graph = self.graph_from_data(
            branch_axes_top, shift_frequency, shifted_left, BLUE, 2.8
        )
        shifted_bottom_graph = self.graph_from_data(
            branch_axes_bottom, shift_frequency, shifted_right, ORANGE, 2.8
        )
        shift_arrow_top = Arrow(
            branch_axes_top.c2p(carrier_frequency, 0.90),
            branch_axes_top.c2p(0.05, 0.90),
            buff=0.08,
            color=BLUE,
            stroke_width=4,
        )
        shift_arrow_bottom = Arrow(
            branch_axes_bottom.c2p(-carrier_frequency, 0.90),
            branch_axes_bottom.c2p(-0.05, 0.90),
            buff=0.08,
            color=ORANGE,
            stroke_width=4,
        )
        self.play(
            GrowArrow(shift_arrow_top),
            GrowArrow(shift_arrow_bottom),
            Transform(branch_top_graph, shifted_top_graph),
            Transform(branch_bottom_graph, shifted_bottom_graph),
            FadeIn(shift_explanation),
            run_time=self.SLOW_DRAW_TIME,
        )
        self.wait(self.LONG_WAIT)

        passband_top_left = branch_axes_top.c2p(-FILTER_CUTOFF_HZ, 0)
        passband_top_right = branch_axes_top.c2p(FILTER_CUTOFF_HZ, 1.0)
        passband_top = Rectangle(
            width=passband_top_right[0] - passband_top_left[0],
            height=passband_top_right[1] - passband_top_left[1],
            stroke_color=GREEN,
            stroke_width=3,
            fill_color=GREEN,
            fill_opacity=0.10,
        ).move_to((passband_top_left + passband_top_right) / 2)
        passband_bottom_left = branch_axes_bottom.c2p(-FILTER_CUTOFF_HZ, 0)
        passband_bottom_right = branch_axes_bottom.c2p(FILTER_CUTOFF_HZ, 1.0)
        passband_bottom = Rectangle(
            width=passband_bottom_right[0] - passband_bottom_left[0],
            height=passband_bottom_right[1] - passband_bottom_left[1],
            stroke_color=GREEN,
            stroke_width=3,
            fill_color=GREEN,
            fill_opacity=0.10,
        ).move_to((passband_bottom_left + passband_bottom_right) / 2)
        passband_text = Text(
            f"cutoff = {FILTER_CUTOFF_HZ:.2f} Hz",
            font_size=19,
            color=GREEN,
        ).next_to(passband_top, RIGHT, buff=0.12)
        filtered_top_graph = self.graph_from_data(
            branch_axes_top, shift_frequency, filtered_baseband, BLUE, 3.0
        )
        filtered_bottom_graph = self.graph_from_data(
            branch_axes_bottom, shift_frequency, filtered_baseband, ORANGE, 3.0
        )
        filter_explanation = Text(
            "Both filters retain the baseband component and suppress the remaining spectrum",
            font_size=21,
            color=GREEN,
        ).to_edge(DOWN, buff=0.22)

        self.play(
            Transform(
                step_title,
                self.make_step_title(
                    "Step 5: Remove noise with a zero-phase low-pass filter", GREEN
                ),
            ),
            FadeOut(shift_arrow_top),
            FadeOut(shift_arrow_bottom),
            FadeOut(shift_explanation),
            FadeIn(passband_top),
            FadeIn(passband_bottom),
            FadeIn(passband_text),
            run_time=self.TRANSITION_TIME,
        )
        self.play(
            Transform(branch_top_graph, filtered_top_graph),
            Transform(branch_bottom_graph, filtered_bottom_graph),
            FadeIn(filter_explanation),
            run_time=self.SLOW_DRAW_TIME,
        )
        self.wait(self.LONG_WAIT)

        returned_top_graph = self.graph_from_data(
            branch_axes_top, shift_frequency, returned_positive, BLUE, 3.0
        )
        returned_bottom_graph = self.graph_from_data(
            branch_axes_bottom, shift_frequency, returned_negative, ORANGE, 3.0
        )
        return_arrow_top = Arrow(
            branch_axes_top.c2p(0.05, 0.90),
            branch_axes_top.c2p(carrier_frequency, 0.90),
            buff=0.08,
            color=BLUE,
            stroke_width=4,
        )
        return_arrow_bottom = Arrow(
            branch_axes_bottom.c2p(-0.05, 0.90),
            branch_axes_bottom.c2p(-carrier_frequency, 0.90),
            buff=0.08,
            color=ORANGE,
            stroke_width=4,
        )
        return_explanation = Text(
            "Branch A restores +f(t), while branch B restores -f(t)",
            font_size=22,
            color=INK,
        ).to_edge(DOWN, buff=0.22)

        self.play(
            Transform(
                step_title,
                self.make_step_title(
                    "Step 6: Shift the filtered component back", ORANGE
                ),
            ),
            FadeOut(passband_top),
            FadeOut(passband_bottom),
            FadeOut(passband_text),
            FadeOut(filter_explanation),
            GrowArrow(return_arrow_top),
            GrowArrow(return_arrow_bottom),
            Transform(branch_top_graph, returned_top_graph),
            Transform(branch_bottom_graph, returned_bottom_graph),
            FadeIn(return_explanation),
            run_time=self.SLOW_DRAW_TIME,
        )
        self.wait(self.WAIT_TIME)

        combined_axes = spectrum_axes_at(UP * 0.10)
        combined_x_label = Text(
            "frequency [Hz]", font_size=19, color=INK
        ).next_to(combined_axes, DOWN, buff=0.10)
        combined_label = Text(
            "Recombined two-sided filtered spectrum",
            font_size=25,
            color=INK,
        ).next_to(combined_axes, UP, buff=0.14)
        combined_positive = self.graph_from_data(
            combined_axes, shift_frequency, returned_positive, BLUE, 3.2
        )
        combined_negative = self.graph_from_data(
            combined_axes, shift_frequency, returned_negative, ORANGE, 3.2
        )
        recombine_text = Text(
            "Averaging the conjugate branches produces a real filtered signal",
            font_size=22,
            color=PURPLE,
        ).to_edge(DOWN, buff=0.35)
        self.play(
            FadeOut(branch_axes_top),
            FadeOut(branch_axes_bottom),
            FadeOut(branch_x_label),
            FadeOut(branch_top_label),
            FadeOut(branch_bottom_label),
            FadeOut(return_arrow_top),
            FadeOut(return_arrow_bottom),
            FadeOut(return_explanation),
            FadeIn(combined_axes),
            FadeIn(combined_x_label),
            FadeIn(combined_label),
            Transform(branch_top_graph, combined_positive),
            Transform(branch_bottom_graph, combined_negative),
            FadeIn(recombine_text),
            run_time=self.TRANSITION_TIME,
        )
        self.wait(self.LONG_WAIT)

        # Final comparison in the same visual structure as the reference plot.
        comparison_top = Axes(
            x_range=[
                0,
                CHIRP_DURATION_S,
                max(CHIRP_DURATION_S / 6.0, 0.1),
            ],
            y_range=[
                -(
                    CHIRP_BASE_AMPLITUDE
                    + abs(CHIRP_AMPLITUDE_VARIATION)
                    + 3.0 * NOISE_STANDARD_DEVIATION
                ),
                CHIRP_BASE_AMPLITUDE
                + abs(CHIRP_AMPLITUDE_VARIATION)
                + 3.0 * NOISE_STANDARD_DEVIATION,
                max(
                    (
                        CHIRP_BASE_AMPLITUDE
                        + abs(CHIRP_AMPLITUDE_VARIATION)
                        + 3.0 * NOISE_STANDARD_DEVIATION
                    )
                    / 2.0,
                    0.1,
                ),
            ],
            x_length=12.2,
            y_length=2.35,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).shift(UP * 1.35)
        comparison_bottom = comparison_top.copy().shift(DOWN * 3.65)
        unfiltered_label = Text(
            "Unfiltered signal",
            font_size=25,
            color=INK,
        ).next_to(comparison_top, UP, buff=0.10)
        filtered_label = Text(
            "Filtered signal",
            font_size=25,
            color=INK,
        ).next_to(comparison_bottom, UP, buff=0.10)
        comparison_time_label = Text(
            "time [s]", font_size=19, color=INK
        ).next_to(comparison_bottom, DOWN, buff=0.10)

        noisy_comparison = self.graph_from_data(
            comparison_top, time, centered_signal, BLUE, 1.8
        )
        clean_top = self.graph_from_data(
            comparison_top, time, clean_signal, ORANGE, 3.0
        )
        filtered_comparison = self.graph_from_data(
            comparison_bottom, time, reconstructed, BLUE, 2.7
        )
        clean_bottom = self.graph_from_data(
            comparison_bottom, time, clean_signal, ORANGE, 2.5
        )
        legend = VGroup(
            Line(LEFT * 0.28, RIGHT * 0.28, color=BLUE, stroke_width=4),
            Text("signal", font_size=19, color=INK),
            Line(LEFT * 0.28, RIGHT * 0.28, color=ORANGE, stroke_width=4),
            Text("reference chirp", font_size=19, color=INK),
        ).arrange(RIGHT, buff=0.14)
        legend.move_to(comparison_top.c2p(9.7, 1.08))

        self.play(
            Transform(
                step_title,
                self.make_step_title(
                    "Result: Noise is removed while the chirp is preserved", RED
                ),
            ),
            FadeOut(combined_axes),
            FadeOut(combined_x_label),
            FadeOut(combined_label),
            FadeOut(branch_top_graph),
            FadeOut(branch_bottom_graph),
            FadeOut(recombine_text),
            FadeIn(comparison_top),
            FadeIn(comparison_bottom),
            FadeIn(unfiltered_label),
            FadeIn(filtered_label),
            FadeIn(comparison_time_label),
            run_time=self.TRANSITION_TIME,
        )
        self.play(
            Create(noisy_comparison),
            Create(clean_top),
            FadeIn(legend),
            run_time=self.SLOW_DRAW_TIME,
        )
        self.wait(self.WAIT_TIME)
        self.play(
            Create(filtered_comparison),
            Create(clean_bottom),
            run_time=self.SLOW_DRAW_TIME,
        )
        self.wait(self.LONG_WAIT)


class ApplyRotFiltFilt(ApplyRotFiltFiltPart1):
    pass
