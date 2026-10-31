"""UI widgets."""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import colorchooser

import customtkinter as ctk

from . import theme

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


# Style helpers
def make_entry(master, **kw) -> ctk.CTkEntry:
    opts = dict(
        height=38, corner_radius=10, fg_color=theme.INPUT, border_color=theme.BORDER,
        border_width=1, text_color=theme.TEXT, placeholder_text_color=theme.FAINT,
        font=theme.font(13),
    )
    opts.update(kw)
    return ctk.CTkEntry(master, **opts)


def primary_button(master, text, command, **kw) -> ctk.CTkButton:
    opts = dict(
        text=text, command=command, height=42, corner_radius=12, fg_color=theme.ACCENT,
        hover_color=theme.ACCENT_HOVER, text_color="#FFFFFF", font=theme.font(13, "bold"),
    )
    opts.update(kw)
    return ctk.CTkButton(master, **opts)


def ghost_button(master, text, command, **kw) -> ctk.CTkButton:
    opts = dict(
        text=text, command=command, height=42, corner_radius=12, fg_color=theme.CARD_HI,
        hover_color=theme.CARD_HI, border_width=1, border_color=theme.BORDER,
        text_color=theme.TEXT, font=theme.font(13, "bold"),
    )
    opts.update(kw)
    return ctk.CTkButton(master, **opts)


def danger_button(master, text, command, **kw) -> ctk.CTkButton:
    opts = dict(
        text=text, command=command, height=36, corner_radius=10, fg_color="transparent",
        hover_color=theme.DANGER_SOFT, border_width=1, border_color=theme.DANGER,
        text_color=theme.DANGER, font=theme.font(12, "bold"),
    )
    opts.update(kw)
    return ctk.CTkButton(master, **opts)


def segmented(master, values, command=None, **kw) -> ctk.CTkSegmentedButton:
    opts = dict(
        values=list(values), command=command, height=36, corner_radius=12,
        fg_color=theme.INPUT, selected_color=theme.ACCENT, selected_hover_color=theme.ACCENT_HOVER,
        unselected_color=theme.INPUT, unselected_hover_color=theme.CARD_HI,
        text_color=theme.TEXT, font=theme.font(12, "bold"), border_width=3,
    )
    opts.update(kw)
    return ctk.CTkSegmentedButton(master, **opts)


def slider(master, from_, to, steps, command, **kw) -> ctk.CTkSlider:
    opts = dict(
        from_=from_, to=to, number_of_steps=steps, command=command, height=18,
        fg_color=theme.INPUT, progress_color=theme.ACCENT, button_color=theme.BLUE,
        button_hover_color=theme.VIOLET,
    )
    opts.update(kw)
    return ctk.CTkSlider(master, **opts)


def section_label(master, text) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=text.upper(), font=theme.font(11, "bold"),
                        text_color=theme.FAINT, anchor="w")


# Glass card
class GlassCard(ctk.CTkFrame):
    """Layered glass card."""

    def __init__(self, master, title=None, subtitle=None, fg=None, width=None, **kw):
        super().__init__(master, fg_color=theme.SHADOW, corner_radius=22, **kw)
        if width:
            self.configure(width=width)
            self.pack_propagate(False)
        self.card = ctk.CTkFrame(
            self, fg_color=fg or theme.CARD, corner_radius=20,
            border_width=1, border_color=theme.BORDER,
        )
        self.card.pack(fill="both", expand=True, padx=(0, 3), pady=(0, 5))
        self.body = ctk.CTkFrame(self.card, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=18)
        if title:
            ctk.CTkLabel(self.body, text=title, font=theme.font(16, "bold"),
                         text_color=theme.TEXT, anchor="w").pack(fill="x")
            if subtitle:
                ctk.CTkLabel(self.body, text=subtitle, font=theme.font(12),
                             text_color=theme.MUTED, anchor="w").pack(fill="x", pady=(0, 12))
            else:
                ctk.CTkFrame(self.body, height=8, fg_color="transparent").pack()


# Color field
class ColorField(ctk.CTkFrame):
    """Color swatch and hex entry."""

    def __init__(self, master, label: str, color: str, command):
        super().__init__(master, fg_color="transparent")
        self._command, self._color, self._silent = command, color, False

        ctk.CTkLabel(self, text=label, font=theme.font(12, "bold"),
                     text_color=theme.MUTED, anchor="w").pack(fill="x", pady=(0, 4))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        self.swatch = ctk.CTkButton(
            row, text="", width=42, height=38, corner_radius=10, fg_color=color,
            hover_color=color, border_width=2, border_color=theme.BORDER_HI, command=self._pick,
        )
        self.swatch.pack(side="left")
        self.var = tk.StringVar(value=color)
        self.entry = make_entry(row, textvariable=self.var, width=104)
        self.entry.pack(side="left", padx=(8, 0))
        self.var.trace_add("write", self._on_text)

    def get(self) -> str:
        return self._color

    def set(self, color: str, notify: bool = False) -> None:
        self._silent = not notify
        self.var.set(color.lower())
        self._silent = False

    def _on_text(self, *_):
        m = _HEX_RE.match(self.var.get().strip())
        if not m:
            self.entry.configure(border_color=theme.DANGER)
            return
        self.entry.configure(border_color=theme.BORDER)
        self._color = "#" + m.group(1).lower()
        self.swatch.configure(fg_color=self._color, hover_color=self._color)
        if not self._silent:
            self._command()

    def _pick(self):
        result = colorchooser.askcolor(color=self._color, title="Choose color",
                                       parent=self.winfo_toplevel())
        if result and result[1]:
            self.set(result[1], notify=True)


# Sidebar button
class NavButton(ctk.CTkFrame):
    def __init__(self, master, text: str, command):
        super().__init__(master, fg_color="transparent")
        self.bar = ctk.CTkFrame(self, width=4, height=24, corner_radius=2, fg_color="transparent")
        self.bar.pack(side="left", padx=(0, 8))
        self.btn = ctk.CTkButton(
            self, text=text, anchor="w", height=44, corner_radius=12, fg_color="transparent",
            hover_color=theme.CARD_HI, text_color=theme.MUTED, font=theme.font(14, "bold"),
            command=command,
        )
        self.btn.pack(side="left", fill="x", expand=True)

    def set_active(self, active: bool) -> None:
        self.bar.configure(fg_color=theme.ACCENT if active else "transparent")
        self.btn.configure(
            fg_color=theme.CARD_HI if active else "transparent",
            text_color=theme.TEXT if active else theme.MUTED,
        )
