"""
enhance_service.py — Pipeline 2: Forensic Sketch → Photorealistic Enhancement

Uses a multi-stage OpenCV pipeline to enhance a raw greyscale pencil sketch
into a sharper, high-contrast, photo-quality forensic image.
Runs entirely offline — no deep learning models required.
Part of the THIRD EYE AI Forensic System.
"""

import cv2
import numpy as np


def enhance_sketch(image_input, save_path: str | None = None) -> np.ndarray:
    """
    Enhance a forensic sketch image into a higher-quality visual output.

    Args:
        image_input: Either a file path (str) or a numpy ndarray (greyscale or BGR).
        save_path:   Optional path to save the result as a PNG.

    Returns:
        Enhanced greyscale numpy array.
    """
    # ── Load ────────────────────────────────────────────────────────────────
    if isinstance(image_input, str):
        img = cv2.imread(image_input, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_input}")
    elif isinstance(image_input, np.ndarray):
        img = image_input.copy()
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        raise TypeError("image_input must be a file path or numpy array")

    # ── Stage 1 — Adaptive Histogram Equalisation (CLAHE) ───────────────────
    # Improve local contrast without blowing out highlights
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    stage1 = clahe.apply(img)

    # ── Stage 2 — Bilateral Filter (edge-preserving smoothing) ──────────────
    # Remove noise while keeping crisp facial edges
    stage2 = cv2.bilateralFilter(stage1, d=9, sigmaColor=80, sigmaSpace=80)

    # ── Stage 3 — Unsharp Mask (detail sharpening) ──────────────────────────
    # Subtract a slightly blurred copy to emphasise fine-detail edges
    blurred = cv2.GaussianBlur(stage2, (0, 0), sigmaX=2.5)
    stage3 = cv2.addWeighted(stage2, 1.6, blurred, -0.6, 0)

    # ── Stage 4 — Sketch Line Reinforcement ─────────────────────────────────
    # Standard pencil-sketch inversion trick to darken feature lines
    inverted   = cv2.bitwise_not(stage3)
    blur_inv   = cv2.GaussianBlur(inverted, (17, 17), 0)
    inv_blur   = cv2.bitwise_not(blur_inv)
    sketch     = cv2.divide(stage3, inv_blur, scale=256.0)

    # ── Stage 5 — Gamma correction (brighten mid-tones) ─────────────────────
    gamma = 1.3
    look_up = np.array([
        min(255, int((i / 255.0) ** (1.0 / gamma) * 255))
        for i in range(256)
    ], dtype=np.uint8)
    stage5 = cv2.LUT(sketch, look_up)

    # ── Stage 6 — Convert to 3-channel for detail enhance ───────────────────
    bgr = cv2.cvtColor(stage5, cv2.COLOR_GRAY2BGR)
    detail = cv2.detailEnhance(bgr, sigma_s=12, sigma_r=0.15)
    final = cv2.cvtColor(detail, cv2.COLOR_BGR2GRAY)

    # ── Stage 7 — Final mild sharpen ────────────────────────────────────────
    kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
    final  = cv2.filter2D(final, -1, kernel)
    final  = np.clip(final, 0, 255).astype(np.uint8)

    if save_path:
        import os
        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
        cv2.imwrite(save_path, final)

    return final
