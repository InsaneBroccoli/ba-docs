from manim import *
import theme  # sets URW Gothic as the default Text font
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


class SpectraAnimationBase:
    def graph_from_data(self, axes, x, y, color=BLUE, stroke_width=3):
        graph = VMobject(color=color, stroke_width=stroke_width)
        points = [axes.c2p(float(xi), float(yi)) for xi, yi in zip(x, y)]
        graph.set_points_as_corners(points)
        return graph

    def lollipop_spectrum(self, axes, omega, amp, color=PURPLE):
        spectrum = VGroup()
        max_amp = max(float(np.max(amp)), 1e-9)
        for w, a in zip(omega, amp):
            ratio = min(float(a) / max_amp, 1.0)
            opacity = 0.18 + 0.72 * ratio
            stroke_width = 1.0 + 3.2 * ratio
            stem = Line(
                axes.c2p(float(w), 0),
                axes.c2p(float(w), float(a)),
                color=color,
                stroke_width=stroke_width,
            )
            stem.set_opacity(opacity)
            dot = Dot(
                axes.c2p(float(w), float(a)),
                radius=0.018 + 0.038 * ratio,
                color=color,
                fill_opacity=opacity,
                stroke_width=0,
            )
            spectrum.add(stem, dot)
        return spectrum

    def make_step_title(self, text, color=INK):
        return Text(text, font_size=34, color=color).to_edge(UP, buff=0.35)

    def example_data(self):
        rng = np.random.default_rng(4)
        fs = 80
        t = np.arange(0, 4, 1 / fs)
        f_start = 2
        f_end = 18
        chirp_rate = (f_end - f_start) / 4
        chirp_phase = 2 * np.pi * (f_start * t + 0.5 * chirp_rate * t**2)
        signal = (
            0.60 * np.sin(chirp_phase)
            + 0.12 * np.sin(2 * np.pi * 3 * t + 0.4)
            + 0.08 * np.sin(2 * np.pi * 17 * t + 1.1)
            + 0.18
            + 0.06 * t
            + 0.035 * rng.normal(size=t.size)
        )
        return fs, t, signal, signal - np.mean(signal)


