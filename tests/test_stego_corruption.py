from pathlib import Path
from collections.abc import Callable

import numpy as np
import pytest

from container import pack_header
from stego_module import (
    bytes_to_bits_msb,
    embed_kbits_lsb,
    embed_message,
    extract_message_from_image,
    extract_stego_payload,
    load_rgb_array,
    save_rgb_png,
)


def _create_valid_stego(
    tmp_path: Path,
    create_cover: Callable[[int, int, str], Path],
    name: str = "valid.png",
) -> Path:
    cover_path = create_cover(80, 80)
    return embed_message(
        cover_path,
        tmp_path / name,
        b"payload for corruption checks",
        mode=0x01,
        k=2,
        nonce=b"123456789012",
        extra_data=b"0123456789abcdef",
    )


@pytest.mark.parametrize("channel_index", [0, 4 * 8 + 7, 5 * 8 + 7])
def test_corrupt_magic_version_or_mode_is_rejected(
    tmp_path: Path, create_cover: Callable[[int, int, str], Path], channel_index: int
) -> None:
    stego_path = _create_valid_stego(tmp_path, create_cover)
    rgb = load_rgb_array(stego_path)
    flat = rgb.reshape(-1)
    flat[channel_index] ^= 1
    corrupted_path = save_rgb_png(rgb, tmp_path / f"corrupted_{channel_index}.png")

    with pytest.raises(ValueError):
        extract_message_from_image(corrupted_path)


def test_truncated_header_is_rejected(
    create_cover: Callable[[int, int, str], Path],
) -> None:
    channels = load_rgb_array(create_cover(80, 80)).reshape(-1)[:20]

    with pytest.raises(ValueError):
        extract_stego_payload(channels)


def test_truncated_payload_is_rejected(
    tmp_path: Path, create_cover: Callable[[int, int, str], Path]
) -> None:
    stego_path = _create_valid_stego(tmp_path, create_cover)
    channels = load_rgb_array(stego_path).reshape(-1)
    header_channels = 40 * 8
    payload_channels = (len(b"payload for corruption checks") * 8 + 1) // 2
    truncated_channels = channels[: header_channels + payload_channels - 1]

    with pytest.raises(ValueError, match="Insufficient channels"):
        extract_stego_payload(truncated_channels)


def test_ct_len_larger_than_remaining_capacity_is_rejected(
    tmp_path: Path, create_cover: Callable[[int, int, str], Path]
) -> None:
    cover = load_rgb_array(create_cover(80, 80))
    channels = cover.reshape(-1).copy()
    header = pack_header(
        mode=0x01,
        k=1,
        nonce=b"123456789012",
        ct_len=10_000_000,
        extra_data=b"0123456789abcdef",
    )
    embed_kbits_lsb(channels, bytes_to_bits_msb(header), k=1, inplace=True)
    stego_path = save_rgb_png(channels.reshape(cover.shape), tmp_path / "oversized_length.png")

    with pytest.raises(ValueError, match="Insufficient channels"):
        extract_message_from_image(stego_path)
