"""Application window."""
from __future__ import annotations

import sys

import customtkinter as ctk
from PIL import ImageTk

from .config import APP_NAME, APP_TAGLINE, APP_VERSION, user_data_dir
from .database import HistoryDB
from .ui import assets, theme
from .ui.about_view import AboutView
from .ui.generator_view import GeneratorView
from .ui.history_view import HistoryView
from .ui.widgets import GlassCard, NavButton


class KodigoApp(ctk.CTk):
    NAV = (("studio", "Studio"), ("history", "History"), ("about", "About"))

    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=theme.BG)

        self.title(f"{APP_NAME} — {APP_TAGLINE}")
        self._place_window(1280, 820)
        self.minsize(1120, 740)
        self.db = HistoryDB()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew", padx=(8, 18), pady=18)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self.history = HistoryView(content, self.db, on_open=self._open_from_history)
        self.studio = GeneratorView(content, self.db, on_saved=self.history.refresh)
        self.about = AboutView(content)
        self.views = {"studio": self.studio, "history": self.history, "about": self.about}
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

        self.bind("<Control-s>", lambda _e: self.studio.export_png())
        self.show("studio")
        self.after(250, self._set_icon)

    # Layout
    def _place_window(self, w: int, h: int):
        try:
            scale = self._get_window_scaling()
        except Exception:
            scale = 1.0
        sw, sh = self.winfo_screenwidth() / scale, self.winfo_screenheight() / scale
        w, h = min(w, int(sw - 60)), min(h, int(sh - 90))
        self.geometry(f"{w}x{h}+{int((sw - w) / 2)}+{int((sh - h) / 3)}")

    def _build_sidebar(self):
        side = GlassCard(self, fg=theme.SIDEBAR, width=250)
        side.grid(row=0, column=0, sticky="ns", padx=(18, 8), pady=18)
        body = side.body

        brand = ctk.CTkFrame(body, fg_color="transparent")
        brand.pack(fill="x", pady=(2, 26))
        mark = assets.brand_mark(96)
        self._mark = ctk.CTkImage(light_image=mark, dark_image=mark, size=(46, 46))
        ctk.CTkLabel(brand, image=self._mark, text="").pack(side="left")
        names = ctk.CTkFrame(brand, fg_color="transparent")
        names.pack(side="left", padx=12)
        ctk.CTkLabel(names, text=APP_NAME, font=theme.font(21, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(names, text=APP_TAGLINE, font=theme.font(12), text_color=theme.MUTED,
                     anchor="w").pack(fill="x")

        self.nav_buttons = {}
        for key, label in self.NAV:
            btn = NavButton(body, label, lambda k=key: self.show(k))
            btn.pack(fill="x", pady=3)
            self.nav_buttons[key] = btn

        self.dark_mode = ctk.CTkSwitch(
            body, text="Dark mode", font=theme.font(12, "bold"),
            text_color=theme.MUTED, progress_color=theme.ACCENT,
            button_color=theme.BLUE, button_hover_color=theme.VIOLET,
            command=self._toggle_appearance,
        )
        self.dark_mode.pack(side="bottom", anchor="w", pady=(0, 12))

        # Footer
        tip = ctk.CTkFrame(body, fg_color=theme.CARD, corner_radius=14, border_width=1,
                           border_color=theme.BORDER)
        tip.pack(side="bottom", fill="x")
        ctk.CTkLabel(tip, text="Pro tip", font=theme.font(12, "bold"), text_color=theme.VIOLET,
                     anchor="w").pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(tip, text="Press Ctrl+S to export your QR code as a PNG.", font=theme.font(12),
                     text_color=theme.MUTED, anchor="w", justify="left", wraplength=190).pack(
            fill="x", padx=14, pady=(2, 12))
        ctk.CTkLabel(body, text=f"v{APP_VERSION}", font=theme.font(11), text_color=theme.FAINT).pack(
            side="bottom", pady=(0, 10))

    def _toggle_appearance(self):
        mode = "dark" if self.dark_mode.get() else "light"
        ctk.set_appearance_mode(mode)
        self.studio.refresh_appearance()

    # Navigation
    def show(self, name: str):
        self.views[name].tkraise()
        for key, btn in self.nav_buttons.items():
            btn.set_active(key == name)
        if name == "history":
            self.history.refresh()

    def _open_from_history(self, settings: dict):
        self.show("studio")
        self.studio.load_settings(settings)

    def _set_icon(self):
        try:
            if sys.platform.startswith("win"):
                self.iconbitmap(str(assets.ensure_icon(user_data_dir() / "kodigo.ico")))
            else:
                self._icon_photo = ImageTk.PhotoImage(assets.brand_mark(64))
                self.iconphoto(True, self._icon_photo)
        except Exception:
            pass
