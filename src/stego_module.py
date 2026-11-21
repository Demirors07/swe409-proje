from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

import numpy as np
import numpy.typing as npt
from PIL import Image

from container import (
    HEADER_PREFIX_SIZE,
    calculate_max_payload_bytes,
    pack_header,
    unpack_header_prefix,
    unpack_header_rest,
)

UInt8Array: TypeAlias = npt.NDArray[np.uint8]
ImageInput: TypeAlias = str | Path | Image.Image | UInt8Array
_HEADER_SIZES = {0x01: 40, 0x02: 280}
_EXTRA_DATA_SIZES = {0x01: 16, 0x02: 256}
_BIT_SHIFTS = {
    k: np.arange(k - 1, -1, -1, dtype=np.uint8)
    for k in range(1, 9)
}


class CapacityError(ValueError):
    """Raised when a payload exceeds the image's available capacity."""


def _validate_k(k: int, *, wire_format: bool = False) -> None:
    max_k = 3 if wire_format else 8
    if not isinstance(k, int) or not 1 <= k <= max_k:
        raise ValueError(f"k must be between 1 and {max_k}, received: {k}")


def _as_flat_channels(channels: UInt8Array) -> UInt8Array:
    array = np.asarray(channels)
    if array.dtype != np.uint8:
        raise TypeError(f"Channels must have dtype uint8, received: {array.dtype}")
    if array.ndim != 1:
        raise ValueError(f"Channels must be a flat array, received shape: {array.shape}")
    return array


