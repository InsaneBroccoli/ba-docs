from manim import *

# ==========================================
# Global style
# ==========================================
config.background_color = "#F6EEE1"

INK = "#6B584C"
BLUE = "#2563EB"
GREEN = "#16A34A"
RED = "#DC2626"
GRAY = "#8A817C"


class ClosedLoopIdentification(Scene):
    def make_sum_pm(self):
        """Summing junction with + and -"""
        c = Circle(radius=0.23, stroke_color=INK, stroke_width=2)
        plus = MathTex("+", color=INK, font_size=28).move_to(c.get_center() + LEFT * 0.08 + UP * 0.04)
        minus = MathTex("-", color=INK, font_size=30).move_to(c.get_center() + DOWN * 0.10)
        return VGroup(c, plus, minus)

    def make_sum_pp(self):
        """Summing junction with + and +"""
        c = Circle(radius=0.23, stroke_color=INK, stroke_width=2)
        plus1 = MathTex("+", color=INK, font_size=24).move_to(c.get_center() + LEFT * 0.08 + UP * 0.04)
        plus2 = MathTex("+", color=INK, font_size=24).move_to(c.get_center() + UP * 0.12)
        return VGroup(c, plus1, plus2)

    def block(self, label, width=2.2, height=1.0):
        rect = Rectangle(width=width, height=height, stroke_color=INK, stroke_width=2)
        txt = Text(label, color=INK, font_size=28)
        txt.move_to(rect.get_center())
        return VGroup(rect, txt)

    def arrow_between(self, mob1, mob2):
        return Arrow(
            mob1.get_right(),
            mob2.get_left(),
            buff=0.03,
            stroke_width=3,
            color=INK,
            max_tip_length_to_length_ratio=0.15
        )

    def construct(self):
        # ==========================================
        # Title
        # ==========================================
        title = Text(
            "Closed-Loop Identification Principle",
            color=INK,
            font_size=34
        ).to_edge(UP, buff=0.35)

        self.play(Write(title))
        self.wait(0.3)

        # ==========================================
        # Main diagram elements
        # ==========================================
        sum1 = self.make_sum_pm().move_to(LEFT * 5.0 + UP * 0.2)
        ctrl = self.block("C").move_to(LEFT * 2.7 + UP * 0.2)
        sum2 = self.make_sum_pp().move_to(LEFT * 0.2 + UP * 0.2)
        plant = self.block("P").move_to(RIGHT * 2.2 + UP * 0.2)
        sum3 = self.make_sum_pp().move_to(RIGHT * 4.8 + UP * 0.2)

        # Reference input
        r_arrow = Arrow(
            sum1.get_left() + LEFT * 1.3,
            sum1.get_left(),
            buff=0,
            stroke_width=3,
            color=INK,
            max_tip_length_to_length_ratio=0.15
        )
        r_label = MathTex("r", color=INK, font_size=34).next_to(r_arrow, UP, buff=0.05)

        # Internal arrows
        e_arrow = self.arrow_between(sum1, ctrl)
        u_arrow = self.arrow_between(ctrl, sum2)
        p_arrow = self.arrow_between(sum2, plant)
        yline_arrow = self.arrow_between(plant, sum3)

        y_arrow = Arrow(
            sum3.get_right(),
            sum3.get_right() + RIGHT * 1.1,
            buff=0.03,
            stroke_width=3,
            color=INK,
            max_tip_length_to_length_ratio=0.15
        )
        y_label = MathTex("y", color=INK, font_size=34).next_to(y_arrow, UP, buff=0.05)

        # Signal labels
        e_label = MathTex("e", color=INK, font_size=32).next_to(e_arrow, UP, buff=0.03)
        u_label = MathTex("u", color=INK, font_size=32).next_to(u_arrow, UP, buff=0.03)

        # Disturbances
        din_arrow = Arrow(
            sum2.get_top() + UP * 1.1,
            sum2.get_top(),
            buff=0.03,
            stroke_width=3,
            color=INK,
            max_tip_length_to_length_ratio=0.15
        )
        din_label = Text("Input\nDisturbance", color=INK, font_size=22, line_spacing=0.8)
        din_label.next_to(din_arrow, UP, buff=0.08)

        dout_arrow = Arrow(
            sum3.get_top() + UP * 1.1,
            sum3.get_top(),
            buff=0.03,
            stroke_width=3,
            color=INK,
            max_tip_length_to_length_ratio=0.15
        )
        dout_label = Text("Output\nDisturbance", color=INK, font_size=22, line_spacing=0.8)
        dout_label.next_to(dout_arrow, UP, buff=0.08)

        # Feedback path
        feedback_dot = Dot(sum3.get_right() + RIGHT * 0.12, radius=0.06, color=INK)
        fb_down = Line(feedback_dot.get_center(), feedback_dot.get_center() + DOWN * 1.7, color=INK, stroke_width=2.5)
        fb_left = Line(fb_down.get_end(), sum1.get_bottom() + DOWN * 1.7, color=INK, stroke_width=2.5)
        fb_up = Arrow(
            fb_left.get_end(),
            sum1.get_bottom(),
            buff=0.03,
            stroke_width=2.5,
            color=INK,
            max_tip_length_to_length_ratio=0.15
        )

        diagram = VGroup(
            sum1, ctrl, sum2, plant, sum3,
            r_arrow, r_label,
            e_arrow, e_label,
            u_arrow, u_label,
            p_arrow, yline_arrow, y_arrow, y_label,
            din_arrow, din_label,
            dout_arrow, dout_label,
            feedback_dot, fb_down, fb_left, fb_up
        )

        # ==========================================
        # Animate build-up of diagram
        # ==========================================
        self.play(FadeIn(sum1), GrowArrow(r_arrow), FadeIn(r_label))
        self.wait(0.2)

        self.play(GrowArrow(e_arrow), FadeIn(e_label), FadeIn(ctrl))
        self.wait(0.2)

        self.play(GrowArrow(u_arrow), FadeIn(u_label), FadeIn(sum2))
        self.play(GrowArrow(din_arrow), FadeIn(din_label))
        self.wait(0.2)

        self.play(GrowArrow(p_arrow), FadeIn(plant))
        self.wait(0.2)

        self.play(FadeIn(sum3), GrowArrow(yline_arrow), GrowArrow(y_arrow), FadeIn(y_label))
        self.play(GrowArrow(dout_arrow), FadeIn(dout_label))
        self.wait(0.2)

        self.play(FadeIn(feedback_dot), Create(fb_down), Create(fb_left), GrowArrow(fb_up))
        self.wait(0.5)

        # Small highlight
        loop_box = SurroundingRectangle(
            VGroup(sum1, ctrl, sum2, plant, sum3),
            color=BLUE,
            buff=0.25,
            stroke_width=2
        )
        self.play(Create(loop_box))
        self.wait(0.4)
        self.play(FadeOut(loop_box))

        # ==========================================
        # Move diagram upward
        # ==========================================
        self.play(diagram.animate.scale(0.88).shift(UP * 1.2))
        self.wait(0.3)

        # ==========================================
        # Equations
        # ==========================================
        eq1 = MathTex(
            r"G_{yr}(\omega)=\frac{Y(\omega)}{R(\omega)}"
            r"=\frac{C(\omega)P(\omega)}{1+C(\omega)P(\omega)}"
            r"=T(\omega)",
            color=INK,
            font_size=30
        ).next_to(diagram, DOWN, buff=0.55)

        eq2 = MathTex(
            r"G_{ur}(\omega)=\frac{U(\omega)}{R(\omega)}"
            r"=\frac{C(\omega)}{1+C(\omega)P(\omega)}"
            r"=S(\omega)C(\omega)",
            color=INK,
            font_size=30
        ).next_to(eq1, DOWN, aligned_edge=LEFT, buff=0.30)

        eq3 = MathTex(
            r"P(\omega)=\frac{G_{yr}(\omega)}{G_{ur}(\omega)}",
            color=GREEN,
            font_size=34
        ).next_to(eq2, DOWN, aligned_edge=LEFT, buff=0.42)

        eq4 = MathTex(
            r"C(\omega)=\frac{G_{ur}(\omega)}{1-G_{yr}(\omega)}",
            color=RED,
            font_size=34
        ).next_to(eq3, RIGHT, buff=1.0)

        self.play(Write(eq1))
        self.wait(0.5)

        self.play(Write(eq2))
        self.wait(0.6)

        self.play(Write(eq3))
        self.play(Write(eq4))
        self.wait(1.5)