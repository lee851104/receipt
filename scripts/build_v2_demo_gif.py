"""Assemble fictional browser captures; requires Pillow in the chosen tooling environment."""
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parents[1]
paths = sorted((root / "runtime/v2-demo-frames").glob("*.png"))
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
