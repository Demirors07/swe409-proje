import numpy as np
import pytest

from stego_module import embed_kbits_lsb, extract_kbits_lsb


@pytest.mark.parametrize("k", [1, 2, 3])
def test_bit_embedding_roundtrip_preserves_unused_channel_bits(k: int) -> None:
    channels = np.array(
        [0b10101010, 0b01010101, 0b11110000, 0b00111100,
         0b11001100, 0b00110011, 0b11111100, 0b00000011],
        dtype=np.uint8,
    )
    bits = np.array([1, 0, 1, 1, 0, 0, 1, 1], dtype=np.uint8)
    original_channels = channels.copy()

    embedded, end = embed_kbits_lsb(channels, bits, k=k)
    extracted, extract_end = extract_kbits_lsb(embedded, bits.size, k=k)

    np.testing.assert_array_equal(extracted, bits)
    assert end == extract_end == (bits.size + k - 1) // k
    assert np.array_equal(channels, original_channels)
    mask = np.uint8(0xFF ^ ((1 << k) - 1))
    np.testing.assert_array_equal(embedded[:end] & mask, channels[:end] & mask)
    np.testing.assert_array_equal(embedded[end:], channels[end:])


def test_bit_embedding_rejects_non_binary_input() -> None:
    with pytest.raises(ValueError, match="only zero and one"):
        embed_kbits_lsb(
            np.zeros(4, dtype=np.uint8),
            np.array([0, 2], dtype=np.uint8),
            k=1,
        )
