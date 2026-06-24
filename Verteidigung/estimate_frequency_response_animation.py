from manim import *
import numpy as np


# Render settings ------------------------------------------------------------
config.background_color = "#F6EEE1"
config.frame_width = 16
config.frame_height = 9
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_rate = 30

# Timing: increase these values to slow down the complete video.
DRAW_TIME = 2.2
TRANSITION_TIME = 1.4
SHORT_WAIT = 1.2
LONG_WAIT = 3.0

# Visual style
INK = "#111827"
MUTED = "#6B7280"
GRID = "#D1D5DB"
BLUE = "#2563EB"
ORANGE = "#F97316"
GREEN = "#16A34A"
PURPLE = "#7C3AED"
RED = "#DC2626"


class FrequencyResponseBase(Scene):
    """Shared data and drawing helpers for both PowerPoint-ready scenes."""

    def title(self, text, color=INK):
        return Text(text, font_size=34, color=color, weight="SEMIBOLD").to_edge(UP, buff=0.28)

    def graph(self, axes, x, y, color=BLUE, width=3.0):
        points = [axes.c2p(float(xi), float(yi)) for xi, yi in zip(x, y)]
        return VMobject(color=color, stroke_width=width).set_points_as_corners(points)

    def small_axes(self, x_range, y_range, x_length=6.2, y_length=2.25):
        axes = Axes(
            x_range=x_range,
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 1.8},
        )
        axes.add_coordinates(font_size=16, color=MUTED)
        return axes

    def example_data(self):
        """Deterministic broadband input and output of a low-pass plant."""
        rng = np.random.default_rng(12)
        fs = 80.0
        duration = 12.0
        t = np.arange(0, duration, 1 / fs)

        freqs = np.array([0.8, 1.5, 2.8, 4.2, 6.0, 8.5, 11.0, 14.0, 17.5])
        amps = np.array([0.28, 0.23, 0.26, 0.18, 0.22, 0.15, 0.12, 0.10, 0.08])
        phases = rng.uniform(0, 2 * np.pi, len(freqs))
        u = sum(a * np.sin(2 * np.pi * f * t + p) for f, a, p in zip(freqs, amps, phases))
        u += 0.025 * rng.normal(size=t.size) + 0.12

        # Discrete first-order low-pass response, fc approximately 5 Hz.
        tau = 1 / (2 * np.pi * 5.0)
        alpha = (1 / fs) / (tau + 1 / fs)
        y = np.zeros_like(u)
        for k in range(1, len(u)):
            y[k] = y[k - 1] + alpha * (u[k] - y[k - 1])
        y += 0.035 * rng.normal(size=t.size) - 0.08
        return fs, t, u, y

    def welch_spectra(self):
        fs, t, u, y = self.example_data()
        u = u - np.mean(u)
        y = y - np.mean(y)
        nest = 256
        noverlap = 192
        step = nest - noverlap
        window = np.hanning(nest)
        scale = np.sum(window) / 2
        suu = []
        syu = []
        syy = []
        starts = list(range(0, len(u) - nest + 1, step))
        for start in starts:
            us = u[start:start + nest] - np.mean(u[start:start + nest])
            ys = y[start:start + nest] - np.mean(y[start:start + nest])
            U = np.fft.rfft(us * window) / scale
            Y = np.fft.rfft(ys * window) / scale
            a = U * np.conj(U)
            b = Y * np.conj(U)
            c = Y * np.conj(Y)
            a[[0, -1]] /= 4
            b[[0, -1]] /= 4
            c[[0, -1]] /= 4
            suu.append(a)
            syu.append(b)
            syy.append(c)
        freq = np.fft.rfftfreq(nest, 1 / fs)
        return fs, t, u, y, nest, noverlap, starts, window, freq, np.mean(suu, 0), np.mean(syu, 0), np.mean(syy, 0)


