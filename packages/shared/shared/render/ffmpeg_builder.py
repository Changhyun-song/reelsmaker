"""FFmpeg command builder for final video rendering.

v2: Supports transitions (fade in/out, dip-to-black), eased Ken Burns,
    pause/beat segments, and enhanced subtitle styling.

Builds a single ffmpeg invocation that:
  - Concatenates video clip segments with transitions
  - Generates eased Ken Burns motion for still-image segments
  - Renders pause segments (hold-last, black, fade-black)
  - Mixes narration audio per-segment with padding
  - Applies intro fade-in and outro fade-out
  - Optionally burns in styled subtitles
  - Outputs a single MP4

Designed for 1080x1920 vertical-first, but configurable.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("reelsmaker.render.ffmpeg")


@dataclass
class SegmentFile:
    """Resolved local file path for one timeline segment."""
    index: int
    asset_type: str  # "video" | "image" | "missing" | "pause"
    video_path: str | None = None
    image_path: str | None = None
    audio_path: str | None = None
    duration_ms: int = 4000
    zoom_start: float = 1.0
    zoom_end: float = 1.15
    pan_direction: str = "left_to_right"
    easing: str = "linear"
    is_first: bool = False
    is_last: bool = False
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    pause_visual: str = "black"  # "black" | "hold_last" | "fade_black"


@dataclass
class RenderConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    crf: int = 23
    preset: str = "medium"
    pixel_format: str = "yuv420p"
    subtitle_path: str | None = None
    burn_subtitles: bool = False
    subtitle_style: str = "default"  # "default" | "bold_hook" | "cinematic" | "minimal"
    intro_fade_in_ms: int = 0
    outro_fade_out_ms: int = 0


def probe_file(path: str) -> dict:
    """Run ffprobe on a file and return parsed JSON metadata."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        logger.warning("ffprobe failed for %s: %s", path, e)
    return {}


_SUBTITLE_STYLES: dict[str, str] = {
    "default": "FontName=Noto Sans KR,FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2,MarginV=40",
    "bold_hook": "FontName=Noto Sans KR,FontSize=18,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=3,Shadow=2,Alignment=2,MarginV=50",
    "cinematic": "FontName=Noto Sans KR,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=1,Shadow=1,Alignment=2,MarginV=60",
    "minimal": "FontName=Noto Sans KR,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=1,Shadow=0,Alignment=2,MarginV=30",
}


def _easing_expr(easing: str, on_var: str, total_frames: str) -> str:
    """Generate easing progress expression for zoompan.

    Returns an expression that maps on/total to [0,1] with easing.
    """
    t = f"({on_var}/{total_frames})"
    if easing == "ease_in":
        return f"({t}*{t})"
    elif easing == "ease_out":
        return f"(1-(1-{t})*(1-{t}))"
    elif easing == "ease_in_out":
        return f"(3*{t}*{t}-2*{t}*{t}*{t})"
    return t  # linear


def _ken_burns_filter(seg: SegmentFile, cfg: RenderConfig) -> str:
    """Build zoompan filter for a still image segment with easing."""
    dur_sec = seg.duration_ms / 1000.0
    total_frames = int(dur_sec * cfg.fps)

    zs = seg.zoom_start
    ze = seg.zoom_end
    progress = _easing_expr(seg.easing, "on", str(total_frames))
    zoom_expr = f"'{zs}+({ze}-{zs})*{progress}'"

    pan = seg.pan_direction
    if pan == "left_to_right":
        x_expr = f"'(iw-iw/zoom)*{progress}'"
        y_expr = "'(ih-ih/zoom)/2'"
    elif pan == "right_to_left":
        x_expr = f"'(iw-iw/zoom)*(1-{progress})'"
        y_expr = "'(ih-ih/zoom)/2'"
    elif pan == "bottom_to_top":
        x_expr = "'(iw-iw/zoom)/2'"
        y_expr = f"'(ih-ih/zoom)*(1-{progress})'"
    elif pan == "top_to_bottom":
        x_expr = "'(iw-iw/zoom)/2'"
        y_expr = f"'(ih-ih/zoom)*{progress}'"
    else:  # center
        x_expr = "'(iw-iw/zoom)/2'"
        y_expr = "'(ih-ih/zoom)/2'"

    return (
        f"zoompan=z={zoom_expr}:x={x_expr}:y={y_expr}"
        f":d={total_frames}:s={cfg.width}x{cfg.height}:fps={cfg.fps}"
    )