class EstimateSpectraWelchPart1(SpectraAnimationBase, Scene):
    def construct(self):
        fs, t, signal, signal_centered = self.example_data()
        step_title = self.make_step_title("Step 1: Remove global mean", BLUE)

        FAST_TIME = 1.2
        TRANSITION_TIME = 2.0
        DRAW_TIME = 3.5
        SLOW_DRAW_TIME = 5.0
        LONG_WAIT = 4.0

        time_axes = Axes(
            x_range=[0, 4, 1],
            y_range=[-0.8, 1.25, 0.5],
            x_length=6.2,
            y_length=2.35,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        )
        time_axes.add_coordinates(font_size=16, num_decimal_places=0)
        time_axes.to_edge(LEFT, buff=0.6).shift(UP * 0.35)

        time_label = Text("Input signal", font_size=22, color=INK).next_to(time_axes, UP, buff=0.12)
        signal_graph = self.graph_from_data(time_axes, t, signal, BLUE, 3)
        mean_line = DashedLine(
            time_axes.c2p(0, np.mean(signal)),
            time_axes.c2p(4, np.mean(signal)),
            color=RED,
            dash_length=0.12,
            stroke_width=2.5,
        )
        #mean_text = Text("global mean", font_size=18, color=RED).next_to(mean_line, UP, buff=0.08)

        self.play(
            FadeIn(step_title, shift=DOWN * 0.15),
            FadeIn(time_axes),
            FadeIn(time_label),
            run_time=TRANSITION_TIME,
        )
        self.play(Create(signal_graph), run_time=SLOW_DRAW_TIME)
        #self.play(Create(mean_line), FadeIn(mean_text), run_time=TRANSITION_TIME)

        centered_graph = self.graph_from_data(time_axes, t, signal_centered, BLUE, 3)
        mean_formula = Text("centered signal = input signal - global mean", font_size=22, color=INK)
        if mean_formula.width > time_axes.width:
            mean_formula.scale_to_fit_width(time_axes.width)
        mean_formula.next_to(time_axes, DOWN, buff=0.18)
        self.play(
            Transform(signal_graph, centered_graph),
            #FadeOut(mean_text),
            FadeOut(mean_line),
            FadeIn(mean_formula),
            run_time=TRANSITION_TIME,
        )
        self.wait(LONG_WAIT)

        nest = 96
        noverlap = 48
        starts = [0, nest - noverlap, 2 * (nest - noverlap)]
        segment_colors = [ORANGE, GREEN, PURPLE]
        rects = VGroup()
        for start, color in zip(starts, segment_colors):
            t0 = t[start]
            t1 = t[start + nest - 1]
            left = time_axes.c2p(t0, -0.93)
            right = time_axes.c2p(t1, 0.96)
            rect = Rectangle(
                width=right[0] - left[0],
                height=right[1] - left[1],
                stroke_color=color,
                stroke_width=3,
                fill_color=color,
                fill_opacity=0.08,
            )
            rect.move_to((left + right) / 2)
            rects.add(rect)

        overlap_text = Text(
            "Segment length and overlap define the analysis blocks",
            font_size=21,
            color=INK,
        )
        if overlap_text.width > time_axes.width:
            overlap_text.scale_to_fit_width(time_axes.width)
        overlap_text.next_to(time_axes, DOWN, buff=0.18)
        self.play(
            Transform(step_title, self.make_step_title("Step 2: Segment signal with overlap", ORANGE)),
            ReplacementTransform(mean_formula, overlap_text),
            run_time=TRANSITION_TIME,
        )
        self.play(LaggedStart(*[Create(r) for r in rects], lag_ratio=0.25), run_time=SLOW_DRAW_TIME)

        win_axes = Axes(
            x_range=[0, 1, 0.5],
            y_range=[-1.0, 1.1, 0.5],
            x_length=5.1,
            y_length=2.35,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        )
        win_axes.to_edge(RIGHT, buff=0.7).shift(UP * 0.35)
        win_label = Text("Windowed segment", font_size=22, color=INK).next_to(win_axes, UP, buff=0.12)

        n = np.arange(nest)
        xloc = n / (nest - 1)
        segment = signal_centered[starts[0] : starts[0] + nest]
        segment = segment - np.mean(segment)
        window = np.hanning(nest)
        windowed = segment * window

        segment_graph = self.graph_from_data(win_axes, xloc, segment, ORANGE, 2.5)
        window_graph = self.graph_from_data(win_axes, xloc, window, GREEN, 2.5)
        windowed_graph = self.graph_from_data(win_axes, xloc, windowed, BLUE, 3)

        legend = VGroup(
            Dot(color=ORANGE),
            Text("Segment", font_size=17, color=INK),
            Dot(color=GREEN),
            Text("Window", font_size=17, color=INK),
            Dot(color=BLUE),
            Text("windowed segment", font_size=17, color=INK),
        ).arrange(RIGHT, buff=0.12)
        legend.next_to(win_axes, DOWN, buff=0.12)

        self.play(
            Transform(step_title, self.make_step_title("Step 3: Apply window to each segment", GREEN)),
            FadeIn(win_axes),
            FadeIn(win_label),
            run_time=TRANSITION_TIME,
        )
        self.play(Create(segment_graph), run_time=DRAW_TIME)
        self.play(Create(window_graph), run_time=DRAW_TIME)
        self.play(
            Transform(segment_graph, windowed_graph),
            FadeIn(legend),
            run_time=SLOW_DRAW_TIME,
        )

        fft_text = Text("time domain → angular-frequency domain", font_size=24, color=INK)
        fft_text.to_edge(DOWN, buff=0.55)
        self.play(
            Transform(step_title, self.make_step_title("Step 4: Compute FFT and amplitude scaling", PURPLE)),
            FadeIn(fft_text, shift=UP * 0.15),
            run_time=TRANSITION_TIME,
        )
        self.wait(LONG_WAIT)


