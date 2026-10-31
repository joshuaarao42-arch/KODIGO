"""Input forms."""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from . import theme
from .. import payloads
from .widgets import make_entry, segmented


class BaseForm(ctk.CTkFrame):
    kind = ""

    def __init__(self, master, on_change):
        super().__init__(master, fg_color="transparent")
        self.on_change = on_change
        self.vars: dict = {}

    def _label(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=theme.font(12, "bold"),
                            text_color=theme.MUTED, anchor="w")

    def _entry(self, parent, key, placeholder="", **kw):
        var = tk.StringVar()
        var.trace_add("write", lambda *_: self.on_change())
        self.vars[key] = var
        return make_entry(parent, textvariable=var, placeholder_text=placeholder, **kw)

    def get_fields(self) -> dict:
        return {k: v.get() for k, v in self.vars.items()}

    def set_fields(self, data: dict) -> None:
        for k, v in self.vars.items():
            v.set(data.get(k, ""))


class UrlForm(BaseForm):
    kind = "url"

    def __init__(self, master, on_change):
        super().__init__(master, on_change)
        self._label(self, "Website URL").pack(fill="x", pady=(0, 4))
        self._entry(self, "url", "https://example.com").pack(fill="x")
        ctk.CTkLabel(self, text="https:// is added automatically if you leave it out.",
                     font=theme.font(11), text_color=theme.FAINT, anchor="w").pack(fill="x", pady=(6, 0))


class TextForm(BaseForm):
    kind = "text"

    def __init__(self, master, on_change):
        super().__init__(master, on_change)
        self._label(self, "Your text").pack(fill="x", pady=(0, 4))
        self.box = ctk.CTkTextbox(
            self, height=140, corner_radius=10, fg_color=theme.INPUT, border_width=1,
            border_color=theme.BORDER, text_color=theme.TEXT, font=theme.font(13),
        )
        self.box.pack(fill="x")
        self.box.bind("<KeyRelease>", lambda e: self.on_change())

    def get_fields(self) -> dict:
        return {"text": self.box.get("1.0", "end-1c")}

    def set_fields(self, data: dict) -> None:
        self.box.delete("1.0", "end")
        self.box.insert("1.0", data.get("text", ""))


class ContactForm(BaseForm):
    kind = "contact"

    def __init__(self, master, on_change):
        super().__init__(master, on_change)
        self.grid_columnconfigure((0, 1), weight=1, uniform="c")

        def field(row, col, label, key, ph, span=1):
            cell = ctk.CTkFrame(self, fg_color="transparent")
            cell.grid(row=row, column=col, columnspan=span, sticky="ew",
                      padx=(0, 8) if col == 0 and span == 1 else 0, pady=(0, 8))
            self._label(cell, label).pack(fill="x", pady=(0, 4))
            self._entry(cell, key, ph).pack(fill="x")

        field(0, 0, "First name", "first", "Juan")
        field(0, 1, "Last name", "last", "Dela Cruz")
        field(1, 0, "Company", "org", "Acme Inc.")
        field(1, 1, "Job title", "title", "Designer")
        field(2, 0, "Phone", "phone", "+63 900 000 0000")
        field(2, 1, "Email", "email", "name@example.com")
        field(3, 0, "Website", "website", "https://example.com", span=2)
        field(4, 0, "Address", "address", "Street, City, Country", span=2)


class WifiForm(BaseForm):
    kind = "wifi"
    SECURITY = list(payloads.WIFI_SECURITY.keys())

    def __init__(self, master, on_change):
        super().__init__(master, on_change)
        self._label(self, "Network name (SSID)").pack(fill="x", pady=(0, 4))
        self._entry(self, "ssid", "MyHomeWiFi").pack(fill="x")

        self._label(self, "Password").pack(fill="x", pady=(10, 4))
        self.pw = self._entry(self, "password", "Network password", show="•")
        self.pw.pack(fill="x")
        self.show_pw = ctk.CTkCheckBox(
            self, text="Show password", font=theme.font(12), text_color=theme.MUTED,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, border_color=theme.BORDER_HI,
            command=lambda: self.pw.configure(show="" if self.show_pw.get() else "•"),
        )
        self.show_pw.pack(anchor="w", pady=(8, 0))

        self._label(self, "Security").pack(fill="x", pady=(10, 4))
        self.security = tk.StringVar(value=self.SECURITY[0])
        self.seg = segmented(self, self.SECURITY, command=lambda v: (self.security.set(v), self.on_change()))
        self.seg.set(self.SECURITY[0])
        self.seg.pack(fill="x")

        self.hidden = ctk.CTkSwitch(
            self, text="Hidden network", font=theme.font(12), text_color=theme.MUTED,
            progress_color=theme.ACCENT, button_color=theme.BLUE, button_hover_color=theme.VIOLET,
            command=self.on_change,
        )
        self.hidden.pack(anchor="w", pady=(12, 0))

    def get_fields(self) -> dict:
        data = super().get_fields()
        data["security"] = self.security.get()
        data["hidden"] = "1" if self.hidden.get() else "0"
        return data

    def set_fields(self, data: dict) -> None:
        super().set_fields(data)
        sec = data.get("security") if data.get("security") in self.SECURITY else self.SECURITY[0]
        self.security.set(sec)
        self.seg.set(sec)
        (self.hidden.select if str(data.get("hidden", "0")) == "1" else self.hidden.deselect)()


FORMS = {"url": UrlForm, "text": TextForm, "contact": ContactForm, "wifi": WifiForm}
