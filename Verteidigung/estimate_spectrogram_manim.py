from manim import *
import theme  # sets URW Gothic as the default Text font
import numpy as np


config.background_color = "#F6EEE1"
config.frame_width = 16
config.frame_height = 9


INK = "#111827"
MUTED = "#6B7280"
GRID = "#E5E7EB"
BLUE = "#2563EB"
LIGHT_BLUE = "#DBEAFE"
ORANGE = "#F97316"
GREEN = "#16A34A"
PURPLE = "#7C3AED"
RED = "#DC2626"
YELLOW = "#F59E0B"


class SpectrogramAnimationBase:
    def make_step_title(self, text, color=INK):
        return Text(text, font_size=34, color=color).to_edge(UP, buff=0.35)

    def graph_from_data(self, axes, x, y, color=BLUE, stroke_width=3):
        graph = VMobject(color=color, stroke_width=stroke_width)
        points = [axes.c2p(float(xi), float(yi)) for xi, yi in zip(x, y)]
        graph.set_points_as_corners(points)
        return graph

    def lollipop_spectrum(self, axes, freq, amp, color=PURPLE):
        spectrum = VGroup()
        max_amp = max(float(np.max(amp)), 1e-9)
        for f, a in zip(freq, amp):
            ratio = min(float(a) / max_amp, 1.0)
            opacity = 0.18 + 0.72 * ratio
            stroke_width = 1.0 + 3.0 * ratio
            stem = Line(
                axes.c2p(float(f), 0),
                axes.c2p(float(f), float(a)),
                color=color,
                stroke_width=stroke_width,
            )
            stem.set_opacity(opacity)
            dot = Dot(
                axes.c2p(float(f), float(a)),
                radius=0.018 + 0.035 * ratio,
                color=color,
                fill_opacity=opacity,
                stroke_width=0,
            )
            spectrum.add(stem, dot)
        return spectrum

    def heat_color(self, value):
        stops = ["#F8FAFC", "#BFDBFE", "#60A5FA", "#2563EB", "#1E3A8A"]
        value = float(np.clip(value, 0, 1))
        idx = min(int(round(value * (len(stops) - 1))), len(stops) - 1)
        return stops[idx]

    def heatmap(self, matrix, width=6.6, height=3.25, stroke_width=0.8):
        matrix = np.asarray(matrix, dtype=float)
        if np.max(matrix) > np.min(matrix):
            values = (matrix - np.min(matrix)) / (np.max(matrix) - np.min(matrix))
        else:
            values = np.zeros_like(matrix)

        rows, cols = values.shape
        cell_w = width / cols
        cell_h = height / rows
        cells = VGroup()
        for r in range(rows):
            for c in range(cols):
                cell = Rectangle(
                    width=cell_w,
                    height=cell_h,
                    stroke_color=WHITE,
                    stroke_width=stroke_width,
                    fill_color=self.heat_color(values[r, c]),
                    fill_opacity=1,
                )
                x = -width / 2 + cell_w / 2 + c * cell_w
                y = height / 2 - cell_h / 2 - r * cell_h
                cell.move_to([x, y, 0])
                cells.add(cell)
        return cells

    def example_data(self):
        rng = np.random.default_rng(7)
        fs = 80
        t = np.arange(0, 8, 1 / fs)

        # Thrust-like operating coordinate.
        y = 0.5 + 0.42 * np.sin(2 * np.pi * 0.12 * t - 0.4)
        y += 0.08 * np.sin(2 * np.pi * 0.31 * t + 0.7)
        y = np.clip(y, 0, 1)

        low_band = (1 - y)
        high_band = y
        signal = (
            (0.18 + 0.45 * low_band) * np.sin(2 * np.pi * 4.0 * t + 0.3)
            + (0.10 + 0.35 * high_band) * np.sin(2 * np.pi * 13.0 * t + 1.2)
            + 0.16 * np.sin(2 * np.pi * 8.0 * t + 0.4 * np.sin(2 * np.pi * 0.2 * t))
            + 0.08
            + 0.025 * rng.normal(size=t.size)
        )
        return fs, t, signal, y

    def compute_spectrogram(self, signal, y, fs, segment_length=96, overlap=72, y_bins=12, freq_limit=20):
        window = np.hanning(segment_length)
        step = segment_length - overlap
        starts = list(range(0, len(signal) - segment_length + 1, step))
        freqs = np.fft.rfftfreq(segment_length, d=1 / fs)
        keep = freqs <= freq_limit
        freqs = freqs[keep]

        y_min = float(np.min(y))
        y_max = float(np.max(y))
        heat = np.zeros((y_bins, len(freqs)))
        counts = np.zeros(y_bins)
        shown = []

        for start in starts:
            idx = slice(start, start + segment_length)
            segment = signal[idx]
            segment = segment - np.mean(segment)
            fourier_coefficients = np.fft.rfft(segment * window) / (np.sum(window) / 2)
            segment_power = np.abs(fourier_coefficients[keep]) ** 2
            segment_power[0] /= 4
            segment_power[-1] /= 4

            y_segment = y[idx]
            y_indices = np.round((y_segment - y_min) / max(y_max - y_min, 1e-9) * (y_bins - 1)).astype(int)
            y_indices = np.clip(y_indices, 0, y_bins - 1)
            unique, unique_counts = np.unique(y_indices, return_counts=True)

            for row, count in zip(unique, unique_counts):
                heat[row, :] += count * segment_power
                counts[row] += count

            shown.append((start, segment_power, unique, unique_counts))

        valid = counts > 0
        heat[valid, :] = heat[valid, :] / counts[valid, None]
        smooth = self.smooth2d(heat)
        y_axis = np.linspace(y_min, y_max, y_bins)
        return freqs, y_axis, heat, smooth, shown

    def smooth2d(self, matrix):
        kernel = np.array([[1, 3, 1], [3, 5, 3], [1, 3, 1]], dtype=float)
        kernel = kernel / np.sum(kernel)
        rows, cols = matrix.shape
        out = np.zeros_like(matrix)
        den = np.zeros_like(matrix)
        for r in range(rows):
            for c in range(cols):
                for kr in range(-1, 2):
                    for kc in range(-1, 2):
                        rr = r + kr
                        cc = c + kc
                        if 0 <= rr < rows and 0 <= cc < cols:
                            w = kernel[kr + 1, kc + 1]
                            out[r, c] += w * matrix[rr, cc]
                            den[r, c] += w
        return out / np.maximum(den, 1e-12)


