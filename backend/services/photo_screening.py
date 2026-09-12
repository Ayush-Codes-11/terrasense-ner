"""Conservative OpenCV photo screening adapter.

This detects possible line-like crack candidates and image quality only. It
does not verify a landslide and must not be described as an AI diagnosis.
"""
from __future__ import annotations

from typing import Any


def screen_image_bytes(image_bytes: bytes) -> dict[str, Any]:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV screening requires backend/requirements-local.txt"
        ) from exc

    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return {
            "status": "REJECTED_INVALID_IMAGE",
            "screening_type": "OPENCV_SCREENING_ONLY",
            "candidate_detected": False,
        }
    contrast = float(image.std())
    edges = cv2.Canny(image, 80, 160)
    edge_ratio = float(np.count_nonzero(edges)) / float(edges.size)
    return {
        "status": "SCREENED",
        "screening_type": "OPENCV_SCREENING_ONLY",
        "candidate_detected": edge_ratio >= 0.08 and contrast >= 25.0,
        "image_width": int(image.shape[1]),
        "image_height": int(image.shape[0]),
        "contrast_stddev": round(contrast, 3),
        "edge_ratio": round(edge_ratio, 5),
        "requires_human_verification": True,
        "model_status": "NO_TRAINED_VISION_MODEL",
    }
