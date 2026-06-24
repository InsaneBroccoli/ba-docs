from manim import *
import theme  # sets URW Gothic as the default Text font
import numpy as np
from PIL import Image
import os


def create_clean_drone_image():
    input_path = "drone.png"
    output_path = "drone_clean.png"

    if os.path.exists(output_path):
        return

    img = Image.open(input_path).convert("RGBA")
    pixels = img.load()

    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]

            # Remove white / light gray background
            if r > 185 and g > 185 and b > 185:
                pixels[x, y] = (255, 255, 255, 0)

    img.save(output_path)
class TitleDroneAnimation(Scene):
    def construct(self):
        create_clean_drone_image()

        self.camera.background_color = WHITE


        blue = "#16457A"
        light_blue = "#0065A8"
        gray = "#4b5563"

        subtitle = Text(
            "Bachelor's Thesis - System Engineering",
            font_size=28,
            color=gray,
        )

        title = Text(
            "Betaflight - Offline Controller Tuning",
            font_size=44,
            color=blue,
            weight=BOLD,
        )

        authors = Text(
            "Yuri Bianchi | Janick Dort | Dario Jurietti",
            font_size=27,
            color=light_blue,
        )

        date = Text(
            "26.06.2026",
            font_size=25,
            color=gray,
        )

        text_group = VGroup(subtitle, title, authors, date).arrange(
            DOWN,
            buff=0.35,
        )
        text_group.move_to(UP * 1.35)

        # Drone image
        drone = ImageMobject("drone_clean.png")
        drone.set_height(1.6)
        drone.set_z_index(5)

        progress = ValueTracker(0)

        def drone_path(alpha):
            # Drone flies from left to right in the lower area
            x = -7.8 + 15.6 * alpha
            y = -1.65 + 0.18 * np.sin(2 * np.pi * alpha * 2)
            return np.array([x, y, 0])

        drone.move_to(drone_path(0))

        def move_drone(mob):
            alpha = progress.get_value() % 1
            mob.move_to(drone_path(alpha))

            # Small realistic tilt
            angle = 0.04 * np.cos(2 * np.pi * alpha * 2)
            mob.set_rotation(angle)

        drone.add_updater(move_drone)

        # Optional subtle line below the title
        underline = Line(
            LEFT * 3.8,
            RIGHT * 3.8,
            color=light_blue,
            stroke_width=2,
        )
        underline.next_to(title, DOWN, buff=0.12)

        self.add(text_group)
        self.add(underline)
        self.add(drone)

        self.play(
            progress.animate.set_value(4),
            run_time=20,
            rate_func=linear,
        )

        self.wait(0.5)
