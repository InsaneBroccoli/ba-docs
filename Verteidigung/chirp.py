from manim import *
import theme  # sets URW Gothic as the default Text font
import numpy as np


class ChirpSignalAnimation(Scene):
    def construct(self):

        # ==========================================
        # Global settings
        # ==========================================
        TIME_SCALE = 1.5
        self.camera.background_color = "#F6EEE1"

        # ==========================================
        # Chirp parameters
        # ==========================================
        f0 = 1
        f1 = 50
        T = 20
        N = 5000

        # Plot margins
        PLOT_START_MARGIN = 0.0

        # Axis extends beyond the chirp
        AXIS_END_MARGIN = 1.5
        AXIS_END = T + AXIS_END_MARGIN

        # ==========================================
        # Lag-filter parameters
        # ==========================================
        fp = 5
        fz = 20

        # ==========================================
        # Low-frequency scaling parameters
        # ==========================================
        low_frequency_limit = 1.5
        scaling_strength = 4.0

        # ==========================================
        # Generate chirp once
        # ==========================================
        t = np.linspace(0, T, N)

        ratio = f1 / f0
        f_t = f0 * ratio ** (t / T)

        phi = (
            2 * np.pi * T * f0 / np.log(ratio)
            * (ratio ** (t / T) - 1)
        )

        x = np.sin(phi)

        # ==========================================
        # Lag-filter envelope
        # ==========================================
        lag_gain = np.sqrt(
            (1 + (f_t / fz) ** 2)
            / (1 + (f_t / fp) ** 2)
        )

        x_filtered = lag_gain * x

        # ==========================================
        # Additional scaling below 1.5 Hz
        # ==========================================
        low_frequency_gain = np.where(
            f_t < low_frequency_limit,
            (f_t / low_frequency_limit) ** scaling_strength,
            1.0
        )

        combined_gain = lag_gain * low_frequency_gain
        x_low_scaled = combined_gain * x

        # ==========================================
        # Helper function
        # ==========================================
        def make_curve(
            axes,
            x_values,
            y_values,
            color,
            stroke_width=2
        ):
            visible = (
                (x_values >= PLOT_START_MARGIN)
                & (x_values <= T)
            )

            points = [
                axes.c2p(xi, yi)
                for xi, yi in zip(
                    x_values[visible],
                    y_values[visible]
                )
            ]

            curve = VMobject(
                color=color,
                stroke_width=stroke_width
            )

            curve.set_points_as_corners(points)
            return curve

        # ==========================================
        # Slide 1: Original chirp
        # ==========================================
        title = Text(
            "Exponential Chirp Signal",
            font_size=36,
            color=BLACK
        )
        title.to_edge(UP)

        signal_axes = Axes(
            x_range=[0, AXIS_END, 5],
            y_range=[-1.2, 1.2, 0.5],
            x_length=10,
            y_length=2.5,
            axis_config={
                "include_numbers": False,
                "color": BLACK
            },
        )
        signal_axes.next_to(title, DOWN, buff=0.5)

        signal_label = Text(
            "Signal x(t)",
            font_size=22,
            color=BLACK
        )
        signal_label.next_to(signal_axes, LEFT)
        signal_label.shift(LEFT * 0.01)

        freq_axes = Axes(
            x_range=[0, AXIS_END, 5],
            y_range=[0, 55, 10],
            x_length=10,
            y_length=2.5,
            axis_config={
                "include_numbers": False,
                "color": BLACK
            },
        )
        freq_axes.next_to(signal_axes, DOWN, buff=0.8)

        freq_label = Text(
            "Frequency f(t)",
            font_size=22,
            color=BLACK
        )
        freq_label.next_to(freq_axes, LEFT)
        freq_label.shift(LEFT * -0.35)

        signal_curve = make_curve(
            signal_axes,
            t,
            x,
            BLUE,
            stroke_width=2
        )

        freq_curve = make_curve(
            freq_axes,
            t,
            f_t,
            GREEN,
            stroke_width=3
        )

        self.play(
            Write(title),
            run_time=1.0 * TIME_SCALE
        )

        self.play(
            Create(signal_axes),
            Create(freq_axes),
            FadeIn(signal_label),
            FadeIn(freq_label),
            run_time=2.0 * TIME_SCALE
        )

        self.play(
            Create(signal_curve),
            Create(freq_curve),
            run_time=6.0 * TIME_SCALE,
            rate_func=linear
        )

        self.wait(1.5 * TIME_SCALE)

        # ==========================================
        # Slide 2: Apply lag filter
        # ==========================================
        title_filtered = Text(
            "Lag Filter Applied to the Chirp Signal",
            font_size=34,
            color=BLACK
        )
        title_filtered.to_edge(UP)

        zoom_axes = Axes(
            x_range=[0, AXIS_END, 5],
            y_range=[-1.2, 1.2, 0.5],
            x_length=10,
            y_length=5,
            axis_config={
                "include_numbers": False,
                "color": BLACK
            },
        )
        zoom_axes.next_to(title_filtered, DOWN, buff=0.6)

        zoom_label = Text(
            "Signal x(t)",
            font_size=22,
            color=BLACK
        )
        zoom_label.next_to(zoom_axes, LEFT)
        zoom_label.shift(LEFT * 0.01)

        original_zoom_curve = make_curve(
            zoom_axes,
            t,
            x,
            BLUE,
            stroke_width=2
        )

        filtered_curve = make_curve(
            zoom_axes,
            t,
            x_filtered,
            BLUE,
            stroke_width=2
        )

        upper_envelope = make_curve(
            zoom_axes,
            t,
            lag_gain,
            GREEN,
            stroke_width=3
        )

        lower_envelope = make_curve(
            zoom_axes,
            t,
            -lag_gain,
            GREEN,
            stroke_width=3
        )

        filter_label = Text(
            "Lag filter envelope",
            font_size=22,
            color=BLACK
        )
        filter_label.next_to(zoom_axes, DOWN, buff=0.25)

        self.play(
            FadeOut(freq_axes),
            FadeOut(freq_curve),
            FadeOut(freq_label),
            FadeOut(signal_label),
            Transform(title, title_filtered),
            Transform(signal_axes, zoom_axes),
            Transform(signal_curve, original_zoom_curve),
            FadeIn(zoom_label),
            run_time=2.0 * TIME_SCALE
        )

        self.play(
            Create(upper_envelope),
            Create(lower_envelope),
            FadeIn(filter_label),
            run_time=2.0 * TIME_SCALE
        )

        self.play(
            Transform(signal_curve, filtered_curve),
            run_time=3.0 * TIME_SCALE,
            rate_func=smooth
        )

        self.wait(2.0 * TIME_SCALE)

        # ==========================================
        # Slide 3: Scaling below 1.5 Hz
        # ==========================================
        title_low_frequency = Text(
            "Low-Frequency Scaling",
            font_size=34,
            color=BLACK
        )
        title_low_frequency.to_edge(UP)

        low_scaled_curve = make_curve(
            zoom_axes,
            t,
            x_low_scaled,
            BLUE,
            stroke_width=2
        )

        final_upper_envelope = make_curve(
            zoom_axes,
            t,
            combined_gain,
            RED,
            stroke_width=3
        )

        final_lower_envelope = make_curve(
            zoom_axes,
            t,
            -combined_gain,
            RED,
            stroke_width=3
        )

        final_filter_label = Text(
            "Combined filter envelope",
            font_size=22,
            color=BLACK
        )
        final_filter_label.next_to(
            zoom_axes,
            DOWN,
            buff=0.25
        )

        # Time when the chirp reaches 1.5 Hz
        t_limit = (
            T
            * np.log(low_frequency_limit / f0)
            / np.log(f1 / f0)
        )

        limit_line = DashedLine(
            zoom_axes.c2p(t_limit, -1.2),
            zoom_axes.c2p(t_limit, 1.2),
            color=BLACK,
            stroke_width=2
        )

        self.play(
            Transform(title, title_low_frequency),
            Transform(signal_curve, low_scaled_curve),
            Transform(upper_envelope, final_upper_envelope),
            Transform(lower_envelope, final_lower_envelope),
            Transform(filter_label, final_filter_label),
            FadeIn(limit_line),
            run_time=3.0 * TIME_SCALE,
            rate_func=smooth
        )

        self.wait(3.0 * TIME_SCALE)
