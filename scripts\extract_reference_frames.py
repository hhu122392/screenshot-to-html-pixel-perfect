from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageSequence

from _image_common import sha256_file, write_json


VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".avi", ".mkv"}


def within(time_ms: float, start_ms: float, end_ms: float | None) -> bool:
    return time_ms >= start_ms and (end_ms is None or time_ms <= end_ms)


def extract_image(path: Path, output_dir: Path, start_ms: float, end_ms: float | None) -> dict[str, object]:
    with Image.open(path) as image:
        declared = int(getattr(image, "n_frames", 1))
        frames = []
        time_ms = 0
        source_decoded = 0
        for index, frame in enumerate(ImageSequence.Iterator(image)):
            source_decoded += 1
            duration = int(frame.info.get("duration", image.info.get("duration", 0)))
            if within(time_ms, start_ms, end_ms):
                filename = f"frame-{len(frames):06d}.png"
                frame.convert("RGB").save(output_dir / filename)
                frames.append(
                    {
                        "index": len(frames),
                        "source_index": index,
                        "time_ms": time_ms,
                        "duration_ms": duration,
                        "file": filename,
                    }
                )
            time_ms += duration
        if source_decoded != declared:
            raise RuntimeError(f"Frame loss: declared={declared}, decoded={source_decoded}")
        return {
            "kind": "animated_image" if declared > 1 else "static_image",
            "source_declared_frame_count": declared,
            "source_decoded_frame_count": source_decoded,
            "declared_frame_count": len(frames),
            "decoded_frame_count": len(frames),
            "fps": None,
            "frames": frames,
        }


def extract_video(path: Path, output_dir: Path, start_ms: float, end_ms: float | None) -> dict[str, object]:
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError("OpenCV is required to extract video frames") from error
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {path}")
    declared = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frames = []
    source_decoded = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        source_index = source_decoded
        source_decoded += 1
        time_ms = source_index * 1000 / fps if fps > 0 else float(capture.get(cv2.CAP_PROP_POS_MSEC))
        if within(time_ms, start_ms, end_ms):
            filename = f"frame-{len(frames):06d}.png"
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            Image.fromarray(rgb, "RGB").save(output_dir / filename)
            frames.append(
                {
                    "index": len(frames),
                    "source_index": source_index,
                    "time_ms": round(time_ms, 3),
                    "duration_ms": round(1000 / fps, 3) if fps > 0 else None,
                    "file": filename,
                }
            )
    capture.release()
    if start_ms == 0 and end_ms is None and declared > 0 and source_decoded != declared:
        raise RuntimeError(f"Frame loss: declared={declared}, decoded={source_decoded}")
    return {
        "kind": "video",
        "source_declared_frame_count": declared,
        "source_decoded_frame_count": source_decoded,
        "declared_frame_count": len(frames),
        "decoded_frame_count": len(frames),
        "fps": round(fps, 6) if fps > 0 else None,
        "frames": frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode every frame in an image or bounded video clip without sampling.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--start-ms", type=float, default=0)
    parser.add_argument("--end-ms", type=float)
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"input not found: {args.input}")
    if args.end_ms is not None and args.end_ms < args.start_ms:
        parser.error("end-ms must be greater than or equal to start-ms")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.input.suffix.lower() in VIDEO_SUFFIXES:
        manifest = extract_video(args.input, args.output_dir, args.start_ms, args.end_ms)
    else:
        manifest = extract_image(args.input, args.output_dir, args.start_ms, args.end_ms)
    manifest.update(
        {
            "source": str(args.input.resolve()),
            "source_sha256": sha256_file(args.input),
            "clip_start_ms": args.start_ms,
            "clip_end_ms": args.end_ms,
        }
    )
    write_json(args.output_dir / "frames.json", manifest)
    print(f"PASS decoded {manifest['decoded_frame_count']} of {manifest['source_decoded_frame_count']} source frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

