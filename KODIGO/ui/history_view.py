"""History view."""
from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime, timezone
from io import BytesIO
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from .. import payloads, qr_engine
from . import theme
from .widgets import danger_button, ghost_button, make_entry, primary_button


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).astimezone()
        return dt.strftime("%b %d, %Y · %I:%M %p")
    except ValueError:
        return iso


class HistoryView(ctk.CTkFrame):
    def __init__(self, master, db, on_open):
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.db, self.on_open = db, on_open
        self._images: list = []
        self._search_after = None
        self._msg_after = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(2, 14))
        head.grid_columnconfigure(0, weight=1)
        titles = ctk.CTkFrame(head, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(titles, text="History", font=theme.font(28, "bold"),
                     text_color=theme.TEXT, anchor="w").pack(fill="x")
        self.subtitle = ctk.CTkLabel(titles, text="", font=theme.font(13),
                                     text_color=theme.MUTED, anchor="w")
        self.subtitle.pack(fill="x")

        tools = ctk.CTkFrame(head, fg_color="transparent")
        tools.grid(row=0, column=1, sticky="e")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        make_entry(tools, textvariable=self.search_var, placeholder_text="Search history…",
                   width=240).pack(side="left", padx=(0, 10))
        danger_button(tools, "Clear all", self._clear_all, width=90, height=38).pack(side="left")

        self.msg = ctk.CTkLabel(self, text="", font=theme.font(12), text_color=theme.SUCCESS, anchor="w")
        self.msg.grid(row=2, column=0, sticky="ew")

        self.list = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color=theme.BORDER,
            scrollbar_button_hover_color=theme.BORDER_HI,
        )
        self.list.grid(row=1, column=0, sticky="nsew")
        self.refresh()

    # Data
    def _on_search(self, *_):
        if self._search_after:
            self.after_cancel(self._search_after)
        self._search_after = self.after(200, self.refresh)

    def refresh(self):
        self._search_after = None
        for child in self.list.winfo_children():
            child.destroy()
        self._images.clear()

        rows = self.db.list(self.search_var.get())
        total = self.db.count()
        self.subtitle.configure(text=f"{total} saved QR code{'s' if total != 1 else ''}")

        if not rows:
            empty = "No matches found." if self.search_var.get().strip() else \
                "Nothing here yet.\nGenerate a QR code in the Studio and hit “Save to History”."
            ctk.CTkLabel(self.list, text=empty, font=theme.font(14), text_color=theme.FAINT,
                         justify="center").pack(pady=80)
            return
        for row in rows:
            self._add_row(row)

    def _add_row(self, row):
        card = ctk.CTkFrame(self.list, fg_color=theme.CARD, corner_radius=16,
                            border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=(0, 10), padx=(0, 6))

        try:
            img = Image.open(BytesIO(row["thumbnail"])).convert("RGB")
            ci = ctk.CTkImage(light_image=img, dark_image=img, size=(76, 76))
            self._images.append(ci)
            ctk.CTkLabel(card, image=ci, text="").pack(side="left", padx=14, pady=14)
        except Exception:
            ctk.CTkFrame(card, width=76, height=76, fg_color=theme.INPUT, corner_radius=10).pack(
                side="left", padx=14, pady=14)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=14)
        ctk.CTkLabel(info, text=row["title"], font=theme.font(14, "bold"), text_color=theme.TEXT,
                     anchor="w").pack(fill="x")
        meta = ctk.CTkFrame(info, fg_color="transparent")
        meta.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(meta, text=payloads.KIND_LABEL.get(row["kind"], row["kind"]),
                     font=theme.font(11, "bold"), text_color="#FFFFFF", fg_color=theme.ACCENT,
                     corner_radius=8, padx=8, height=22).pack(side="left")
        ctk.CTkLabel(meta, text=_fmt_time(row["created_at"]), font=theme.font(12),
                     text_color=theme.MUTED).pack(side="left", padx=10)

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(side="right", padx=14)
        primary_button(actions, "Open", lambda r=row: self._open(r), width=80, height=36).pack(side="left", padx=4)
        ghost_button(actions, "Export", lambda r=row: self._export(r), width=80, height=36).pack(side="left", padx=4)
        danger_button(actions, "Delete", lambda r=row: self._delete(r), width=80).pack(side="left", padx=4)

    # Actions
    def _flash(self, text, color=theme.SUCCESS):
        if self._msg_after:
            self.after_cancel(self._msg_after)
        self.msg.configure(text=text, text_color=color)
        self._msg_after = self.after(3500, lambda: self.msg.configure(text=""))

    def _open(self, row):
        self.on_open(json.loads(row["settings"]))

    def _export(self, row):
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), title="Export QR code", defaultextension=".png",
            initialfile=f"kodigo-{row['kind']}-{row['id']}.png", filetypes=[("PNG image", "*.png")],
        )
        if not path:
            return
        try:
            res = qr_engine.render_from_settings(json.loads(row["settings"]))
            qr_engine.save_png(res.image, path)
            self._flash(f"Exported {res.image.width}×{res.image.height}px PNG ✓")
        except Exception as exc:
            self._flash(f"Export failed: {exc}", theme.DANGER)

    def _delete(self, row):
        self.db.delete(row["id"])
        self.refresh()

    def _clear_all(self):
        if self.db.count() == 0:
            return
        if messagebox.askyesno("Clear history", "Delete all saved QR codes? This can't be undone.",
                               parent=self.winfo_toplevel()):
            self.db.clear()
            self.refresh()
