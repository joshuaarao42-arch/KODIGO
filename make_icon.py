"""Icon generator."""
from pathlib import Path

from KODIGO.ui.assets import ensure_icon

out = Path(__file__).parent / "assets" / "kodigo.ico"
out.parent.mkdir(exist_ok=True)
ensure_icon(out)
print(f"Icon written to {out}")
