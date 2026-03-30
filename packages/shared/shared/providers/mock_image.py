"""Mock image provider — generates placeholder PNGs for flow testing."""

from __future__ import annotations

import io
import random
import struct
import time
import zlib
from typing import Any

from shared.providers.image_base import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageProvider,
)


def _generate_placeholder_png(
    width: int,
    height: int,
    seed: int,
    text: str = "",
) -> bytes:
    """Generate a simple colored PNG with no external dependencies."""
    rng = random.Random(seed)
    r, g, b = rng.randint(30, 200), rng.randint(30, 200), rng.randint(30, 200)

    raw_rows = []
    for y in range(height):
        row = bytearray()
        row.append(0)  # filter byte
        for x in range(width):
            # gradient effect
            gr = int(r * (1 - y / height * 0.4))
            gg = int(g * (1 - x / width * 0.3))
            gb = int(b * (1 - (x + y) / (width + height) * 0.3))
            row.extend([max(0, min(255, gr)), max(0, min(255, gg)), max(0, min(255, gb))])
        raw_rows.append(bytes(row))
    raw_data = b"".join(raw_rows)

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    compressed = zlib.compress(raw_data)

    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", compressed)
    png += _chunk(b"IEND", b"")
    return png


class MockImageProvider(ImageProvider):
    """Generates colored placeholder PNGs — no external API calls."""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        start = time.monotonic()
        images: list[GeneratedImage] = []

        base_seed = request.seed if request.seed is not None else random.randint(0, 2**31)

        w = min(request.width, 512)
        h = min(request.height, 512)

        for i in range(request.num_variants):
            seed = base_seed + i
            png_bytes = _generate_placeholder_png(
                width=w,
                height=h,
                seed=seed,
                text=request.prompt[:40],
            )
            images.append(
                GeneratedImage(
                    image_bytes=png_bytes,
                    width=w,
                    height=h,
                    mime_type="image/png",
                    seed=seed,
                    variant_index=i,
                    metadata={"prompt_preview": request.prompt[:100]},
                )
            )

        elapsed = int((time.monotonic() - start) * 1000)

        return ImageGenerationResponse(
            images=images,
            model="mock-placeholder",
            provider="mock",
            latency_ms=elapsed,
            cost_estimate=0.0,
            metadata={"note": "placeholder image for flow testing"},
        )

    async def health_check(self) -> bool:
        return True
