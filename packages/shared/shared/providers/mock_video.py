"""Mock video provider — generates a minimal valid MP4 for flow testing.

The generated MP4 contains a single solid-color frame repeated for the
requested duration. It's tiny but playable in browsers, which is enough
to validate the entire pipeline end-to-end.
"""

from __future__ import annotations

import random
import struct
import time
from typing import Any

from shared.providers.video_base import (
    GeneratedVideo,
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoProvider,
)


def _generate_placeholder_mp4(
    width: int,
    height: int,
    duration_sec: float,
    fps: int,
    seed: int,
) -> bytes:
    """Create a minimal MP4 with colored frames using raw ftyp/moov/mdat atoms.

    Produces a valid but very small file that browsers can play.
    """
    rng = random.Random(seed)
    r, g, b = rng.randint(30, 200), rng.randint(30, 200), rng.randint(30, 200)

    w = min(width, 320)
    h = min(height, 180)
    num_frames = max(1, int(duration_sec * fps))
    timescale = 600
    frame_dur = timescale // fps

    yuv_y = int(0.299 * r + 0.587 * g + 0.114 * b)
    yuv_u = int(-0.169 * r - 0.331 * g + 0.5 * b + 128)
    yuv_v = int(0.5 * r - 0.419 * g - 0.081 * b + 128)
    yuv_y = max(16, min(235, yuv_y))
    yuv_u = max(16, min(240, yuv_u))
    yuv_v = max(16, min(240, yuv_v))

    # --- Construct raw H.264 bitstream (single I-frame, repeated) ---
    sps = bytes([
        0x67, 0x42, 0xc0, 0x1e, 0xd9, 0x00,
        (w >> 8) & 0xff, w & 0xff,
        (h >> 8) & 0xff, h & 0xff,
        0x00, 0x00, 0x00, 0x01,
    ])
    pps = bytes([0x68, 0xce, 0x38, 0x80])

    mb_w = (w + 15) // 16
    mb_h = (h + 15) // 16

    slice_data = bytearray([0x65, 0x88, 0x80, 0x40])
    for _mb in range(mb_w * mb_h):
        slice_data.extend([yuv_y & 0xff, yuv_u & 0xff, yuv_v & 0xff])

    nalu_sps = b'\x00\x00\x00\x01' + sps
    nalu_pps = b'\x00\x00\x00\x01' + pps
    nalu_slice = b'\x00\x00\x00\x01' + bytes(slice_data)
    i_frame = nalu_sps + nalu_pps + nalu_slice

    sample_size = len(i_frame)

    mdat_payload = i_frame * num_frames
    mdat_size = 8 + len(mdat_payload)

    def box(box_type: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", 8 + len(payload)) + box_type + payload

    def fullbox(box_type: bytes, version: int, flags: int, payload: bytes) -> bytes:
        return box(box_type, struct.pack(">I", (version << 24) | flags) + payload)

    # ftyp
    ftyp = box(b'ftyp', b'isom' + struct.pack(">I", 0x200) + b'isomiso2mp41')

    # stts
    stts_data = struct.pack(">II", num_frames, frame_dur)
    stts = fullbox(b'stts', 0, 0, struct.pack(">I", 1) + stts_data)

    # stss (sync samples — all are key frames)
    stss_entries = b''.join(struct.pack(">I", i + 1) for i in range(num_frames))
    stss = fullbox(b'stss', 0, 0, struct.pack(">I", num_frames) + stss_entries)

    # stsc
    stsc = fullbox(b'stsc', 0, 0, struct.pack(">I", 1) + struct.pack(">III", 1, num_frames, 1))

    # stsz
    stsz_entries = struct.pack(">I", sample_size) * num_frames
    stsz = fullbox(b'stsz', 0, 0, struct.pack(">II", 0, num_frames) + stsz_entries)

    # stco (will be fixed up after we know moov size)
    stco_placeholder = fullbox(b'stco', 0, 0, struct.pack(">II", 1, 0))

    # stsd — avc1 sample entry (simplified)
    avcc = box(b'avcC', bytes([
        1, sps[1] if len(sps) > 1 else 0x42, sps[2] if len(sps) > 2 else 0xc0,
        sps[3] if len(sps) > 3 else 0x1e, 0xff, 0xe1,
        (len(sps) >> 8) & 0xff, len(sps) & 0xff,
    ]) + sps + bytes([
        0x01,
        (len(pps) >> 8) & 0xff, len(pps) & 0xff,
    ]) + pps)

    avc1_payload = (
        bytes(6)  # reserved
        + struct.pack(">H", 1)  # data ref index
        + bytes(16)  # pre-defined + reserved
        + struct.pack(">HH", w, h)
        + struct.pack(">II", 0x00480000, 0x00480000)  # 72dpi
        + bytes(4)  # reserved
        + struct.pack(">H", 1)  # frame count
        + bytes(32)  # compressor name
        + struct.pack(">H", 0x0018)  # depth
        + struct.pack(">h", -1)  # pre-defined
        + avcc
    )
    avc1 = box(b'avc1', avc1_payload)
    stsd = fullbox(b'stsd', 0, 0, struct.pack(">I", 1) + avc1)

    stbl = box(b'stbl', stsd + stts + stss + stsc + stsz + stco_placeholder)

    vmhd = fullbox(b'vmhd', 0, 1, bytes(8))
    dref = fullbox(b'dref', 0, 0, struct.pack(">I", 1) + fullbox(b'url ', 0, 1, b''))
    dinf = box(b'dinf', dref)
    minf = box(b'minf', vmhd + dinf + stbl)

    total_dur = num_frames * frame_dur
    mdhd = fullbox(b'mdhd', 0, 0, struct.pack(">IIII", 0, 0, timescale, total_dur) + bytes(4))
    hdlr = fullbox(b'hdlr', 0, 0, bytes(4) + b'vide' + bytes(12) + b'VideoHandler\x00')
    tkhd = fullbox(b'tkhd', 0, 3, struct.pack(">IIIII", 0, 0, 1, 0, total_dur) + bytes(8) +
                   struct.pack(">hh", 0, 0) + bytes(4) +
                   struct.pack(">IIIIIIIII", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) +
                   struct.pack(">II", w << 16, h << 16))

    mdia = box(b'mdia', mdhd + hdlr + minf)
    trak = box(b'trak', tkhd + mdia)

    mvhd = fullbox(b'mvhd', 0, 0, struct.pack(">IIII", 0, 0, timescale, total_dur) +
                   struct.pack(">I", 0x10000) + struct.pack(">H", 0x100) + bytes(10) +
                   struct.pack(">IIIIIIIII", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) +
                   bytes(24) + struct.pack(">I", 2))

    moov = box(b'moov', mvhd + trak)

    # Fix stco offset: ftyp + moov + mdat header (8 bytes)
    mdat_data_offset = len(ftyp) + len(moov) + 8
    stco_offset_pos = moov.rfind(b'stco') + 4 + 4 + 4  # after size+type+version+count
    moov_ba = bytearray(moov)
    struct.pack_into(">I", moov_ba, stco_offset_pos, mdat_data_offset)
    moov = bytes(moov_ba)

    mdat = struct.pack(">I", mdat_size) + b'mdat' + mdat_payload

    return ftyp + moov + mdat


class MockVideoProvider(VideoProvider):
    """Generates a minimal placeholder MP4 — no external API calls."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        start = time.monotonic()

        seed = request.seed if request.seed is not None else random.randint(0, 2**31)

        w = min(request.width, 320)
        h = min(request.height, 180)
        fps = min(request.fps, 12)

        mp4_bytes = _generate_placeholder_mp4(
            width=w,
            height=h,
            duration_sec=request.duration_sec,
            fps=fps,
            seed=seed,
        )

        elapsed = int((time.monotonic() - start) * 1000)

        video = GeneratedVideo(
            video_bytes=mp4_bytes,
            width=w,
            height=h,
            duration_sec=request.duration_sec,
            fps=fps,
            mime_type="video/mp4",
            seed=seed,
            metadata={
                "mode": request.mode,
                "has_start_frame": request.start_frame_bytes is not None,
                "has_end_frame": request.end_frame_bytes is not None,
                "prompt_preview": request.prompt[:100],
            },
        )

        return VideoGenerationResponse(
            video=video,
            model="mock-placeholder",
            provider="mock",
            latency_ms=elapsed,
            cost_estimate=0.0,
            metadata={"note": "placeholder video for flow testing"},
        )

    async def health_check(self) -> bool:
        return True
