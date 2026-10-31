"""QR payloads."""
from __future__ import annotations

KINDS = (("url", "Link"), ("text", "Text"), ("contact", "Contact"), ("wifi", "Wi-Fi"))
KIND_LABEL = dict(KINDS)

WIFI_SECURITY = {"WPA/WPA2/WPA3": "WPA", "WEP": "WEP", "None": "nopass"}


def _s(fields: dict, key: str) -> str:
    return (fields.get(key) or "").strip()


# URL and text
def _build_url(f: dict) -> str:
    url = _s(f, "url")
    if not url:
        return ""
    if "://" not in url and not url.lower().startswith(("mailto:", "tel:", "sms:")):
        url = "https://" + url
    return url


def _build_text(f: dict) -> str:
    return (f.get("text") or "").rstrip()


# vCard
def _v(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _full_name(f: dict) -> str:
    return " ".join(p for p in (_s(f, "first"), _s(f, "last")) if p)


def _build_contact(f: dict) -> str:
    name = _full_name(f)
    if not any(_s(f, k) for k in ("first", "last", "org", "phone", "email")):
        return ""
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{_v(_s(f, 'last'))};{_v(_s(f, 'first'))};;;",
        f"FN:{_v(name or _s(f, 'org'))}",
    ]
    if _s(f, "org"):
        lines.append(f"ORG:{_v(_s(f, 'org'))}")
    if _s(f, "title"):
        lines.append(f"TITLE:{_v(_s(f, 'title'))}")
    if _s(f, "phone"):
        lines.append(f"TEL;TYPE=CELL:{_v(_s(f, 'phone'))}")
    if _s(f, "email"):
        lines.append(f"EMAIL;TYPE=INTERNET:{_v(_s(f, 'email'))}")
    if _s(f, "website"):
        lines.append(f"URL:{_s(f, 'website')}")
    if _s(f, "address"):
        lines.append(f"ADR;TYPE=WORK:;;{_v(_s(f, 'address'))};;;;")
    lines.append("END:VCARD")
    return "\n".join(lines)


# Wi-Fi
def _w(value: str) -> str:
    for ch in ("\\", ";", ",", ":", '"'):
        value = value.replace(ch, "\\" + ch)
    return value


def _build_wifi(f: dict) -> str:
    ssid = _s(f, "ssid")
    if not ssid:
        return ""
    sec = WIFI_SECURITY.get(f.get("security") or "WPA/WPA2/WPA3", "WPA")
    out = f"WIFI:T:{sec};S:{_w(ssid)};"
    if sec != "nopass":
        out += f"P:{_w(f.get('password') or '')};"
    if str(f.get("hidden", "0")) in ("1", "true", "True"):
        out += "H:true;"
    return out + ";"


_BUILDERS = {"url": _build_url, "text": _build_text, "contact": _build_contact, "wifi": _build_wifi}


def build(kind: str, fields: dict) -> str:
    builder = _BUILDERS.get(kind)
    return builder(fields) if builder else ""


def title_for(kind: str, fields: dict) -> str:
    if kind == "url":
        t = _s(fields, "url")
    elif kind == "text":
        t = (fields.get("text") or "").strip().splitlines()[0] if (fields.get("text") or "").strip() else ""
    elif kind == "contact":
        t = _full_name(fields) or _s(fields, "org")
    elif kind == "wifi":
        t = f"Wi-Fi · {_s(fields, 'ssid')}"
    else:
        t = ""
    t = t or "Untitled"
    return t if len(t) <= 56 else t[:53] + "…"