class EstimateFrequencyResponsePart1(FrequencyResponseBase):
    """Part 1: from input/output signals to the three Welch spectra."""

    def construct(self):
        fs, t, u, y, nest, noverlap, starts, window, freq, suu, syu, syy = self.welch_spectra()

        heading = self.title("Step 1: Remove the mean from input and output", BLUE)
        axes_u = self.small_axes([0, 6, 1], [-1.2, 1.2, 0.5], 6.0, 2.05).to_edge(LEFT, 0.65).shift(UP * 1.15)
        axes_y = self.small_axes([0, 6, 1], [-1.0, 1.0, 0.5], 6.0, 2.05).to_edge(LEFT, 0.65).shift(DOWN * 2.2)
        show = t <= 6
        u_raw = self.example_data()[2][show]
        y_raw = self.example_data()[3][show]
        gu = self.graph(axes_u, t[show], u_raw, BLUE)
        gy = self.graph(axes_y, t[show], y_raw, ORANGE)
        label_u = Text("Input signal", font_size=22, color=BLUE).next_to(axes_u, UP, 0.08)
        label_y = Text("Output signal", font_size=22, color=ORANGE).next_to(axes_y, UP, 0.08)
        time_u = MathTex(r"t\,[\mathrm{s}]", font_size=25, color=INK).next_to(axes_u, DOWN, 0.12)
        time_y = MathTex(r"t\,[\mathrm{s}]", font_size=25, color=INK).next_to(axes_y, DOWN, 0.12)

        formulas = VGroup(
            MathTex(r"u_0[n]=u[n]-\overline{u}", font_size=36, color=BLUE),
            MathTex(r"y_0[n]=y[n]-\overline{y}", font_size=36, color=ORANGE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.45).to_edge(RIGHT, 1.15)

        # Make the subtraction of the constant (DC) component visible.
        mean_u = float(np.mean(u_raw))
        mean_y = float(np.mean(y_raw))
        dc_line_u = DashedLine(
            axes_u.c2p(0, mean_u), axes_u.c2p(6, mean_u),
            color=RED, stroke_width=2.5, dash_length=0.12,
        )
        dc_line_y = DashedLine(
            axes_y.c2p(0, mean_y), axes_y.c2p(6, mean_y),
            color=RED, stroke_width=2.5, dash_length=0.12,
        )
        dc_label_u = Text("DC component", font_size=18, color=RED).next_to(dc_line_u, UP, 1.0).align_to(dc_line_u, RIGHT)
        dc_label_y = Text("DC component", font_size=18, color=RED).next_to(dc_line_y, UP, 1.0).align_to(dc_line_y, RIGHT)

        self.play(FadeIn(heading), FadeIn(axes_u), FadeIn(axes_y), FadeIn(label_u), FadeIn(label_y), FadeIn(time_u), FadeIn(time_y), run_time=TRANSITION_TIME)
        self.play(Create(gu), Create(gy), run_time=DRAW_TIME)
        self.play(Create(dc_line_u), Create(dc_line_y), FadeIn(dc_label_u), FadeIn(dc_label_y), run_time=DRAW_TIME)
        gu_center = self.graph(axes_u, t[show], u[show], BLUE)
        gy_center = self.graph(axes_y, t[show], y[show], ORANGE)
        zero_line_u = DashedLine(axes_u.c2p(0, 0), axes_u.c2p(6, 0), color=GREEN, stroke_width=2.5, dash_length=0.12)
        zero_line_y = DashedLine(axes_y.c2p(0, 0), axes_y.c2p(6, 0), color=GREEN, stroke_width=2.5, dash_length=0.12)
        zero_label_u = Text("zero mean", font_size=18, color=GREEN).next_to(zero_line_u, UP, 1.0).align_to(zero_line_u, RIGHT)
        zero_label_y = Text("zero mean", font_size=18, color=GREEN).next_to(zero_line_y, UP, 1.00).align_to(zero_line_y, RIGHT)
        self.play(
            Transform(gu, gu_center), Transform(gy, gy_center),
            Transform(dc_line_u, zero_line_u), Transform(dc_line_y, zero_line_y),
            Transform(dc_label_u, zero_label_u), Transform(dc_label_y, zero_label_y),
            FadeIn(formulas, shift=LEFT * 0.2),
            run_time=DRAW_TIME,
        )
        self.wait(LONG_WAIT)

        # Step 2: show identical segmentation on input and output.
        new_heading = self.title("Step 2: Divide both signals into overlapping segments", ORANGE)
        self.play(
            Transform(heading, new_heading),
            FadeOut(formulas), FadeOut(dc_line_u), FadeOut(dc_line_y),
            FadeOut(dc_label_u), FadeOut(dc_label_y),
            FadeOut(axes_u), FadeOut(axes_y),
            FadeOut(gu), FadeOut(gy), FadeOut(label_u), FadeOut(label_y),
            FadeOut(time_u), FadeOut(time_y),
            run_time=TRANSITION_TIME,
        )

        seg_axes_u = self.small_axes([0, 6, 1], [-1.2, 1.2, 0.5], 10.2, 1.65).shift(UP * 1.25)
        seg_axes_y = self.small_axes([0, 6, 1], [-1.0, 1.0, 0.5], 10.2, 1.65).shift(DOWN * 1.15)
        seg_graph_u = self.graph(seg_axes_u, t[show], u[show], BLUE, 2.6)
        seg_graph_y = self.graph(seg_axes_y, t[show], y[show], ORANGE, 2.6)
        seg_label_u = Text("Input signal", font_size=21, color=BLUE).next_to(seg_axes_u, UP, 0.08)
        seg_label_y = Text("Output signal", font_size=21, color=ORANGE).next_to(seg_axes_y, UP, 0.08)

        rectangles_u = VGroup()
        rectangles_y = VGroup()
        segment_seconds = nest / fs
        shift_seconds = (nest - noverlap) / fs
        for i, start_time in enumerate([0, shift_seconds, 2 * shift_seconds]):
            col = [ORANGE, GREEN, PURPLE][i]
            for axes, ymin, ymax, group in [
                (seg_axes_u, -1.12, 1.12, rectangles_u),
                (seg_axes_y, -0.92, 0.92, rectangles_y),
            ]:
                left = axes.c2p(start_time, ymin)
                right = axes.c2p(start_time + segment_seconds, ymax)
                rect = Rectangle(
                    width=right[0] - left[0], height=right[1] - left[1],
                    stroke_color=col, stroke_width=3,
                    fill_color=col, fill_opacity=0.07,
                ).move_to((left + right) / 2)
                group.add(rect)

        overlap_note = VGroup(
            Text("Each coloured frame represents one segment", font_size=22, color=INK),
            Text("Shift to the next segment = segment length − overlap", font_size=22, color=INK),
        ).arrange(DOWN, buff=0.15).to_edge(DOWN, 0.22)

        self.play(
            FadeIn(seg_axes_u), FadeIn(seg_axes_y),
            FadeIn(seg_label_u), FadeIn(seg_label_y),
            Create(seg_graph_u), Create(seg_graph_y),
            run_time=DRAW_TIME,
        )
        paired_rectangles = [
            AnimationGroup(Create(rectangles_u[i]), Create(rectangles_y[i]))
            for i in range(3)
        ]
        self.play(
            LaggedStart(*paired_rectangles, lag_ratio=0.30),
            FadeIn(overlap_note),
            run_time=DRAW_TIME * 1.5,
        )
        self.wait(LONG_WAIT)

        # Step 3: window and Fourier transforms.
        self.play(Transform(heading, self.title("Step 3: Apply the window and compute both Fourier transforms", GREEN)),
                  FadeOut(seg_axes_u), FadeOut(seg_axes_y),
                  FadeOut(seg_graph_u), FadeOut(seg_graph_y),
                  FadeOut(seg_label_u), FadeOut(seg_label_y),
                  FadeOut(rectangles_u), FadeOut(rectangles_y),
                  FadeOut(overlap_note), run_time=TRANSITION_TIME)

        n = np.arange(nest)
        us = u[:nest] - np.mean(u[:nest])
        ys = y[:nest] - np.mean(y[:nest])
        us_w = us * window
        ys_w = ys * window
        local_t = n / fs
        ax_in = self.small_axes([0, nest / fs, 1], [-1.1, 1.1, 0.5], 6.0, 2.15).to_edge(LEFT, 0.65).shift(UP * 1.05)
        ax_out = self.small_axes([0, nest / fs, 1], [-0.9, 0.9, 0.4], 6.0, 2.15).to_edge(LEFT, 0.65).shift(DOWN * 1.65)
        g_in = self.graph(ax_in, local_t, us, BLUE, 2.5)
        g_out = self.graph(ax_out, local_t, ys, ORANGE, 2.5)
        g_in_w = self.graph(ax_in, local_t, us_w, BLUE, 3.0)
        g_out_w = self.graph(ax_out, local_t, ys_w, ORANGE, 3.0)
        win_scaled_in = self.graph(ax_in, local_t, window, GREEN, 2.2)
        win_scaled_out = self.graph(ax_out, local_t, 0.75 * window, GREEN, 2.2)
        labs = VGroup(Text("Input segment", font_size=21, color=BLUE).next_to(ax_in, UP, 0.08),
                      Text("Output segment", font_size=21, color=ORANGE).next_to(ax_out, UP, 0.08))
        equations = VGroup(
            MathTex(r"U_k(\omega)=\mathcal{F}\!\left\{u_k[n]\cdot\operatorname{window}[n]\right\}", font_size=29, color=BLUE),
            MathTex(r"Y_k(\omega)=\mathcal{F}\!\left\{y_k[n]\cdot\operatorname{window}[n]\right\}", font_size=29, color=ORANGE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.38).to_edge(RIGHT, 0.7)
        self.play(FadeIn(ax_in), FadeIn(ax_out), FadeIn(labs), Create(g_in), Create(g_out), run_time=DRAW_TIME)
        self.play(Create(win_scaled_in), Create(win_scaled_out), run_time=DRAW_TIME)
        self.play(Transform(g_in, g_in_w), Transform(g_out, g_out_w), FadeOut(win_scaled_in), FadeOut(win_scaled_out), run_time=DRAW_TIME)
        self.play(FadeIn(equations, shift=LEFT * 0.2), run_time=TRANSITION_TIME)
        self.wait(LONG_WAIT)

        # Step 4: make three spectra and average.
        self.play(Transform(heading, self.title("Step 4: Form and average three spectral quantities", PURPLE)),
                  FadeOut(ax_in), FadeOut(ax_out), FadeOut(labs), FadeOut(g_in), FadeOut(g_out), FadeOut(equations), run_time=TRANSITION_TIME)

        # Use real segment spectra as small graphical icons.
        first_u = u[:nest] - np.mean(u[:nest])
        first_y = y[:nest] - np.mean(y[:nest])
        U_icon = np.abs(np.fft.rfft(first_u * window))
        Y_icon = np.abs(np.fft.rfft(first_y * window))
        icon_keep = freq <= 20
        icon_freq = freq[icon_keep]
        U_icon = U_icon[icon_keep] / max(np.max(U_icon[icon_keep]), 1e-12)
        Y_icon = Y_icon[icon_keep] / max(np.max(Y_icon[icon_keep]), 1e-12)

        def spectrum_icon(values, color, label, position):
            axes = Axes(
                x_range=[0, 20, 10], y_range=[0, 1.05, 0.5],
                x_length=1.45, y_length=0.72, tips=False,
                axis_config={"color": MUTED, "stroke_width": 1.2, "include_ticks": False},
            ).move_to(position)
            curve = self.graph(axes, icon_freq, values, color, 2.2)
            text = Text(label, font_size=16, color=color).next_to(axes, UP, 0.05)
            return VGroup(axes, curve, text)

        card_centres = [LEFT * 5.05 + UP * 0.95, UP * 0.95, RIGHT * 5.05 + UP * 0.95]
        cards = VGroup()
        pair_groups = VGroup()
        result_groups = VGroup()
        card_data = [
            (U_icon, BLUE, "Input", U_icon, BLUE, "Input conjugate", "Input power", r"S_{uu,k}=U_kU_k^{*}", BLUE),
            (Y_icon, ORANGE, "Output", U_icon, BLUE, "Input conjugate", "Cross spectrum", r"S_{yu,k}=Y_kU_k^{*}", PURPLE),
            (Y_icon, ORANGE, "Output", Y_icon, ORANGE, "Output conjugate", "Output power", r"S_{yy,k}=Y_kY_k^{*}", ORANGE),
        ]

        for centre, data in zip(card_centres, card_data):
            left_values, left_color, left_label, right_values, right_color, right_label, result_label, equation, result_color = data
            card = RoundedRectangle(
                width=4.55, height=3.05, corner_radius=0.18,
                color=GRID, stroke_width=2, fill_color="#F9FAFB", fill_opacity=1,
            ).move_to(centre)
            left_icon = spectrum_icon(left_values, left_color, left_label, centre + LEFT * 1.05 + UP * 0.52)
            right_icon = spectrum_icon(right_values, right_color, right_label, centre + RIGHT * 1.05 + UP * 0.52)
            multiply = MathTex(r"\times", font_size=31, color=INK).move_to(centre + UP * 0.48)
            arrow = Arrow(
                centre + UP * 0.02, centre + DOWN * 0.47,
                buff=0.03, color=MUTED, stroke_width=2.5, max_tip_length_to_length_ratio=0.25,
            )
            result = Text(result_label, font_size=22, color=result_color, weight="SEMIBOLD").move_to(centre + DOWN * 0.73)
            formula_small = MathTex(equation, font_size=25, color=result_color).move_to(centre + DOWN * 1.15)
            cards.add(card)
            pair_groups.add(VGroup(left_icon, right_icon, multiply))
            result_groups.add(VGroup(arrow, result, formula_small))

        averaging = VGroup(
            Text("Repeat for every segment", font_size=22, color=INK),
            MathTex(r"\text{Average over all segments:}\quad \widehat{S}=\frac{1}{K}\sum_{k=1}^{K}S_k", font_size=31, color=INK),
        ).arrange(DOWN, buff=0.12).shift(DOWN * 1.18)
        correction = VGroup(
            Text("Keep only frequencies from direct current to Nyquist", font_size=23, color=INK),
            Text("Correct direct-current and Nyquist bins by dividing their power by four", font_size=21, color=RED),
        ).arrange(DOWN, buff=0.13).shift(DOWN * 2.10)
        output_box = RoundedRectangle(width=11.3, height=0.68, corner_radius=0.15, color=GREEN, stroke_width=2).shift(DOWN * 3.5)
        output_text = MathTex(r"P_{\mathrm{avg}}=\left[\widehat{S}_{uu},\;\widehat{S}_{yu},\;\widehat{S}_{yy}\right]", font_size=35, color=GREEN).move_to(output_box)

        self.play(LaggedStart(*[FadeIn(card) for card in cards], lag_ratio=0.18), run_time=TRANSITION_TIME)
        self.play(LaggedStart(*[FadeIn(pair, shift=UP * 0.12) for pair in pair_groups], lag_ratio=0.22), run_time=DRAW_TIME)
        self.play(LaggedStart(*[FadeIn(result) for result in result_groups], lag_ratio=0.22), run_time=DRAW_TIME)
        self.play(FadeIn(averaging, shift=UP * 0.12), run_time=TRANSITION_TIME)
        self.play(FadeIn(correction), run_time=TRANSITION_TIME)
        self.play(Create(output_box), FadeIn(output_text), run_time=TRANSITION_TIME)
        self.wait(LONG_WAIT)


class EstimateFrequencyResponsePart2(FrequencyResponseBase):
    """Part 2: frequency response and coherence from averaged spectra."""

    def construct(self):
        fs, t, u, y, nest, noverlap, starts, window, freq, suu, syu, syy = self.welch_spectra()
        g = syu / suu
        coherence = np.clip(np.abs(syu) ** 2 / (suu * syy), 0, 1)
        keep = (freq >= 0.35) & (freq <= 20)
        f = freq[keep]
        mag = 20 * np.log10(np.maximum(np.abs(g[keep]), 1e-7))
        # Display the physically relevant phase range of this low-pass example.
        phase = np.clip(np.rad2deg(np.unwrap(np.angle(g[keep]))), -90, 0)
        coh = np.real(coherence[keep])

        heading = self.title("Step 5: Calculate the frequency-response estimate", BLUE)
        source = MathTex(r"P_{\mathrm{avg}}=\left[\widehat{S}_{uu},\;\widehat{S}_{yu},\;\widehat{S}_{yy}\right]", font_size=38, color=GREEN).shift(UP * 1.55)
        arrow = Arrow(UP * 0.9, DOWN * 0.2, color=MUTED, stroke_width=3, buff=0.05)
        formula = MathTex(r"\widehat{G}(\omega)=\frac{\widehat{S}_{yu}(\omega)}{\widehat{S}_{uu}(\omega)}", font_size=50, color=BLUE).shift(DOWN * 0.65)
        note = Text("Cross spectrum divided by the input power spectrum", font_size=22, color=MUTED).shift(DOWN * 1.75)
        self.play(FadeIn(heading), FadeIn(source), run_time=TRANSITION_TIME)
        self.play(GrowArrow(arrow), FadeIn(formula, shift=DOWN * 0.15), run_time=DRAW_TIME)
        self.play(FadeIn(note), run_time=TRANSITION_TIME)
        self.wait(LONG_WAIT)

        # Bode magnitude and phase.
        self.play(Transform(heading, self.title("The estimate contains magnitude and phase", BLUE)),
                  FadeOut(source), FadeOut(arrow), FadeOut(formula), FadeOut(note), run_time=TRANSITION_TIME)
        xlog = np.log10(f)
        x_range = [np.log10(0.35), np.log10(20), 0.5]
        ax_mag = self.small_axes(x_range, [-25, 5, 10], 10.2, 2.25).shift(UP * 1.2)
        ax_phase = self.small_axes(x_range, [-90, 5, 30], 10.2, 2.25).shift(DOWN * 1.65)
        gm = self.graph(ax_mag, xlog, mag, BLUE, 3.2)
        gp = self.graph(ax_phase, xlog, phase, ORANGE, 3.2)
        mag_lab = MathTex(r"20\log_{10}|\widehat{G}|\;[\mathrm{dB}]", font_size=26, color=BLUE).next_to(ax_mag, LEFT, 0.18)
        phase_lab = MathTex(r"\angle\widehat{G}\;[{}^\circ]", font_size=26, color=ORANGE).next_to(ax_phase, LEFT, 0.18)
        freq_lab = MathTex(r"f\;[\mathrm{Hz}]", font_size=26, color=INK).next_to(ax_phase, DOWN, 0.15)
        tick_labels = VGroup()
        for val in [0.5, 1, 2, 5, 10, 20]:
            lbl = Text(str(val), font_size=15, color=MUTED).next_to(ax_phase.c2p(np.log10(val), -90), DOWN, 0.12)
            tick_labels.add(lbl)
        self.play(FadeIn(ax_mag), FadeIn(ax_phase), FadeIn(mag_lab), FadeIn(phase_lab), FadeIn(freq_lab), FadeIn(tick_labels), run_time=TRANSITION_TIME)
        self.play(Create(gm), Create(gp), run_time=DRAW_TIME * 1.5)
        self.wait(LONG_WAIT)

        # Coherence gets its own clean screen.
        self.play(Transform(heading, self.title("Step 6: Use coherence as a reliability indicator", PURPLE)),
                  FadeOut(ax_mag), FadeOut(ax_phase), FadeOut(gm), FadeOut(gp), FadeOut(mag_lab), FadeOut(phase_lab), FadeOut(freq_lab), FadeOut(tick_labels), run_time=TRANSITION_TIME)
        coh_formula = MathTex(
            r"\gamma^2(\omega)=\frac{|\widehat{S}_{yu}(\omega)|^2}{\widehat{S}_{uu}(\omega)\widehat{S}_{yy}(\omega)}",
            font_size=44, color=PURPLE,
        ).shift(UP * 2.1)
        ax_coh = self.small_axes(x_range, [0, 1.05, 0.25], 10.5, 3.4).shift(DOWN * 0.25)
        gc = self.graph(ax_coh, xlog, coh, PURPLE, 3.5)
        freq_lab2 = MathTex(r"f\;[\mathrm{Hz}]", font_size=26, color=INK).next_to(ax_coh, DOWN, 0.17)
        tick_labels2 = VGroup()
        for val in [0.5, 1, 2, 5, 10, 20]:
            tick_labels2.add(Text(str(val), font_size=15, color=MUTED).next_to(ax_coh.c2p(np.log10(val), 0), DOWN, 0.12))
        reliable = DashedLine(ax_coh.c2p(x_range[0], 0.8), ax_coh.c2p(x_range[1], 0.8), color=GREEN, stroke_width=2)
        reliable_text = Text("high reliability", font_size=19, color=GREEN).next_to(reliable, UP, 0.06).align_to(reliable, LEFT)
        self.play(FadeIn(coh_formula), FadeIn(ax_coh), FadeIn(freq_lab2), FadeIn(tick_labels2), run_time=TRANSITION_TIME)
        self.play(Create(reliable), FadeIn(reliable_text), Create(gc), run_time=DRAW_TIME * 1.5)
        interpretation = VGroup(
            Text("close to 1: output is strongly linearly related to the input", font_size=22, color=GREEN),
            Text("close to 0: the frequency-response estimate is unreliable", font_size=22, color=RED),
        ).arrange(DOWN, buff=0.16).to_edge(DOWN, 0.25)
        self.play(FadeIn(interpretation), run_time=TRANSITION_TIME)
        self.wait(LONG_WAIT)

        # Final clean overview.
        self.play(Transform(heading, self.title("Frequency-response estimation using Welch's method", INK)),
                  FadeOut(coh_formula), FadeOut(ax_coh), FadeOut(gc), FadeOut(freq_lab2), FadeOut(tick_labels2),
                  FadeOut(reliable), FadeOut(reliable_text), FadeOut(interpretation), run_time=TRANSITION_TIME)
        overview = VGroup(
            Text("1. Centre input and output signals", font_size=25, color=INK),
            Text("2. Divide both signals into identical overlapping segments", font_size=25, color=INK),
            Text("3. Apply the window and calculate both Fourier transforms", font_size=25, color=INK),
            Text("4. Form and average input power, cross spectrum and output power", font_size=25, color=INK),
            MathTex(r"5.\quad \widehat{G}=\widehat{S}_{yu}/\widehat{S}_{uu}", font_size=34, color=BLUE),
            MathTex(r"6.\quad \gamma^2=|\widehat{S}_{yu}|^2/(\widehat{S}_{uu}\widehat{S}_{yy})", font_size=34, color=PURPLE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to(ORIGIN).shift(DOWN * 0.15)
        self.play(LaggedStart(*[FadeIn(item, shift=RIGHT * 0.18) for item in overview], lag_ratio=0.13), run_time=DRAW_TIME * 1.5)
        self.wait(LONG_WAIT)
