from pathlib import Path
from collections.abc import Callable

import numpy as np
import pytest

from stego_module import CapacityError, capacity, embed_message, extract_message_from_image


@pytest.mark.parametrize("k", [1, 2, 3])
def test_payload_fills_exact_capacity(
    tmp_path: Path, create_cover: Callable[[int, int, str], Path], k: int
) -> None:
    cover_path = create_cover(96, 96)
    output_path = tmp_path / f"exact_capacity_k{k}.png"
    rng = np.random.default_rng(900 + k)
    payload_size = capacity(cover_path, mode=0x01, k=k)
    payload = rng.bytes(payload_size)

    saved_path = embed_message(
        cover_path,
        output_path,
        payload,
        mode=0x01,
        k=k,
        nonce=rng.bytes(12),
        extra_data=rng.bytes(16),
    )

    assert extract_message_from_image(saved_path)[0] == payload


@pytest.mark.parametrize("k", [1, 2, 3])
def test_payload_one_byte_over_capacity_raises_capacity_error(
    tmp_path: Path, create_cover: Callable[[int, int, str], Path], k: int
) -> None:
    cover_path = create_cover(96, 96)
    max_payload_bytes = capacity(cover_path, mode=0x01, k=k)
    required_payload_bytes = max_payload_bytes + 1

    with pytest.raises(CapacityError) as error:
        embed_message(
            cover_path,
            tmp_path / f"overflow_k{k}.png",
            b"x" * required_payload_bytes,
            mode=0x01,
            k=k,
            nonce=b"123456789012",
            extra_data=b"abcdefghijklmnop",
        )

    message = str(error.value)
    assert f"required={required_payload_bytes} bytes" in message
    assert f"available={max_payload_bytes} bytes" in message


def test_capacity_is_independent_of_rgb_or_rgba_storage(
    create_cover: Callable[[int, int, str], Path],
) -> None:
    rgb_path = create_cover(80, 56, "RGB")
    rgba_path = create_cover(80, 56, "RGBA")

    for mode in (0x01, 0x02):
        for k in (1, 2, 3):
            assert capacity(rgb_path, mode, k) == capacity(rgba_path, mode, k)


@pytest.mark.parametrize("k", [0, 4])
def test_embed_rejects_unsupported_wire_k(
    tmp_path: Path,
    create_cover: Callable[[int, int, str], Path],
    k: int,
) -> None:
    cover_path = create_cover(64, 64)

    with pytest.raises(ValueError, match="k must be between 1 and 3"):
        embed_message(
            cover_path,
            tmp_path / f"unsupported_k{k}.png",
            b"payload",
            mode=0x01,
            k=k,
            nonce=b"123456789012",
            extra_data=b"0123456789abcdef",
        )
