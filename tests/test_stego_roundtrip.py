from pathlib import Path
from collections.abc import Callable

import numpy as np
import pytest
from PIL import Image

from container import HEADER_PREFIX_SIZE, pack_header
from stego_module import (
    bits_to_bytes_msb,
    capacity,
    embed_message,
    extract_kbits_lsb,
    extract_message_from_image,
    load_rgb_array,
)


@pytest.mark.parametrize(("width", "height"), [(64, 64), (128, 96), (192, 128)])
@pytest.mark.parametrize(("mode", "extra_data"), [(0x01, b"s" * 16), (0x02, b"w" * 256)])
@pytest.mark.parametrize("k", [1, 2, 3])
@pytest.mark.parametrize("image_mode", ["RGB", "RGBA"])
def test_random_payload_roundtrip_and_k1_header(
    tmp_path: Path,
    create_cover: Callable[[int, int, str], Path],
    width: int,
    height: int,
    mode: int,
    extra_data: bytes,
    k: int,
    image_mode: str,
) -> None:
    cover_path = create_cover(width, height, image_mode)
    rng = np.random.default_rng(width + height + mode + k)
    payload = rng.bytes(257)
    nonce = rng.bytes(12)
    output_path = tmp_path / f"stego_{image_mode}_{mode}_{k}.png"

    saved_path = embed_message(
        cover_path,
        output_path,
        payload,
        mode=mode,
        k=k,
        nonce=nonce,
        extra_data=extra_data,
    )

    assert capacity(cover_path, mode, k) == capacity(load_rgb_array(cover_path), mode, k)
    assert saved_path.exists()
    assert extract_message_from_image(saved_path) == (
        payload,
        mode,
        k,
        nonce,
        extra_data,
    )

    header = pack_header(mode, k, nonce, len(payload), extra_data)
    channels = load_rgb_array(saved_path).reshape(-1)
    header_bits, _ = extract_kbits_lsb(channels, len(header) * 8, k=1)
    assert bits_to_bytes_msb(header_bits) == header


def test_rgb_loader_composites_transparency_on_white(
    create_cover: Callable[[int, int, str], Path],
) -> None:
    rgba_path = create_cover(32, 24, "RGBA")
    with Image.open(rgba_path) as image:
        rgba = image.convert("RGBA")
    rgb = load_rgb_array(rgba_path)
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    expected = np.asarray(Image.alpha_composite(background, rgba).convert("RGB"))

    assert rgb.shape == (24, 32, 3)
    np.testing.assert_array_equal(rgb, expected)


@pytest.mark.parametrize("image_mode", ["L", "P"])
def test_grayscale_and_palette_png_roundtrip(
    tmp_path: Path,
    image_mode: str,
) -> None:
    if image_mode == "L":
        image = Image.fromarray(
            np.full((72, 80), 127, dtype=np.uint8),
            mode="L",
        )
    else:
        indices = np.tile(np.arange(3, dtype=np.uint8), (72, 27))[:, :80]
        image = Image.fromarray(indices, mode="P")
        image.putpalette(
            [12, 34, 56, 78, 90, 123, 210, 180, 150] + [0] * (768 - 9)
        )

    cover_path = tmp_path / f"cover_{image_mode}.png"
    output_path = tmp_path / f"stego_{image_mode}.png"
    image.save(cover_path)
    with Image.open(cover_path) as saved_image:
        expected_rgb = np.asarray(saved_image.convert("RGB"))

    rgb = load_rgb_array(cover_path)
    np.testing.assert_array_equal(rgb, expected_rgb)
    payload = f"round-trip from {image_mode} image".encode()
    embed_message(
        cover_path,
        output_path,
        payload,
        mode=0x01,
        k=2,
        nonce=b"123456789012",
        extra_data=b"0123456789abcdef",
    )

    assert extract_message_from_image(output_path)[0] == payload