class EstimateSpectrogramPart1(Scene, SpectrogramAnimationBase):
    def construct(self):
        fs, t, signal, y = self.example_data()
        freqs, y_axis, heat, smooth_heat, shown = self.compute_spectrogram(signal, y, fs)

        FAST_TIME = 1.2
        TRANSITION_TIME = 2.0
        DRAW_TIME = 3.0
        SLOW_DRAW_TIME = 4.0
        WAIT_TIME = 1.2
        LONG_WAIT = 3.5

        step_title = self.make_step_title("Step 1: Define bins along thrust", BLUE)

        signal_axes = Axes(
            x_range=[0, 8, 2],
            y_range=[-0.9, 0.95, 0.5],
            x_length=6.1,
            y_length=2.25,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).to_edge(LEFT, buff=0.75).shift(UP * 0.55)
        signal_label = Text("Input signal", font_size=22, color=INK).next_to(signal_axes, UP, buff=0.12)
        signal_graph = self.graph_from_data(signal_axes, t, signal, BLUE, 2.7)

        y_axes = Axes(
            x_range=[0, 8, 2],
            y_range=[0, 1, 0.25],
            x_length=6.1,
            y_length=2.25,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).to_edge(RIGHT, buff=0.75).shift(UP * 0.55)
        y_label = Text("Thrust", font_size=22, color=INK).next_to(y_axes, UP, buff=0.12)
        y_graph = self.graph_from_data(y_axes, t, y, ORANGE, 2.7)

        self.play(
            FadeIn(step_title, shift=DOWN * 0.15),
            FadeIn(signal_axes),
            FadeIn(signal_label),
            FadeIn(y_axes),
            FadeIn(y_label),
            run_time=FAST_TIME,
        )
        self.play(Create(signal_graph), Create(y_graph), run_time=SLOW_DRAW_TIME)

        y_bin_lines = VGroup()
        for y_value in np.linspace(0, 1, 7):
            line = DashedLine(
                y_axes.c2p(0, y_value),
                y_axes.c2p(8, y_value),
                color=GREEN,
                stroke_width=1.6,
                dash_length=0.12,
            )
            y_bin_lines.add(line)
        bottom_text = Text("Thrust is split into spectrogram rows", font_size=22, color=INK)
        bottom_text.to_edge(DOWN, buff=0.65)
        self.play(Create(y_bin_lines), FadeIn(bottom_text), run_time=TRANSITION_TIME)
        self.wait(WAIT_TIME)

        segment_length = 96
        starts = [shown[6][0], shown[7][0], shown[8][0]]
        segment_rects = VGroup()
        for start, color in zip(starts, [PURPLE, GREEN, ORANGE]):
            t0 = t[start]
            t1 = t[start + segment_length - 1]
            left = signal_axes.c2p(t0, -0.82)
            right = signal_axes.c2p(t1, 0.88)
            rect = Rectangle(
                width=right[0] - left[0],
                height=right[1] - left[1],
                stroke_color=color,
                stroke_width=3,
                fill_color=color,
                fill_opacity=0.08,
            )
            rect.move_to((left + right) / 2)
            segment_rects.add(rect)

        self.play(
            Transform(step_title, self.make_step_title("Step 2: Segment the signal and apply the window", ORANGE)),
            Transform(bottom_text, Text("Overlapping segments are analysed one by one", font_size=22, color=INK).to_edge(DOWN, buff=0.65)),
            run_time=TRANSITION_TIME,
        )
        self.play(LaggedStart(*[Create(rect) for rect in segment_rects], lag_ratio=0.25), run_time=SLOW_DRAW_TIME)

        spectrum_axes = Axes(
            x_range=[0, 20, 5],
            y_range=[0, 0.45, 0.15],
            x_length=4.8,
            y_length=1.6,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).move_to(ORIGIN).shift(DOWN * 2.2)
        spectrum_label = Text("Single-sided power spectrum", font_size=19, color=INK).next_to(
            spectrum_axes, UP, buff=0.08
        )

        # This is the green segment retained above. The same segment is used at
        # the beginning of Part 2 so that the transition is unambiguous.
        chosen = shown[7]
        segment_power = chosen[1]
        spectrum_graph = self.lollipop_spectrum(spectrum_axes, freqs, segment_power, PURPLE)
        spectrum_text = Text("Each segment becomes one spectrum", font_size=22, color=PURPLE)
        spectrum_text.to_edge(DOWN, buff=0.65)

        self.play(
            Transform(step_title, self.make_step_title("Step 3: Compute a single-sided power spectrum", PURPLE)),
            FadeOut(segment_rects[0]),
            FadeOut(segment_rects[2]),
            FadeIn(spectrum_axes),
            FadeIn(spectrum_label),
            run_time=TRANSITION_TIME,
        )
        self.play(FadeIn(spectrum_graph), Transform(bottom_text, spectrum_text), run_time=DRAW_TIME)
        self.wait(LONG_WAIT)


