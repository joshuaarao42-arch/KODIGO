"""QR studio."""
from __future__ import annotations

import hashlib
import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk
from PIL import ImageTk

from .. import payloads, qr_engine
from ..qr_engine import QRStyle
from . import assets, theme
from .forms import FORMS
from .widgets import (ColorField, GlassCard, ghost_button, primary_button,
                      section_label, segmented, slider)

PRESETS = (
    ("Classic", "#000000", "#ffffff"),
    ("Midnight", "#12174a", "#e8ecff"),
    ("Violet", "#5b3fd8", "#f3f0ff"),
    ("Ocean", "#0b5ed7", "#eaf3ff"),
    ("Emerald", "#047857", "#ecfdf5"),
    ("Sunset", "#c2410c", "#fff7ed"),
)
LOGO_TYPES = [("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.ico"), ("All files", "*.*")]


class GeneratorView(ctk.CTkFrame):
    DEBOUNCE_MS = 160

    def __init__(self, master, db, on_saved=None):
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.db, self.on_saved = db, on_saved
        self.kind = "url"
        self.forms: dict = {}
        self._after_id = None
        self._toast_id = None
        self._loading = False
        self._photo = None
        self._result = None
        self._payload = ""
        self._settings: dict = {}
        self._logo_path = None
        self._last_stage = (0, 0)
        self._base_status = ("Waiting for content…", theme.MUTED)

        self.grid_columnconfigure(0, weight=11, uniform="cols")
        self.grid_columnconfigure(1, weight=9, uniform="cols")
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_controls()
        self._build_preview()
        self._select_kind("url")
        self._on_color_change(render=False)
        self._schedule()

    # UI
    def _build_header(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(2, 14))
        ctk.CTkLabel(head, text="QR Studio", font=theme.font(28, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(head, text="Design, preview and export beautiful QR codes in real time.",
                     font=theme.font(13), text_color=theme.MUTED, anchor="w").pack(fill="x")

    def _build_controls(self):
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color=theme.BORDER,
            scrollbar_button_hover_color=theme.BORDER_HI,
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        # Content card
        content = GlassCard(scroll, "Content", "Choose what your QR code should open or share")
        content.pack(fill="x", pady=(0, 14))
        self._labels = {label: key for key, label in payloads.KINDS}
        self.kind_seg = segmented(content.body, [l for _, l in payloads.KINDS],
                                  command=lambda label: self._select_kind(self._labels[label]))
        self.kind_seg.pack(fill="x", pady=(0, 14))
        holder = ctk.CTkFrame(content.body, fg_color="transparent")
        holder.pack(fill="x")
        for key, cls in FORMS.items():
            self.forms[key] = cls(holder, self._schedule)

        # Style card
        style = GlassCard(scroll, "Style", "Colors, logo and module shape")
        style.pack(fill="x", pady=(0, 14))
        b = style.body

        section_label(b, "Colors").pack(fill="x", pady=(0, 6))
        colors = ctk.CTkFrame(b, fg_color="transparent")
        colors.pack(fill="x")
        colors.grid_columnconfigure((0, 1), weight=1, uniform="col")
        defaults = QRStyle()
        self.fg_field = ColorField(colors, "Foreground", defaults.fg, self._on_color_change)
        self.fg_field.grid(row=0, column=0, sticky="w")
        self.bg_field = ColorField(colors, "Background", defaults.bg, self._on_color_change)
        self.bg_field.grid(row=0, column=1, sticky="w")

        presets = ctk.CTkFrame(b, fg_color="transparent")
        presets.pack(fill="x", pady=(12, 0))
        for name, fg, bg in PRESETS:
            ctk.CTkButton(
                presets, text="QR", width=48, height=34, corner_radius=9, fg_color=bg,
                hover_color=bg, text_color=fg, font=theme.font(12, "bold"), border_width=2,
                border_color=theme.BORDER_HI, command=lambda f=fg, g=bg: self._apply_preset(f, g),
            ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            presets, text="⇄ Swap", width=70, height=34, corner_radius=9, fg_color=theme.CARD_HI,
            hover_color=theme.CARD_HI, text_color=theme.TEXT, font=theme.font(12, "bold"),
            command=self._swap_colors,
        ).pack(side="left", padx=(6, 0))

        self.contrast = ctk.CTkLabel(b, text="", font=theme.font(12), anchor="w", justify="left",
                                     wraplength=420)
        self.contrast.pack(fill="x", pady=(10, 0))

        section_label(b, "Center logo").pack(fill="x", pady=(18, 6))
        logo_row = ctk.CTkFrame(b, fg_color="transparent")
        logo_row.pack(fill="x")
        ghost_button(logo_row, "Choose image…", self._choose_logo, height=38, width=140).pack(side="left")
        self.logo_remove = ghost_button(logo_row, "Remove", self._remove_logo, height=38, width=84,
                                        state="disabled")
        self.logo_remove.pack(side="left", padx=(8, 0))
        self.logo_name = ctk.CTkLabel(logo_row, text="No logo", font=theme.font(12),
                                      text_color=theme.FAINT, anchor="w")
        self.logo_name.pack(side="left", padx=12)

        size_row = ctk.CTkFrame(b, fg_color="transparent")
        size_row.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(size_row, text="Logo size", font=theme.font(12), text_color=theme.MUTED,
                     width=80, anchor="w").pack(side="left")
        self.logo_slider = slider(size_row, 0.10, 0.30, 20, self._on_logo_size)
        self.logo_slider.set(defaults.logo_scale)
        self.logo_slider.pack(side="left", fill="x", expand=True, padx=8)
        self.logo_size_lbl = ctk.CTkLabel(size_row, text="22%", width=40, font=theme.font(12, "bold"),
                                          text_color=theme.TEXT)
        self.logo_size_lbl.pack(side="left")

        section_label(b, "Module shape").pack(fill="x", pady=(18, 6))
        self.shape_seg = segmented(b, qr_engine.MODULE_STYLES, command=lambda _: self._schedule())
        self.shape_seg.set(defaults.module_style)
        self.shape_seg.pack(fill="x")

        section_label(b, "Quiet zone (margin)").pack(fill="x", pady=(18, 6))
        margin_row = ctk.CTkFrame(b, fg_color="transparent")
        margin_row.pack(fill="x")
        self.margin_slider = slider(margin_row, 1, 8, 7, self._on_margin)
        self.margin_slider.set(defaults.border)
        self.margin_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.margin_lbl = ctk.CTkLabel(margin_row, text="4", width=40, font=theme.font(12, "bold"),
                                       text_color=theme.TEXT)
        self.margin_lbl.pack(side="left")

        section_label(b, "Export quality").pack(fill="x", pady=(18, 6))
        self.quality_seg = segmented(b, list(qr_engine.QUALITY_BOX_SIZE), command=lambda _: self._schedule())
        self.quality_seg.set(defaults.quality)
        self.quality_seg.pack(fill="x")
        ctk.CTkLabel(b, text="Higher quality = larger PNG (Ultra is great for print).",
                     font=theme.font(11), text_color=theme.FAINT, anchor="w").pack(fill="x", pady=(6, 0))

    def _build_preview(self):
        card = GlassCard(self, "Live preview")
        card.grid(row=1, column=1, sticky="nsew")
        self.stage = ctk.CTkFrame(card.body, fg_color=theme.STAGE, corner_radius=16,
                                  border_width=1, border_color=theme.BORDER)
        self.stage.pack(fill="both", expand=True)
        self.stage.pack_propagate(False)
        self.preview = tk.Label(self.stage, bg=theme.color(theme.STAGE), bd=0, highlightthickness=0,
                                fg=theme.color(theme.MUTED), font=(theme.FONT_FAMILY, 11),
                                compound="center")
        self.preview.place(relx=0.5, rely=0.5, anchor="center")
        self.stage.bind("<Configure>", self._on_stage_configure)

        self.status = ctk.CTkLabel(card.body, text="", font=theme.font(12), text_color=theme.MUTED,
                                   wraplength=380, justify="center")
        self.status.pack(fill="x", pady=(12, 12))

        btns = ctk.CTkFrame(card.body, fg_color="transparent")
        btns.pack(fill="x")
        btns.grid_columnconfigure((0, 1), weight=1, uniform="b")
        self.btn_save = ghost_button(btns, "Save to History", self.save_to_history)
        self.btn_save.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btn_export = primary_button(btns, "Export PNG", self.export_png)
        self.btn_export.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    # State
    def _select_kind(self, key: str):
        if key not in self.forms:
            key = "url"
        self.forms[self.kind].pack_forget()
        self.kind = key
        self.forms[key].pack(fill="x")
        self.kind_seg.set(payloads.KIND_LABEL[key])
        self._schedule()

    def _style(self) -> QRStyle:
        return QRStyle(
            fg=self.fg_field.get(), bg=self.bg_field.get(), logo_path=self._logo_path,
            logo_scale=float(self.logo_slider.get()), module_style=self.shape_seg.get(),
            quality=self.quality_seg.get(), border=int(round(self.margin_slider.get())),
        )

    def _schedule(self, *_):
        if self._loading:
            return
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(self.DEBOUNCE_MS, self._render)

    # Style events
    def _apply_preset(self, fg, bg):
        self.fg_field.set(fg)
        self.bg_field.set(bg)
        self._on_color_change()

    def _swap_colors(self):
        fg, bg = self.fg_field.get(), self.bg_field.get()
        self.fg_field.set(bg)
        self.bg_field.set(fg)
        self._on_color_change()

    def _on_color_change(self, render: bool = True):
        fg, bg = self.fg_field.get(), self.bg_field.get()
        ratio = qr_engine.contrast_ratio(fg, bg)
        if qr_engine.luminance(fg) > qr_engine.luminance(bg):
            text, color = "Light-on-dark codes (inverted) fail on some scanners.", theme.WARNING
        elif ratio < 3:
            text, color = f"Contrast {ratio:.1f}:1 — too low, this may not scan.", theme.DANGER
        elif ratio < 5:
            text, color = f"Contrast {ratio:.1f}:1 — okay, but darker is safer.", theme.WARNING
        else:
            text, color = f"Contrast {ratio:.1f}:1 — scans easily.", theme.SUCCESS
        self.contrast.configure(text=text, text_color=color)
        if render:
            self._schedule()

    def _choose_logo(self):
        path = filedialog.askopenfilename(parent=self.winfo_toplevel(), title="Choose a logo or image",
                                          filetypes=LOGO_TYPES)
        if path:
            self._set_logo(path)
            self._schedule()

    def _set_logo(self, path):
        self._logo_path = path
        name = os.path.basename(path) if path else "No logo"
        self.logo_name.configure(text=name if len(name) < 26 else name[:23] + "…",
                                 text_color=theme.TEXT if path else theme.FAINT)
        self.logo_remove.configure(state="normal" if path else "disabled")

    def _remove_logo(self):
        self._set_logo(None)
        self._schedule()

    def _on_logo_size(self, value):
        self.logo_size_lbl.configure(text=f"{int(round(value * 100))}%")
        self._schedule()

    def _on_margin(self, value):
        self.margin_lbl.configure(text=str(int(round(value))))
        self._schedule()

    # Rendering
    def _stage_size(self):
        w, h = self.stage.winfo_width() - 14, self.stage.winfo_height() - 14
        return (w, h) if w > 120 and h > 120 else (420, 420)

    def _on_stage_configure(self, event):
        if abs(event.width - self._last_stage[0]) > 2 or abs(event.height - self._last_stage[1]) > 2:
            self._last_stage = (event.width, event.height)
            self._schedule()

    def _render(self):
        self._after_id = None
        fields = self.forms[self.kind].get_fields()
        payload = payloads.build(self.kind, fields)
        style = self._style()
        self._payload = payload
        self._settings = {"kind": self.kind, "fields": fields, "style": style.to_dict()}
        state = "normal" if payload else "disabled"
        self.btn_save.configure(state=state)
        self.btn_export.configure(state=state)

        if not payload:
            self._result = None
            self._set_status("Start typing to generate your QR code.", theme.MUTED)
            self._apply_stage()
            return

        w, h = self._stage_size()
        try:
            res = qr_engine.render(payload, style, preview_px=int(min(w, h) * 0.84))
        except qr_engine.QRDataTooLarge as exc:
            self._result = None
            self._set_status(str(exc), theme.DANGER)
            self._apply_stage()
            return
        except Exception as exc:
            self._result = None
            self._set_status(f"Couldn't render: {exc}", theme.DANGER)
            self._apply_stage()
            return

        self._result = res
        msg = f"{res.modules} × {res.modules} modules · error correction {res.ec_label}"
        if res.warnings:
            self._set_status(msg + "\n" + " ".join(res.warnings), theme.WARNING)
        else:
            self._set_status(msg, theme.MUTED)
        self._apply_stage()

    def _apply_stage(self):
        w, h = self._stage_size()
        stage_color = theme.color(theme.STAGE)
        img = assets.compose_stage(self._result.image if self._result else None, w, h, stage_color)
        self._photo = ImageTk.PhotoImage(img)
        self.preview.configure(bg=stage_color, image=self._photo,
                               text="" if self._result else "Your QR code will appear here")

    def refresh_appearance(self):
        self._apply_stage()

    def _set_status(self, text, color):
        self._base_status = (text, color)
        if not self._toast_id:
            self.status.configure(text=text, text_color=color)

    def _toast(self, text, color=theme.SUCCESS, ms=3500):
        if self._toast_id:
            self.after_cancel(self._toast_id)
        self.status.configure(text=text, text_color=color)

        def restore():
            self._toast_id = None
            self.status.configure(text=self._base_status[0], text_color=self._base_status[1])

        self._toast_id = self.after(ms, restore)

    # Actions
    def _flush(self):
        """Flush."""
        if self._after_id:
            self.after_cancel(self._after_id)
            self._render()

    def save_to_history(self, silent: bool = False) -> bool:
        self._flush()
        if not self._payload or not self._result:
            self._toast("Nothing to save yet.", theme.WARNING)
            return False
        sig = hashlib.sha1(json.dumps(self._settings, sort_keys=True).encode()).hexdigest()
        if sig == self.db.latest_signature():
            if not silent:
                self._toast("Already in your history.", theme.MUTED)
            return True
        title = payloads.title_for(self._settings["kind"], self._settings["fields"])
        self.db.add(self._settings["kind"], title, self._payload, self._settings,
                    assets.thumbnail_bytes(self._result.image), sig)
        if self.on_saved:
            self.on_saved()
        if not silent:
            self._toast("Saved to history ✓")
        return True

    def export_png(self):
        self._flush()
        if not self._payload:
            self._toast("Nothing to export yet.", theme.WARNING)
            return
        default = f"kodigo-{self.kind}-{datetime.now():%Y%m%d-%H%M%S}.png"
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), title="Export QR code", defaultextension=".png",
            initialfile=default, filetypes=[("PNG image", "*.png")],
        )
        if not path:
            return
        try:
            res = qr_engine.render(self._payload, self._style())
            qr_engine.save_png(res.image, path)
        except Exception as exc:
            self._toast(f"Export failed: {exc}", theme.DANGER)
            return
        self.save_to_history(silent=True)
        self._toast(f"Exported {res.image.width}×{res.image.height}px PNG ✓")

    def load_settings(self, settings: dict):
        """Settings."""
        self._loading = True
        try:
            self._select_kind(settings.get("kind", "url"))
            self.forms[self.kind].set_fields(settings.get("fields", {}))
            st = QRStyle.from_dict(settings.get("style", {}))
            self.fg_field.set(st.fg)
            self.bg_field.set(st.bg)
            logo = st.logo_path if st.logo_path and os.path.exists(st.logo_path) else None
            self._set_logo(logo)
            self.logo_slider.set(st.logo_scale)
            self.logo_size_lbl.configure(text=f"{int(round(st.logo_scale * 100))}%")
            if st.module_style in qr_engine.MODULE_STYLES:
                self.shape_seg.set(st.module_style)
            if st.quality in qr_engine.QUALITY_BOX_SIZE:
                self.quality_seg.set(st.quality)
            self.margin_slider.set(st.border)
            self.margin_lbl.configure(text=str(st.border))
        finally:
            self._loading = False
        self._on_color_change(render=False)
        if self._after_id:
            self.after_cancel(self._after_id)
        self._render()
