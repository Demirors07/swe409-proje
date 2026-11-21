from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def create_cover(tmp_path: Path) -> Callable[[int, int, str], Path]:
    def create(width: int, height: int, mode: str = "RGB") -> Path:
        channels = {"RGB": 3, "RGBA": 4}.get(mode)
        if channels is None:
            raise ValueError(f"Unsupported test image mode: {mode}")

        seed = width * 1000 + height * 10 + channels
        pixels = np.random.default_rng(seed).integers(
            0, 256, size=(height, width, channels), dtype=np.uint8
        )
        path = tmp_path / f"cover_{width}x{height}_{mode}.png"
        Image.fromarray(pixels, mode=mode).save(path)
        return path

    return create