class EstimateSpectrogramPart2(Scene, SpectrogramAnimationBase):
    def construct(self):
        fs, t, signal, y = self.example_data()
        freqs, y_axis, heat, smooth_heat, shown = self.compute_spectrogram(signal, y, fs)

        FAST_TIME = 1.2
        TRANSITION_TIME = 2.0
        DRAW_TIME = 3.0
        SLOW_DRAW_TIME = 4.0
        WAIT_TIME = 1.2
        LONG_WAIT = 3.5

        segment_length = 96
        chosen = shown[7]
        segment_start = chosen[0]
        segment_power = chosen[1]
        touched_rows = chosen[2]
        row_counts = chosen[3]

        # A less similar segment is chosen for the second demonstration. It
        # overlaps two rows from segment 1 and also reaches one new row.
        second = shown[4]
        second_start = second[0]
        second_power = second[1]
        second_rows = second[2]
        second_counts = second[3]

        def averaged_result_for_segments(segments):
            accumulated = np.zeros_like(heat)
            sample_count = np.zeros(heat.shape[0])
            for _, power, rows, counts in segments:
                for row, count in zip(rows, counts):
                    accumulated[int(row), :] += int(count) * power
                    sample_count[int(row)] += int(count)
            valid = sample_count > 0
            accumulated[valid, :] /= sample_count[valid, None]
            return accumulated

        heat_after_first = averaged_result_for_segments([chosen])
        heat_after_two = averaged_result_for_segments([chosen, second])

        # ------------------------------------------------------------------
        # Step 4: map all thrust samples from one segment to spectrogram rows.
        # ------------------------------------------------------------------
        step_title = self.make_step_title(
            "Step 4: Assign the segment spectrum to its thrust rows", GREEN
        )

        # An empty grid makes the assignment visible before the completed
        # averaged spectrogram is shown. Flip the matrix for display so that
        # larger thrust values appear at the top.
        empty_heatmap = self.heatmap(np.zeros_like(heat), width=6.7, height=3.75)
        empty_heatmap.to_edge(LEFT, buff=0.75).shift(DOWN * 0.10)
        heatmap_title = Text("Spectrogram rows", font_size=24, color=INK).next_to(
            empty_heatmap, UP, buff=0.18
        )
        x_label = Text("frequency", font_size=18, color=INK).next_to(
            empty_heatmap, DOWN, buff=0.18
        )
        y_heat_label = Text("thrust", font_size=18, color=INK).rotate(PI / 2).next_to(
            empty_heatmap, LEFT, buff=0.18
        )

        segment_indices = np.arange(segment_start, segment_start + segment_length)
        segment_time = t[segment_indices] - t[segment_start]
        segment_thrust = y[segment_indices]
        y_min = float(np.min(y))
        y_max = float(np.max(y))
        sample_rows = np.round(
            (segment_thrust - y_min) / max(y_max - y_min, 1e-9) * (heat.shape[0] - 1)
        ).astype(int)
        sample_rows = np.clip(sample_rows, 0, heat.shape[0] - 1)

        segment_duration = float(segment_time[-1])
        thrust_axes_small = Axes(
            x_range=[0, segment_duration, 0.4],
            y_range=[0, 1, 0.25],
            x_length=4.6,
            y_length=1.75,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).to_edge(RIGHT, buff=0.75).shift(UP * 1.15)
        thrust_label_small = Text("Thrust samples in the selected segment", font_size=20, color=INK).next_to(
            thrust_axes_small, UP, buff=0.12
        )
        thrust_graph_small = self.graph_from_data(
            thrust_axes_small, segment_time, segment_thrust, ORANGE, 2.5
        )

        # Three colours are sufficient for the selected example segment, which
        # touches three neighbouring thrust rows.
        assignment_colors = [GREEN, PURPLE, YELLOW, RED, BLUE]
        demonstration_rows = sorted(
            set(int(row) for row in touched_rows)
            | set(int(row) for row in second_rows)
        )
        row_color = {
            row: assignment_colors[i % len(assignment_colors)]
            for i, row in enumerate(demonstration_rows)
        }

        sample_dots = VGroup()
        # Display every fourth sample to keep the plot readable. Counts below
        # still use every sample, exactly as in the MATLAB implementation.
        for local_index in range(0, segment_length, 4):
            row = int(sample_rows[local_index])
            sample_dots.add(
                Dot(
                    thrust_axes_small.c2p(
                        segment_time[local_index], segment_thrust[local_index]
                    ),
                    radius=0.035,
                    color=row_color.get(row, MUTED),
                )
            )

        row_height = 3.75 / heat.shape[0]
        row_markers = VGroup()
        row_tokens = VGroup()
        representative_dots = VGroup()
        assignment_arrows = VGroup()

        for row, count in zip(touched_rows, row_counts):
            display_row = heat.shape[0] - 1 - int(row)
            row_y = empty_heatmap.get_top()[1] - (display_row + 0.5) * row_height
            color = row_color[int(row)]
            marker = Rectangle(
                width=6.75,
                height=row_height,
                stroke_color=color,
                stroke_width=2.6,
                fill_color=color,
                fill_opacity=0.10,
            ).move_to([empty_heatmap.get_center()[0], row_y, 0])
            token = Text(
                f"same spectrum × {int(count)} samples",
                font_size=13,
                color=color,
            ).move_to(marker)

            indices_in_row = np.where(sample_rows == row)[0]
            representative_index = int(indices_in_row[len(indices_in_row) // 2])
            dot = Dot(
                thrust_axes_small.c2p(
                    segment_time[representative_index],
                    segment_thrust[representative_index],
                ),
                radius=0.065,
                color=color,
            )
            arrow = Arrow(
                dot.get_center(),
                marker.get_right(),
                buff=0.12,
                color=color,
                stroke_width=2.8,
                max_tip_length_to_length_ratio=0.08,
            )
            row_markers.add(marker)
            row_tokens.add(token)
            representative_dots.add(dot)
            assignment_arrows.add(arrow)

        spectrum_axes = Axes(
            x_range=[0, 20, 5],
            y_range=[0, 0.45, 0.15],
            x_length=4.6,
            y_length=1.15,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 1.8},
        ).to_edge(RIGHT, buff=0.75).shift(DOWN * 1.65)
        spectrum_label = Text("Spectrum of the selected segment", font_size=19, color=PURPLE).next_to(
            spectrum_axes, UP, buff=0.08
        )
        spectrum_graph = self.lollipop_spectrum(
            spectrum_axes, freqs, segment_power, PURPLE
        )

        # Prepare a second segment. It touches the same three rows but carries
        # a different spectrum and different sample counts, which makes the
        # weighted averaging visible.
        second_indices = np.arange(second_start, second_start + segment_length)
        second_time = t[second_indices] - t[second_start]
        second_thrust = y[second_indices]
        second_sample_rows = np.round(
            (second_thrust - y_min) / max(y_max - y_min, 1e-9) * (heat.shape[0] - 1)
        ).astype(int)
        second_sample_rows = np.clip(second_sample_rows, 0, heat.shape[0] - 1)

        second_thrust_graph = self.graph_from_data(
            thrust_axes_small, second_time, second_thrust, ORANGE, 2.5
        )
        second_thrust_label = Text(
            "Thrust samples in segment 2", font_size=20, color=INK
        ).move_to(thrust_label_small)
        second_spectrum_graph = self.lollipop_spectrum(
            spectrum_axes, freqs, second_power, RED
        )
        second_spectrum_label = Text(
            "Spectrum of segment 2", font_size=19, color=RED
        ).move_to(spectrum_label)

        second_sample_dots = VGroup()
        for local_index in range(0, segment_length, 4):
            row = int(second_sample_rows[local_index])
            second_sample_dots.add(
                Dot(
                    thrust_axes_small.c2p(
                        second_time[local_index], second_thrust[local_index]
                    ),
                    radius=0.035,
                    color=row_color.get(row, MUTED),
                )
            )

        second_row_markers = VGroup()
        second_row_tokens = VGroup()
        second_representative_dots = VGroup()
        second_assignment_arrows = VGroup()
        for row, count in zip(second_rows, second_counts):
            display_row = heat.shape[0] - 1 - int(row)
            row_y = empty_heatmap.get_top()[1] - (display_row + 0.5) * row_height
            color = row_color[int(row)]
            marker = Rectangle(
                width=6.75,
                height=row_height,
                stroke_color=color,
                stroke_width=2.6,
                fill_color=color,
                fill_opacity=0.10,
            ).move_to([empty_heatmap.get_center()[0], row_y, 0])
            token = Text(
                f"segment 2 spectrum × {int(count)} samples",
                font_size=13,
                color=color,
            ).move_to(marker)

            indices_in_row = np.where(second_sample_rows == row)[0]
            representative_index = int(indices_in_row[len(indices_in_row) // 2])
            dot = Dot(
                thrust_axes_small.c2p(
                    second_time[representative_index],
                    second_thrust[representative_index],
                ),
                radius=0.065,
                color=color,
            )
            arrow = Arrow(
                dot.get_center(),
                marker.get_right(),
                buff=0.12,
                color=color,
                stroke_width=2.8,
                max_tip_length_to_length_ratio=0.08,
            )
            second_row_markers.add(marker)
            second_row_tokens.add(token)
            second_representative_dots.add(dot)
            second_assignment_arrows.add(arrow)

        heatmap_group = VGroup(empty_heatmap, heatmap_title, x_label, y_heat_label)
        bottom_text = Text(
            "Every thrust sample assigns the same segment spectrum to its row",
            font_size=21,
            color=GREEN,
        )
        bottom_text.to_edge(DOWN, buff=0.65)

        self.play(
            FadeIn(step_title, shift=DOWN * 0.15),
            FadeIn(empty_heatmap),
            FadeIn(heatmap_title),
            FadeIn(x_label),
            FadeIn(y_heat_label),
            FadeIn(thrust_axes_small),
            FadeIn(thrust_label_small),
            FadeIn(thrust_graph_small),
            run_time=FAST_TIME,
        )
        self.play(FadeIn(sample_dots), run_time=DRAW_TIME)
        self.play(
            FadeIn(spectrum_axes), FadeIn(spectrum_label), FadeIn(spectrum_graph),
            run_time=TRANSITION_TIME,
        )
        self.play(
            LaggedStart(
                *[
                    AnimationGroup(
                        FadeIn(representative_dots[i]),
                        Create(assignment_arrows[i]),
                        FadeIn(row_markers[i]),
                        FadeIn(row_tokens[i]),
                    )
                    for i in range(len(row_markers))
                ],
                lag_ratio=0.28,
            ),
            FadeIn(bottom_text),
            run_time=SLOW_DRAW_TIME,
        )
        self.wait(LONG_WAIT)

        # First intermediate result: after row-wise division, all three rows
        # contain exactly the same spectrum because only one segment has
        # contributed so far.
        first_result_heatmap = self.heatmap(
            heat_after_first[::-1, :], width=6.7, height=3.75
        ).move_to(empty_heatmap)
        first_result_title = Text(
            "Intermediate result after segment 1", font_size=24, color=PURPLE
        ).move_to(heatmap_title)
        first_result_text = Text(
            "After division by the sample counts, the three rows are identical",
            font_size=21,
            color=PURPLE,
        ).to_edge(DOWN, buff=0.65)

        self.play(
            Transform(
                step_title,
                self.make_step_title(
                    "Step 4: Intermediate spectrogram after segment 1", PURPLE
                ),
            ),
            FadeOut(sample_dots),
            FadeOut(representative_dots),
            FadeOut(assignment_arrows),
            FadeOut(row_markers),
            FadeOut(row_tokens),
            Transform(empty_heatmap, first_result_heatmap),
            Transform(heatmap_title, first_result_title),
            Transform(bottom_text, first_result_text),
            run_time=SLOW_DRAW_TIME,
        )
        self.wait(LONG_WAIT)

        # Repeat the same assignment with a second segment.
        self.play(
            Transform(
                step_title,
                self.make_step_title(
                    "Step 4: Repeat the assignment for segment 2", GREEN
                ),
            ),
            Transform(thrust_graph_small, second_thrust_graph),
            Transform(thrust_label_small, second_thrust_label),
            Transform(spectrum_graph, second_spectrum_graph),
            Transform(spectrum_label, second_spectrum_label),
            FadeIn(second_sample_dots),
            Transform(
                bottom_text,
                Text(
                    "Segment 2 contributes a different spectrum with different weights",
                    font_size=21,
                    color=GREEN,
                ).to_edge(DOWN, buff=0.65),
            ),
            run_time=TRANSITION_TIME,
        )
        self.play(
            LaggedStart(
                *[
                    AnimationGroup(
                        FadeIn(second_representative_dots[i]),
                        Create(second_assignment_arrows[i]),
                        FadeIn(second_row_markers[i]),
                        FadeIn(second_row_tokens[i]),
                    )
                    for i in range(len(second_row_markers))
                ],
                lag_ratio=0.28,
            ),
            run_time=SLOW_DRAW_TIME,
        )
        self.wait(LONG_WAIT)

        # Second intermediate result: the rows are now different weighted
        # averages of the first and second segment spectra.
        second_result_heatmap = self.heatmap(
            heat_after_two[::-1, :], width=6.7, height=3.75
        ).move_to(empty_heatmap)
        second_result_title = Text(
            "Intermediate result after two segments", font_size=24, color=GREEN
        ).move_to(heatmap_title)
        second_result_text = Text(
            "Different sample weights now produce different row averages",
            font_size=21,
            color=GREEN,
        ).to_edge(DOWN, buff=0.65)

        self.play(
            FadeOut(second_sample_dots),
            FadeOut(second_representative_dots),
            FadeOut(second_assignment_arrows),
            FadeOut(second_row_markers),
            FadeOut(second_row_tokens),
            Transform(empty_heatmap, second_result_heatmap),
            Transform(heatmap_title, second_result_title),
            Transform(bottom_text, second_result_text),
            run_time=SLOW_DRAW_TIME,
        )
        self.wait(LONG_WAIT)

        # ------------------------------------------------------------------
        # Step 5: accumulate all segment spectra and divide each row by its
        # number of assigned thrust samples.
        # ------------------------------------------------------------------
        raw_heatmap = self.heatmap(heat[::-1, :], width=6.7, height=3.75)
        centre_shift = ORIGIN + DOWN * 0.05 - heatmap_group.get_center()
        raw_heatmap.move_to(empty_heatmap.get_center() + centre_shift)
        completed_title = Text("Averaged power spectrogram", font_size=24, color=INK)
        completed_title.move_to(heatmap_title.get_center() + centre_shift)
        centred_x_label = x_label.copy().shift(centre_shift)
        centred_y_label = y_heat_label.copy().shift(centre_shift)

        self.play(
            Transform(
                step_title,
                self.make_step_title(
                    "Step 5: Accumulate and average spectra inside each thrust row",
                    GREEN,
                ),
            ),
            FadeOut(thrust_axes_small),
            FadeOut(thrust_label_small),
            FadeOut(thrust_graph_small),
            FadeOut(sample_dots),
            FadeOut(representative_dots),
            FadeOut(assignment_arrows),
            FadeOut(row_markers),
            FadeOut(row_tokens),
            FadeOut(spectrum_axes),
            FadeOut(spectrum_label),
            FadeOut(spectrum_graph),
            Transform(empty_heatmap, raw_heatmap),
            Transform(heatmap_title, completed_title),
            Transform(x_label, centred_x_label),
            Transform(y_heat_label, centred_y_label),
            Transform(
                bottom_text,
                Text(
                    "Each accumulated row is divided by its number of assigned samples",
                    font_size=22,
                    color=GREEN,
                ).to_edge(DOWN, buff=0.65),
            ),
            run_time=TRANSITION_TIME,
        )
        self.wait(LONG_WAIT)

        smooth_heatmap = self.heatmap(smooth_heat[::-1, :], width=6.7, height=3.75)
        smooth_heatmap.move_to(empty_heatmap)
        smooth_title = Text("Smoothed power spectrogram", font_size=24, color=INK)
        smooth_title.move_to(heatmap_title)
        smooth_text = Text("Weighted 3×3 smoothing reduces isolated cells", font_size=22, color=BLUE)
        smooth_text.to_edge(DOWN, buff=0.65)

        self.play(
            Transform(step_title, self.make_step_title("Step 6: Smooth the spectrogram", BLUE)),
            Transform(empty_heatmap, smooth_heatmap),
            Transform(heatmap_title, smooth_title),
            Transform(bottom_text, smooth_text),
            run_time=SLOW_DRAW_TIME,
        )
        self.wait(LONG_WAIT)

        final = VGroup(
            Text("Algorithm overview", font_size=30, color=INK),
            Text("1. Split thrust into spectrogram rows", font_size=23, color=INK),
            Text("2. Segment the input signal with overlap and apply the window", font_size=22, color=INK),
            Text("3. Compute a single-sided power spectrum for each segment", font_size=22, color=INK),
            Text("4. Assign each spectrum to rows using all thrust samples", font_size=22, color=INK),
            Text("5. Accumulate and average the spectra inside each thrust row", font_size=22, color=INK),
            Text("6. Smooth the resulting spectrogram", font_size=22, color=INK),
            Text("Amplitude spectrogram = √(power spectrogram)", font_size=24, color=BLUE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        final.move_to(ORIGIN).shift(DOWN * 0.1)

        self.play(
            Transform(step_title, self.make_step_title("Overview: Welch spectrogram estimation", INK)),
            FadeOut(empty_heatmap),
            FadeOut(heatmap_title),
            FadeOut(x_label),
            FadeOut(y_heat_label),
            FadeOut(bottom_text),
            FadeIn(final, shift=RIGHT * 0.2),
            run_time=TRANSITION_TIME,
        )
        self.wait(LONG_WAIT)


class EstimateSpectrogram(EstimateSpectrogramPart1):
    pass
