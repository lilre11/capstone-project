from typing import Tuple, Sequence

import numpy as np
from PIL import Image


def load_image(path: str) -> Image.Image:
    """Load an image from `path` and return an RGB PIL Image.

    Args:
        path: Path to an image file.

    Returns:
        PIL.Image.Image in RGB mode.
    """
    img = Image.open(path).convert("RGB")
    return img


def resize_and_crop(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
    """Resize `image` preserving aspect ratio then center-crop to `size`.

    Args:
        image: PIL Image.
        size: (width, height) target size.

    Returns:
        Resized and center-cropped PIL Image.
    """
    target_w, target_h = size
    src_w, src_h = image.size

    # Resize so the smaller side matches target, preserving aspect ratio
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(round(src_w * scale))
    new_h = int(round(src_h * scale))
    resized = image.resize((new_w, new_h), Image.BILINEAR)

    # Center crop
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    right = left + target_w
    bottom = top + target_h
    cropped = resized.crop((left, top, right, bottom))
    return cropped


def normalize(array: np.ndarray, mean: Sequence[float] = (0.485, 0.456, 0.406),
              std: Sequence[float] = (0.229, 0.224, 0.225)) -> np.ndarray:
    """Normalize a HWC uint8/float image array to float32 using mean/std.

    Args:
        array: numpy array with shape (H, W, C) and pixel range [0, 255] or [0,1].
        mean: per-channel mean.
        std: per-channel std.

    Returns:
        Normalized float32 numpy array in the same HWC layout.
    """
    arr = array.astype(np.float32)
    # If values are in 0-255 range, scale to 0-1
    if arr.max() > 2.0:
        arr = arr / 255.0
    mean = np.array(mean, dtype=np.float32).reshape(1, 1, 3)
    std = np.array(std, dtype=np.float32).reshape(1, 1, 3)
    return (arr - mean) / std


def to_tensor(array: np.ndarray) -> np.ndarray:
    """Convert HWC numpy array to CHW float32 tensor suitable for ONNX input.

    Args:
        array: numpy array with shape (H, W, C).

    Returns:
        numpy array with shape (1, C, H, W) and dtype float32.
    """
    if array.ndim != 3:
        raise ValueError("Input array must have shape HWC")
    chw = np.transpose(array, (2, 0, 1)).astype(np.float32)
    return np.expand_dims(chw, 0)


__all__ = ["load_image", "resize_and_crop", "normalize", "to_tensor"]
