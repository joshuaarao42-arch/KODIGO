"""Theme tokens."""
import customtkinter as ctk

# Theme colors
BG = ("#F4F7FC", "#0A0E1F")
SHADOW = ("#DCE5F1", "#060917")
SIDEBAR = ("#FFFFFF", "#0F1530")
CARD = ("#FFFFFF", "#131A38")
CARD_HI = ("#EEF3FB", "#1A2348")
INPUT = ("#F8FAFD", "#0E1430")
STAGE = ("#EDF2F9", "#0C1128")

BORDER = ("#E0E7F0", "#2A3568")
BORDER_HI = ("#C7D4E5", "#3B4A8F")

TEXT = ("#19243A", "#E8ECFF")
MUTED = ("#5E6B80", "#A7B1D7")
FAINT = ("#7B8799", "#8591BC")

BLUE = ("#4B83E6", "#4C8DFF")
VIOLET = ("#8267D9", "#8B6CFF")
ACCENT = ("#596FE0", "#6F7BFF")
ACCENT_HOVER = ("#485CC5", "#5C69EE")

SUCCESS = ("#16845B", "#3DDC97")
WARNING = ("#A96A08", "#FFB547")
DANGER = ("#C93F59", "#FF5D7A")
DANGER_HOVER = ("#A93048", "#E04863")
DANGER_SOFT = ("#FCEEF1", "#3A1830")

FONT_FAMILY = "Segoe UI"


def color(value: str | tuple[str, str]) -> str:
    """Resolve active color."""
    if isinstance(value, str):
        return value
    return value[1] if ctk.get_appearance_mode() == "Dark" else value[0]


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)
