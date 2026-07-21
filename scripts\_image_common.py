from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_rgb(path: Path) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    return Image.open(path).convert("RGB")


def validate_box(box: list[int] | tuple[int, int, int, int], size: tuple[int, int], label: str) -> tuple[int, int, int, int]:
    if len(box) != 4:
        raise ValueError(f"{label}: box must contain four integers")
    left, top, right, bottom = map(int, box)
    width, height = size
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError(f"{label}: box {(left, top, right, bottom)} outside {size}")
    return left, top, right, bottom


def compare_images(reference: Image.Image, candidate: Image.Image, threshold: float) -> dict[str, Any]:
    reference_rgb = np.asarray(reference.convert("RGB"), dtype=np.int16)
    candidate_rgb = np.asarray(candidate.convert("RGB"), dtype=np.int16)
    if reference_rgb.shape != candidate_rgb.shape:
        raise ValueError(
            f"Image dimensions differ: reference={reference_rgb.shape[1]}x{reference_rgb.shape[0]}, "
            f"candidate={candidate_rgb.shape[1]}x{candidate_rgb.shape[0]}"
        )
    difference = np.abs(reference_rgb - candidate_rgb)
    mean = float(difference.mean())
    maximum = int(difference.max())
    changed_pixels = int(np.any(difference > 0, axis=2).sum())
    total_pixels = int(difference.shape[0] * difference.shape[1])
    return {
        "mean_absolute_channel_difference": round(mean, 6),
        "max_channel_difference": maximum,
        "changed_pixel_count": changed_pixels,
        "total_pixel_count": total_pixels,
        "passed": mean < threshold,
    }


def save_diff(reference: Image.Image, candidate: Image.Image, output: Path) -> None:
    ref = np.asarray(reference.convert("RGB"), dtype=np.int16)
    cand = np.asarray(candidate.convert("RGB"), dtype=np.int16)
    if ref.shape != cand.shape:
        raise ValueError("Cannot save diff for images with different dimensions")
    visible = np.clip(np.abs(ref - cand) * 4, 0, 255).astype(np.uint8)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(visible, "RGB").save(output)


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-.")
    return cleaned or "item"


def make_contact_sheet(
    assets: list[tuple[str, Image.Image]],
    background: tuple[int, int, int],
    output: Path,
) -> None:
    columns = 4
    cell_width = 240
    cell_height = 250
    rows = max(1, (len(assets) + columns - 1) // columns)
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), background)
    draw = ImageDraw.Draw(sheet)
    label = (18, 31, 56) if sum(background) > 500 else (245, 249, 255)
    for index, (name, asset) in enumerate(assets):
        column = index % columns
        row = index // columns
        x0 = column * cell_width
        y0 = row * cell_height
        preview = asset.convert("RGBA").copy()
        preview.thumbnail((210, 195), Image.Resampling.LANCZOS)
        x = x0 + (cell_width - preview.width) // 2
        y = y0 + 10 + (195 - preview.height) // 2
        sheet.paste(preview, (x, y), preview)
        draw.text((x0 + 12, y0 + 218), name, fill=label)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)