class EstimateSpectraWelchPart2(SpectraAnimationBase, Scene):
    def construct(self):
        fs, t, signal, signal_centered = self.example_data()
        nest = 96
        noverlap = 48
        all_starts = list(range(0, len(signal_centered) - nest + 1, nest - noverlap))
        shown_starts = [all_starts[0], all_starts[len(all_starts) // 2], all_starts[-1]]
        window = np.hanning(nest)

        TRANSITION_TIME = 2.0
        DRAW_TIME = 3.5
        WAIT_TIME = 1.5
        LONG_WAIT = 4.0

        step_title = self.make_step_title("Step 5: Build and average segment spectra", RED)

        spec_axes = Axes(
            x_range=[0, 130, 25],
            y_range=[0, 0.65, 0.2],
            x_length=8.0,
            y_length=3.25,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        )
        spec_axes.move_to(ORIGIN).shift(UP * 0.25)
        spec_label = Text(
            "Single-sided magnitude over angular frequency",
            font_size=22,
            color=INK,
        ).next_to(spec_axes, UP, buff=0.16)
        omega_label = Text("angular frequency ω [rad/s]", font_size=18, color=INK).next_to(
            spec_axes, DOWN, buff=0.16
        )
        magnitude_label = Text("magnitude", font_size=18, color=INK).rotate(PI / 2).next_to(
            spec_axes, LEFT, buff=0.16
        )

        freqs = np.fft.rfftfreq(nest, d=1 / fs)
        keep = freqs <= 20
        omega = 2 * np.pi * freqs[keep]

        def amp_for(start):
            segment = signal_centered[start : start + nest]
            segment = segment - np.mean(segment)
            fourier_coefficients = np.fft.rfft(segment * window) / (np.sum(window) / 2)
            return np.abs(fourier_coefficients)[keep]

        shown_amps = [amp_for(start) for start in shown_starts]
        avg_amp = np.sqrt(np.mean([amp_for(start) ** 2 for start in all_starts], axis=0))

        bars1 = self.lollipop_spectrum(spec_axes, omega, shown_amps[0], PURPLE)
        bars2 = self.lollipop_spectrum(spec_axes, omega, shown_amps[1], GREEN)
        bars3 = self.lollipop_spectrum(spec_axes, omega, shown_amps[2], ORANGE)
        avg_bars = self.lollipop_spectrum(spec_axes, omega, avg_amp, BLUE)

        spectrum_text = Text("Now showing: Segment 1 spectrum", font_size=24, color=PURPLE)
        segment_2_text = Text("Now showing: Segment 2 spectrum", font_size=24, color=GREEN)
        segment_2_text.move_to(spectrum_text)
        segment_3_text = Text("Now showing: Segment 3 spectrum", font_size=24, color=ORANGE)
        segment_3_text.move_to(spectrum_text)
        averaged_spectrum_text = Text("Now showing: Averaged spectrum", font_size=24, color=BLUE)
        averaged_spectrum_text.move_to(spectrum_text)
        correction_text = Text(
            "Single-sided power correction follows after the transform",
            font_size=20,
            color=RED,
        )
        avg_text = Text(
            "Final power spectrum = average of all segment power spectra",
            font_size=21,
            color=INK,
        )
        sqrt_text = Text(
            "Amplitude spectrum = √(final power spectrum)",
            font_size=23,
            color=BLUE,
        )
        note_group = VGroup(spectrum_text, correction_text, avg_text, sqrt_text).arrange(
            DOWN, buff=0.14
        )
        note_group.next_to(spec_axes, DOWN, buff=0.55)
        segment_2_text.move_to(spectrum_text)
        segment_3_text.move_to(spectrum_text)
        averaged_spectrum_text.move_to(spectrum_text)

        self.play(
            FadeIn(step_title, shift=DOWN * 0.15),
            FadeIn(spec_axes),
            FadeIn(spec_label),
            FadeIn(omega_label),
            FadeIn(magnitude_label),
            run_time=TRANSITION_TIME,
        )
        self.play(FadeIn(bars1), FadeIn(spectrum_text), run_time=DRAW_TIME)
        self.play(FadeIn(correction_text), run_time=WAIT_TIME)
        self.play(Transform(spectrum_text, segment_2_text), Transform(bars1, bars2), run_time=DRAW_TIME)
        self.play(Transform(spectrum_text, segment_3_text), Transform(bars1, bars3), run_time=DRAW_TIME)
        self.play(
            Transform(spectrum_text, averaged_spectrum_text),
            FadeIn(avg_text),
            Transform(bars1, avg_bars),
            run_time=DRAW_TIME,
        )
        self.play(FadeIn(sqrt_text), run_time=WAIT_TIME)
        self.wait(LONG_WAIT)

        final = VGroup(
            Text("Algorithm overview", font_size=30, color=INK),
            Text("1. Remove the global mean from the input signal", font_size=23, color=INK),
            Text("2. Split the signal into overlapping analysis segments", font_size=23, color=INK),
            Text("3. Remove segment mean and multiply by the window", font_size=22, color=INK),
            Text("4. Compute the Fourier transform with amplitude scaling", font_size=22, color=INK),
            Text("5. Build single-sided power and correct direct-current/Nyquist bins", font_size=22, color=INK),
            Text("6. Average all segment power spectra → final power spectrum", font_size=22, color=INK),
            Text("Amplitude spectrum = √(final power spectrum)", font_size=24, color=BLUE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        final.move_to(ORIGIN).shift(DOWN * 0.1)

        self.play(
            Transform(step_title, self.make_step_title("Overview: Welch spectrum estimation", INK)),
            FadeOut(note_group),
            FadeOut(spec_axes),
            FadeOut(spec_label),
            FadeOut(omega_label),
            FadeOut(magnitude_label),
            FadeOut(bars1),
            FadeIn(final, shift=RIGHT * 0.2),
            run_time=TRANSITION_TIME,
        )
        self.wait(LONG_WAIT)


class EstimateSpectraWelch(EstimateSpectraWelchPart1):
    pass
