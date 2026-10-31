"""About + scanning tips."""
from __future__ import annotations

import customtkinter as ctk

from ..config import APP_NAME, APP_TAGLINE, APP_VERSION, DB_PATH
from . import theme
from .widgets import GlassCard, section_label

TIPS = (
    "Keep a dark code on a light background — it's the most reliably scannable combo.",
    "Aim for a contrast ratio above 5:1 between foreground and background.",
    "Keep logos at or below ~25% so the code stays readable (logos force the highest error correction).",
    "Leave the quiet zone (margin) at 4 modules or more for best results.",
    "Use Ultra quality for print — PNGs export crisp at any size.",
    "Always test-scan with your phone before printing a big batch.",
)


class AboutView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        ctk.CTkLabel(self, text="About", font=theme.font(28, "bold"), text_color=theme.TEXT,
                     anchor="w").pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(self, text=f"{APP_NAME} — {APP_TAGLINE}  ·  v{APP_VERSION}", font=theme.font(13),
                     text_color=theme.MUTED, anchor="w").pack(fill="x", pady=(0, 14))

        card = GlassCard(self, "Tips for QR codes that scan every time")
        card.pack(fill="x")
        for tip in TIPS:
            ctk.CTkLabel(card.body, text=f"•  {tip}", font=theme.font(13), text_color=theme.TEXT,
                         anchor="w", justify="left", wraplength=760).pack(fill="x", pady=3)

        data = GlassCard(self, "Your data")
        data.pack(fill="x", pady=(14, 0))
        section_label(data.body, "History database").pack(fill="x")
        ctk.CTkLabel(data.body, text=str(DB_PATH), font=theme.font(12), text_color=theme.MUTED,
                     anchor="w", justify="left", wraplength=760).pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(data.body, text="Everything stays on this computer — nothing is uploaded.",
                     font=theme.font(12), text_color=theme.FAINT, anchor="w").pack(fill="x", pady=(8, 0))
