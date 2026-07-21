from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from _image_common import sha256_file, write_json


VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".avi", ".mkv"}


def palette_for(image: Image.Image, colors: int = 8) -> list[dict[str, object]]:
    rgb = image.convert("RGB")
    quantized = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    counts = quantized.getcolors(maxcolors=colors) or []
    palette = quantized.getpalette() or []
    total = rgb.width * rgb.height
    result = []
    for count, index in sorted(counts, reverse=True):
        offset = index * 3
        red, green, blue = palette[offset : offset + 3]
        result.append(
            {
                "hex": f"#{red:02X}{green:02X}{blue:02X}",
                "count": int(count),
                "ratio": round(count / total, 6),
            }
        )
    return result


def analyze_image(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    with Image.open(path) as image:
        frame_count = int(getattr(image, "n_frames", 1))
        durations = []
        if frame_count > 1:
            for index in range(frame_count):
                image.seek(index)
                durations.append(int(image.info.get("duration", 0)))
            image.seek(0)
        source = {
            "path": str(path.resolve()),
            "name": path.name,
            "suffix": path.suffix.lower(),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "kind": "animated_image" if frame_count > 1 else "static_image",
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "declared_frame_count": frame_count,
            "decoded_frame_count": frame_count,
            "fps": None,
            "duration_ms": sum(durations),
        }
        return source, palette_for(image)


def analyze_video(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError("OpenCV is required to analyze video references") from error
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {path}")
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError(f"Cannot decode first video frame: {path}")
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    first = Image.fromarray(frame, "RGB")
    source = {
        "path": str(path.resolve()),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "kind": "video",
        "width": width,
        "height": height,
        "mode": "RGB",
        "declared_frame_count": count,
        "decoded_frame_count": None,
        "fps": round(fps, 6) if fps > 0 else None,
        "duration_ms": round(count * 1000 / fps, 3) if fps > 0 else None,
    }
    return source, palette_for(first)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record immutable facts and a compact palette for a screenshot, GIF, or video.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"input not found: {args.input}")
    if args.input.suffix.lower() in VIDEO_SUFFIXES:
        source, palette = analyze_video(args.input)
    else:
        source, palette = analyze_image(args.input)
    write_json(args.output, {"source": source, "palette": palette, "states": [], "viewports": []})
    print(f"PASS analyzed {source['kind']} {source['width']}x{source['height']} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

