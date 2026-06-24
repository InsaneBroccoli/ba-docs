"""Shared visual theme for the defense animations.

Importing this module sets a global default font for all Manim ``Text``
objects. We use URW Gothic, the freely-licensed, geometrically near-identical
clone of Avant Garde / Century Gothic that ships with gsfonts (installed system
wide). ``MathTex`` equations are intentionally left in the default LaTeX font.
"""

from manim import Text

FONT = "URW Gothic"  # free Avant Garde / Century-Gothic-style geometric sans

Text.set_default(font=FONT)
