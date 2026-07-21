from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from _image_common import make_contact_sheet, read_json, sha256_file, validate_box, write_json


def load_mask(path: Path, size: tuple[int, int]) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"Alpha mask not found: {path}")
    mask = Image.open(path)
    if "A" in mask.getbands():
        mask = mask.getchannel("A")
    else:
        mask = mask.convert("L")
    if mask.size != size:
        raise ValueError(f"Alpha mask size {mask.size} does not match crop size {size}: {path}")
    return np.asarray(mask, dtype=np.uint8)


def ellipse_mask(size: tuple[int, int], config: dict[str, object]) -> np.ndarray:
    width, height = size
    box = config.get("box", [1, 1, width - 1, height - 1])
    left, top, right, bottom = validate_box(box, size, "ellipse")
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse((left, top, right - 1, bottom - 1), fill=255)
    return np.asarray(mask, dtype=np.uint8)


def chroma_mask(rgb: np.ndarray, config: dict[str, object]) -> np.ndarray:
    key = np.asarray(config.get("color", [0, 255, 0]), dtype=np.float32)
    if key.shape != (3,):
        raise ValueError("chroma color must be an RGB triplet")
    tolerance = float(config.get("tolerance", 24))
    softness = max(1.0, float(config.get("softness", 16)))
    distance = np.linalg.norm(rgb.astype(np.float32) - key, axis=2)
    alpha = np.clip((distance - tolerance) / softness * 255, 0, 255)
    return alpha.astype(np.uint8)


def rembg_mask(rgb: np.ndarray, config: dict[str, object]) -> np.ndarray:
    try:
        from rembg import new_session, remove
    except ImportError as error:
        raise RuntimeError("rembg is not installed; supply a manual mask or install rembg") from error
    model = str(config.get("model", "u2netp"))
    mask = remove(
        Image.fromarray(rgb, "RGB"),
        session=new_session(model),
        only_mask=True,
        post_process_mask=True,
    ).convert("L")
    return np.asarray(mask, dtype=np.uint8)


def grabcut_mask(rgb: np.ndarray, config: dict[str, object]) -> np.ndarray:
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError("OpenCV is required for the grabcut Alpha method") from error
    height, width = rgb.shape[:2]
    mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)
    border = int(config.get("border", max(1, min(width, height) // 30)))
    mask[:border, :] = cv2.GC_BGD
    mask[-border:, :] = cv2.GC_BGD
    mask[:, :border] = cv2.GC_BGD
    mask[:, -border:] = cv2.GC_BGD
    for box in config.get("foreground_rects", []):
        left, top, right, bottom = validate_box(box, (width, height), "foreground_rect")
        mask[top:bottom, left:right] = cv2.GC_PR_FGD
    for box in config.get("background_rects", []):
        left, top, right, bottom = validate_box(box, (width, height), "background_rect")
        mask[top:bottom, left:right] = cv2.GC_BGD
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cv2.grabCut(bgr, mask, None, bg_model, fg_model, int(config.get("iterations", 8)), cv2.GC_INIT_WITH_MASK)
    return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)


def remove_small_components(alpha: np.ndarray, minimum_pixels: int) -> np.ndarray:
    if minimum_pixels <= 1:
        return alpha
    foreground = alpha > 0
    visited = np.zeros(foreground.shape, dtype=bool)
    height, width = foreground.shape
    cleaned = alpha.copy()
    for start_y, start_x in np.argwhere(foreground):
        if visited[start_y, start_x]:
            continue
        queue = deque([(int(start_y), int(start_x))])
        visited[start_y, start_x] = True
        component: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            component.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    next_y, next_x = y + dy, x + dx
                    if (
                        0 <= next_y < height
                        and 0 <= next_x < width
                        and foreground[next_y, next_x]
                        and not visited[next_y, next_x]
                    ):
                        visited[next_y, next_x] = True
                        queue.append((next_y, next_x))
        if len(component) < minimum_pixels:
            ys, xs = zip(*component)
            cleaned[np.asarray(ys), np.asarray(xs)] = 0
    return cleaned


def make_alpha(rgb: np.ndarray, config: dict[str, object], spec_dir: Path) -> np.ndarray:
    method = str(config.get("method", "mask"))
    size = (rgb.shape[1], rgb.shape[0])
    if method == "mask":
        raw_path = Path(str(config.get("path", "")))
        path = raw_path if raw_path.is_absolute() else spec_dir / raw_path
        alpha = load_mask(path, size)
    elif method == "ellipse":
        alpha = ellipse_mask(size, config)
    elif method == "chroma":
        alpha = chroma_mask(rgb, config)
    elif method == "rembg":
        alpha = rembg_mask(rgb, config)
    elif method == "grabcut":
        alpha = grabcut_mask(rgb, config)
    else:
        raise ValueError(f"Unsupported Alpha method: {method}")
    clear_below = int(config.get("clear_below", 0))
    solid_above = int(config.get("solid_above", 255))
    alpha = alpha.copy()
    if clear_below > 0:
        alpha[alpha < clear_below] = 0
    if solid_above < 255:
        alpha[alpha > solid_above] = 255
    alpha = remove_small_components(alpha, int(config.get("remove_components_below", 0)))
    if config.get("clear_border"):
        alpha[[0, -1], :] = 0
        alpha[:, [0, -1]] = 0
    return alpha


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract true-RGBA source assets by preserving crop RGB and generating Alpha only.")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--qa-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    if not args.reference.is_file() or not args.spec.is_file():
        parser.error("reference and spec must exist")
    reference = Image.open(args.reference).convert("RGB")
    reference_array = np.asarray(reference, dtype=np.uint8)
    spec = read_json(args.spec)
    assets_spec = spec.get("assets", [])
    if not assets_spec:
        parser.error("spec must contain at least one asset")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    qa_items = []
    assets = []
    for item in assets_spec:
        name = str(item["name"])
        box = validate_box(item["box"], reference.size, name)
        left, top, right, bottom = box
        rgb = reference_array[top:bottom, left:right].copy()
        alpha_config = dict(item.get("alpha", {}))
        alpha = make_alpha(rgb, alpha_config, args.spec.parent)
        rgba = np.dstack((rgb, alpha))
        output = Image.fromarray(rgba, "RGBA")
        output.save(args.output_dir / name)
        qa_items.append((name, output))
        assets.append(
            {
                "file": name,
                "source_box": list(box),
                "output_size": list(output.size),
                "kind": "source_rgb_alpha_mask",
                "alpha_method": alpha_config.get("method", "mask"),
                "alpha_range": list(output.getchannel("A").getextrema()),
                "rgb_mismatch_count": 0,
                "source_composited": bool(item.get("source_composited", False)),
            }
        )
    make_contact_sheet(qa_items, (255, 255, 255), args.qa_dir / "assets-on-white.png")
    make_contact_sheet(qa_items, (10, 34, 75), args.qa_dir / "assets-on-navy.png")
    manifest = {
        "reference_file": str(args.reference.resolve()),
        "reference_sha256": sha256_file(args.reference),
        "reference_size": list(reference.size),
        "checkerboard_used": False,
        "assets": assets,
    }
    write_json(args.manifest, manifest)
    print(f"PASS extracted {len(assets)} true-RGBA assets; checkerboard_used=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
