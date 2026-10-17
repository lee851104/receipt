"""Assemble fictional browser captures; requires Pillow in the chosen tooling environment."""
from pathlib import Path
import json
from PIL import Image
root = Path(__file__).resolve().parents[1]
folder = root / "runtime/v2-demo-frames"
manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
if manifest != {"frames": 9, "fixture": True, "api": "mock", "viewport": {"width": 1366, "height": 900}}:
    raise SystemExit("Unexpected capture manifest; rerun capture_v2_demo.cjs.")
paths = [folder / f"{index:02}.png" for index in range(9)]
if len(paths) != 9:
    raise SystemExit("Expected exactly 9 fictional demo frames; run capture_v2_demo.cjs first.")
frames = []
for path in paths:
    with Image.open(path) as frame:
        frames.append(frame.convert("RGB").quantize(colors=128))
output = root / "docs/assets/v2-contract-demo.gif"
output.parent.mkdir(parents=True, exist_ok=True)
frames[0].save(output, save_all=True, append_images=frames[1:], duration=2200, loop=0, optimize=True, disposal=2)
print(f"Wrote {len(frames)} frames, {output.stat().st_size} bytes.")