def load_rgb_array(image_path: str | Path) -> UInt8Array:
    """Load an image as an independent (height, width, 3) RGB uint8 array."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    with Image.open(path) as image:
        if "A" in image.getbands():
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            rgb_image = Image.alpha_composite(background, rgba).convert("RGB")
        else:
            rgb_image = image.convert("RGB")
        return np.asarray(rgb_image, dtype=np.uint8).copy()


def bytes_to_bits_msb(data: bytes) -> UInt8Array:
    """Convert bytes into a flat MSB-first array of zero and one bits."""
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if not data:
        return np.empty(0, dtype=np.uint8)
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder="big")


def bits_to_bytes_msb(bits: UInt8Array) -> bytes:
    """Convert a byte-aligned zero/one bit array into bytes."""
    bit_array = np.asarray(bits).reshape(-1)
    if not np.issubdtype(bit_array.dtype, np.integer) or np.any(
        (bit_array != 0) & (bit_array != 1)
    ):
        raise ValueError("bits must contain only zero and one")
    if bit_array.size % 8:
        raise ValueError(f"Bit count must be divisible by 8, received: {bit_array.size}")
    if not bit_array.size:
        return b""
    return np.packbits(bit_array.astype(np.uint8), bitorder="big").tobytes()


def embed_kbits_lsb(
    channels: UInt8Array,
    bits: UInt8Array,
    k: int,
    offset: int = 0,
    *,
    inplace: bool = False,
) -> tuple[UInt8Array, int]:
    """Embed a bit stream in channel LSBs, padding only its final partial group."""
    _validate_k(k)
    channel_array = _as_flat_channels(channels)
    bit_array = np.asarray(bits).reshape(-1)
    if not np.issubdtype(bit_array.dtype, np.integer) or np.any(
        (bit_array != 0) & (bit_array != 1)
    ):
        raise ValueError("bits must contain only zero and one")
    bit_array = bit_array.astype(np.uint8, copy=False)
    if not isinstance(offset, int) or offset < 0 or offset > channel_array.size:
        raise ValueError(f"offset must be between 0 and {channel_array.size}")
    if inplace and not channel_array.flags.writeable:
        raise ValueError("channels must be writeable when inplace=True")
    if not bit_array.size:
        return (channel_array if inplace else channel_array.copy()), offset

    channel_count = (bit_array.size + k - 1) // k
    end = offset + channel_count
    if end > channel_array.size:
        raise ValueError(
            f"Insufficient capacity: offset={offset}, required channels={channel_count}, "
            f"available channels={channel_array.size}."
        )

    padded_bits = np.pad(bit_array, (0, channel_count * k - bit_array.size))
    shifts = _BIT_SHIFTS[k]
    values = (padded_bits.reshape(channel_count, k) << shifts).sum(axis=1).astype(np.uint8)
    mask = np.uint8((1 << k) - 1)
    result = channel_array if inplace else channel_array.copy()
    result[offset:end] = (result[offset:end] & np.uint8(0xFF ^ mask)) | values
    return result, end


def extract_kbits_lsb(
    channels: UInt8Array,
    n_bits: int,
    k: int,
    offset: int = 0,
) -> tuple[UInt8Array, int]:
    """Extract exactly n_bits from channel LSB groups in MSB-first order."""
    _validate_k(k)
    channel_array = _as_flat_channels(channels)
    if not isinstance(n_bits, int) or n_bits < 0:
        raise ValueError(f"n_bits must be a non-negative integer, received: {n_bits}")
    if not isinstance(offset, int) or offset < 0 or offset > channel_array.size:
        raise ValueError(f"offset must be between 0 and {channel_array.size}")
    if n_bits == 0:
        return np.empty(0, dtype=np.uint8), offset

    channel_count = (n_bits + k - 1) // k
    end = offset + channel_count
    if end > channel_array.size:
        raise ValueError(
            f"Insufficient channels: offset={offset}, required={channel_count}, "
            f"available={channel_array.size}."
        )

    mask = np.uint8((1 << k) - 1)
    values = channel_array[offset:end] & mask
    bit_groups = ((values[:, None] >> _BIT_SHIFTS[k]) & 1).astype(np.uint8)
    return bit_groups.reshape(-1)[:n_bits], end


def ensure_capacity(
    width: int,
    height: int,
    header_bytes_len: int,
    k: int,
    required_payload_bytes: int,
) -> int:
    """Return payload capacity in bytes or raise CapacityError if it is too small."""
    _validate_k(k, wire_format=True)
    if width <= 0 or height <= 0 or header_bytes_len < 0 or required_payload_bytes < 0:
        raise ValueError("Image dimensions must be positive and lengths non-negative")
    available = calculate_max_payload_bytes(width, height, header_bytes_len, k)
    if required_payload_bytes > available:
        raise CapacityError(
            f"Payload does not fit: required={required_payload_bytes} bytes, "
            f"available={available} bytes (k={k}, header={header_bytes_len} bytes)."
        )
    return available


def _image_dimensions(image: ImageInput) -> tuple[int, int]:
    if isinstance(image, (str, Path)):
        rgb = load_rgb_array(image)
        return rgb.shape[1], rgb.shape[0]
    if isinstance(image, Image.Image):
        return image.size
    array = np.asarray(image)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"Image array must have shape (height, width, 3), received {array.shape}")
    return array.shape[1], array.shape[0]


def capacity(image: ImageInput, mode: int, k: int) -> int:
    """Return maximum payload bytes for the selected header mode and k value."""
    _validate_k(k, wire_format=True)
    try:
        header_size = _HEADER_SIZES[mode]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Unsupported mode: {mode}") from exc
    width, height = _image_dimensions(image)
    return calculate_max_payload_bytes(width, height, header_size, k)


def calculate_capacity(image_path: str | Path, bits_per_pixel: int = 1) -> int:
    """Return raw image capacity in bytes, excluding the steganography header."""
    if not isinstance(bits_per_pixel, int) or not 1 <= bits_per_pixel <= 8:
        raise ValueError("bits_per_pixel must be between 1 and 8")
    with Image.open(image_path) as image:
        width, height = image.size
    return width * height * 3 * bits_per_pixel // 8


def save_rgb_png(rgb_array: UInt8Array, output_path: str | Path) -> Path:
    """Save an (height, width, 3) RGB array losslessly as PNG."""
    array = np.asarray(rgb_array)
    if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"Expected an RGB uint8 array of shape (H, W, 3), received {array.shape}")
    target = Path(output_path)
    if target.suffix.lower() != ".png":
        target = target.with_suffix(".png")
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array).save(target, format="PNG", compress_level=6)
    return target


def embed_message(
    image_path: str | Path,
    output_path: str | Path,
    payload: bytes,
    mode: int,
    k: int,
    nonce: bytes,
    extra_data: bytes,
) -> Path:
    """Embed a fixed-format header and payload into an image and save as PNG."""
    _validate_k(k, wire_format=True)
    if mode not in _HEADER_SIZES:
        raise ValueError(f"Unsupported mode: {mode}")
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    if not isinstance(nonce, bytes) or len(nonce) != 12:
        raise ValueError("nonce must contain exactly 12 bytes")
    if not isinstance(extra_data, bytes) or len(extra_data) != _EXTRA_DATA_SIZES[mode]:
        raise ValueError(
            f"extra_data must contain exactly {_EXTRA_DATA_SIZES[mode]} bytes for mode {mode}"
        )

    rgb = load_rgb_array(image_path)
    height, width, _ = rgb.shape
    header = pack_header(mode, k, nonce, len(payload), extra_data)
    ensure_capacity(width, height, len(header), k, len(payload))

    flat = rgb.reshape(-1)
    flat, payload_offset = embed_kbits_lsb(flat, bytes_to_bits_msb(header), 1, inplace=True)
    flat, _ = embed_kbits_lsb(
        flat, bytes_to_bits_msb(payload), k, offset=payload_offset, inplace=True
    )
    return save_rgb_png(flat.reshape(height, width, 3), output_path)


def extract_stego_payload(channels: UInt8Array) -> tuple[bytes, int, int, bytes, bytes]:
    """Extract and validate the embedded header and payload from RGB channel data."""
    array = np.asarray(channels)
    if array.dtype != np.uint8:
        raise TypeError(f"Channels must have dtype uint8, received: {array.dtype}")
    if array.ndim == 3:
        if array.shape[2] != 3:
            raise ValueError(f"Expected an RGB array, received shape: {array.shape}")
        flat = array.reshape(-1)
    elif array.ndim == 1:
        flat = array
    else:
        raise ValueError(f"Expected a flat channel array or RGB array, received {array.shape}")

    prefix_bits, offset = extract_kbits_lsb(flat, HEADER_PREFIX_SIZE * 8, 1)
    _, _, mode, k, _ = unpack_header_prefix(bits_to_bytes_msb(prefix_bits))
    header_size = _HEADER_SIZES[mode]
    rest_bits, offset = extract_kbits_lsb(flat, (header_size - HEADER_PREFIX_SIZE) * 8, 1, offset)
    nonce, payload_size, extra_data, _ = unpack_header_rest(bits_to_bytes_msb(rest_bits), mode)
    payload_bits, _ = extract_kbits_lsb(flat, payload_size * 8, k, offset)
    return bits_to_bytes_msb(payload_bits), mode, k, nonce, extra_data


def extract_message_from_image(
    image: str | Path | UInt8Array,
) -> tuple[bytes, int, int, bytes, bytes]:
    """Extract a payload from an image path or an RGB uint8 array."""
    rgb = load_rgb_array(image) if isinstance(image, (str, Path)) else image
    return extract_stego_payload(rgb)