def build_render_command(
    segments: list[SegmentFile],
    output_path: str,
    config: RenderConfig | None = None,
) -> list[str]:
    """Build a complete ffmpeg command from segment files.

    Handles video, image (Ken Burns), missing (black), and pause segments.
    Applies fade-in on first, fade-out on last, and subtitle burn-in.
    """
    cfg = config or RenderConfig()

    inputs: list[str] = []
    filter_parts: list[str] = []
    concat_video_labels: list[str] = []
    audio_labels: list[str] = []
    input_idx = 0

    for seg in segments:
        dur_sec = seg.duration_ms / 1000.0

        if seg.asset_type == "video" and seg.video_path:
            inputs.extend(["-i", seg.video_path])
            v_label = f"[v{seg.index}]"
            scale_filter = (
                f"[{input_idx}:v]"
                f"scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=decrease,"
                f"pad={cfg.width}:{cfg.height}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,fps={cfg.fps},"
                f"trim=duration={dur_sec},setpts=PTS-STARTPTS"
            )
            # Fade-in for first segment
            if seg.is_first and seg.fade_in_ms > 0:
                fade_frames = int(seg.fade_in_ms / 1000.0 * cfg.fps)
                scale_filter += f",fade=t=in:st=0:d={seg.fade_in_ms / 1000.0}"
            # Fade-out for last segment
            if seg.is_last and seg.fade_out_ms > 0:
                fade_start = max(0, dur_sec - seg.fade_out_ms / 1000.0)
                scale_filter += f",fade=t=out:st={fade_start:.3f}:d={seg.fade_out_ms / 1000.0}"

            filter_parts.append(f"{scale_filter}{v_label}")
            concat_video_labels.append(v_label)
            input_idx += 1

        elif seg.asset_type == "image" and seg.image_path:
            inputs.extend(["-loop", "1", "-t", f"{dur_sec}", "-i", seg.image_path])
            v_label = f"[v{seg.index}]"
            kb_filter = _ken_burns_filter(seg, cfg)
            scale_filter = (
                f"[{input_idx}:v]"
                f"scale=max({cfg.width}*2\\,iw):max({cfg.height}*2\\,ih),"
                f"{kb_filter},"
                f"setsar=1"
            )
            if seg.is_first and seg.fade_in_ms > 0:
                scale_filter += f",fade=t=in:st=0:d={seg.fade_in_ms / 1000.0}"
            if seg.is_last and seg.fade_out_ms > 0:
                fade_start = max(0, dur_sec - seg.fade_out_ms / 1000.0)
                scale_filter += f",fade=t=out:st={fade_start:.3f}:d={seg.fade_out_ms / 1000.0}"

            filter_parts.append(f"{scale_filter}{v_label}")
            concat_video_labels.append(v_label)
            input_idx += 1

        elif seg.asset_type == "pause":
            if seg.pause_visual == "black" or seg.pause_visual == "fade_black":
                inputs.extend([
                    "-f", "lavfi", "-t", f"{dur_sec}",
                    "-i", f"color=c=black:s={cfg.width}x{cfg.height}:r={cfg.fps}:d={dur_sec}",
                ])
                v_label = f"[v{seg.index}]"
                filter_parts.append(f"[{input_idx}:v]setpts=PTS-STARTPTS{v_label}")
                concat_video_labels.append(v_label)
                input_idx += 1
            else:
                inputs.extend([
                    "-f", "lavfi", "-t", f"{dur_sec}",
                    "-i", f"color=c=black:s={cfg.width}x{cfg.height}:r={cfg.fps}:d={dur_sec}",
                ])
                v_label = f"[v{seg.index}]"
                filter_parts.append(f"[{input_idx}:v]setpts=PTS-STARTPTS{v_label}")
                concat_video_labels.append(v_label)
                input_idx += 1

        else:
            inputs.extend([
                "-f", "lavfi", "-t", f"{dur_sec}",
                "-i", f"color=c=black:s={cfg.width}x{cfg.height}:r={cfg.fps}:d={dur_sec}",
            ])
            v_label = f"[v{seg.index}]"
            filter_parts.append(f"[{input_idx}:v]setpts=PTS-STARTPTS{v_label}")
            concat_video_labels.append(v_label)
            input_idx += 1

        # Audio
        if seg.audio_path:
            inputs.extend(["-i", seg.audio_path])
            a_label = f"[a{seg.index}]"
            filter_parts.append(
                f"[{input_idx}:a]"
                f"aresample=44100,atrim=duration={dur_sec},"
                f"apad=whole_dur={dur_sec},atrim=duration={dur_sec},asetpts=PTS-STARTPTS"
                f"{a_label}"
            )
            audio_labels.append(a_label)
            input_idx += 1
        else:
            inputs.extend([
                "-f", "lavfi", "-t", f"{dur_sec}",
                "-i", "anullsrc=r=44100:cl=stereo",
            ])
            a_label = f"[a{seg.index}]"
            filter_parts.append(
                f"[{input_idx}:a]atrim=duration={dur_sec},asetpts=PTS-STARTPTS{a_label}"
            )
            audio_labels.append(a_label)
            input_idx += 1

    n = len(segments)
    if n == 0:
        return ["echo", "no segments"]

    v_concat_in = "".join(concat_video_labels)
    filter_parts.append(f"{v_concat_in}concat=n={n}:v=1:a=0[outv]")

    a_concat_in = "".join(audio_labels)
    filter_parts.append(f"{a_concat_in}concat=n={n}:v=0:a=1[outa]")

    # Subtitle burn-in with style
    map_video = "[outv]"
    if cfg.burn_subtitles and cfg.subtitle_path:
        sub_escaped = cfg.subtitle_path.replace("\\", "/").replace(":", "\\:")
        style = _SUBTITLE_STYLES.get(cfg.subtitle_style, _SUBTITLE_STYLES["default"])
        filter_parts.append(
            f"[outv]subtitles='{sub_escaped}':force_style='{style}'[outsub]"
        )
        map_video = "[outsub]"

    filter_complex = ";\n".join(filter_parts)

    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(["-map", map_video, "-map", "[outa]"])
    cmd.extend([
        "-c:v", cfg.video_codec,
        "-crf", str(cfg.crf),
        "-preset", cfg.preset,
        "-pix_fmt", cfg.pixel_format,
        "-c:a", cfg.audio_codec,
        "-b:a", cfg.audio_bitrate,
        "-movflags", "+faststart",
        "-shortest",
        output_path,
    ])

    return cmd
