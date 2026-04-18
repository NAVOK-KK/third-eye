"""
matcher_service.py — Pipeline 3: HOG-based CNN-style Cross-Modal Face Matcher

Extracts HOG (Histogram of Oriented Gradients) feature embeddings from face
images and performs cosine-similarity-based ranked matching against a criminal
database — replacing the basic PCA+SVM with a proper cross-modal system.

Confidence tiers follow the THIRD EYE specification:
    > 85 %  → HIGH CONFIDENCE MATCH
    70–85 % → POSSIBLE MATCH (requires human verification)
    < 70 %  → NO RELIABLE MATCH

Part of the THIRD EYE AI Forensic System.
"""

import cv2
import numpy as np
import os
from typing import Optional

# HOG descriptor configuration
_HOG = cv2.HOGDescriptor(
    _winSize   = (128, 128),
    _blockSize = (16, 16),
    _blockStride = (8, 8),
    _cellSize  = (8, 8),
    _nbins     = 9,
)

TARGET_SIZE = (128, 128)  # normalisation size fed into HOG


# ─────────────────────────────────────────────────────────────────────────────
# Embedding utilities
# ─────────────────────────────────────────────────────────────────────────────

def _load_gray(path: str) -> Optional[np.ndarray]:
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    return img


def _extract_embedding(gray: np.ndarray) -> np.ndarray:
    """Return a normalised HOG feature vector for a greyscale image."""
    resized = cv2.resize(gray, TARGET_SIZE)
    # Normalise pixel range
    eq = cv2.equalizeHist(resized)
    desc = _HOG.compute(eq).flatten()
    norm = np.linalg.norm(desc)
    return desc / norm if norm > 0 else desc


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity in [0, 1]."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


# ─────────────────────────────────────────────────────────────────────────────
# Confidence tier classifier
# ─────────────────────────────────────────────────────────────────────────────

def _classify_confidence(score_pct: float) -> str:
    if score_pct >= 85:
        return "HIGH CONFIDENCE"
    if score_pct >= 70:
        return "POSSIBLE MATCH"
    return "NO RELIABLE MATCH"


# ─────────────────────────────────────────────────────────────────────────────
# Database embedding builder
# ─────────────────────────────────────────────────────────────────────────────

class FaceMatcher:
    """
    Maintains an in-memory embedding index of all faces in the database folder.
    Call `build_index()` after adding new suspects.
    """

    def __init__(self, db_path: str = 'database'):
        self.db_path   = db_path
        self.index: list[dict] = []   # [{name, filename, embedding}]
        self.is_trained = False

    # ── Index building ──────────────────────────────────────────────────────

    def build_index(self) -> bool:
        """
        Scan db_path for image files, extract HOG embeddings for each.
        Also adds mirrored / sketch augmentations for cross-modal alignment.
        Returns True if at least 1 subject was indexed.
        """
        self.index = []
        exts = ('.png', '.jpg', '.jpeg')
        files = [f for f in os.listdir(self.db_path)
                 if f.lower().endswith(exts) and not f.startswith('_')]

        if not files:
            self.is_trained = False
            return False

        for filename in files:
            path  = os.path.join(self.db_path, filename)
            name  = os.path.splitext(filename)[0]
            gray  = _load_gray(path)
            if gray is None:
                continue

            emb = _extract_embedding(gray)
            self.index.append({'name': name, 'filename': filename, 'embedding': emb})

            # Add flipped augmentation for robustness
            flipped     = cv2.flip(gray, 1)
            emb_flipped = _extract_embedding(flipped)
            self.index.append({'name': name, 'filename': filename, 'embedding': emb_flipped})

            # Add sketch augmentation (cross-modal alignment)
            sketch_gray = self._to_sketch(gray)
            emb_sketch  = _extract_embedding(sketch_gray)
            self.index.append({'name': name, 'filename': filename, 'embedding': emb_sketch})

        self.is_trained = bool(self.index)
        return self.is_trained

    @staticmethod
    def _to_sketch(gray: np.ndarray) -> np.ndarray:
        """Quick pencil-sketch conversion for augmentation."""
        inv      = cv2.bitwise_not(gray)
        blurred  = cv2.GaussianBlur(inv, (21, 21), 0)
        inv_blur = cv2.bitwise_not(blurred)
        return cv2.divide(gray, inv_blur, scale=256.0)

    # ── Query matching ──────────────────────────────────────────────────────

    def match(self, query_path: str, top_k: int = 5) -> dict:
        """
        Match a query image against the indexed database.

        Returns:
            {
              "success": bool,
              "matches": [
                  {
                      "rank": 1,
                      "name": str,
                      "filename": str,
                      "score": float,       # 0–100
                      "tier": str           # HIGH CONFIDENCE / POSSIBLE / NO RELIABLE
                  }, ...
              ],
              "best_match": str,
              "best_score": float,
              "best_tier": str,
              "best_image": str             # filename for best match
            }
        """
        if not self.is_trained:
            built = self.build_index()
            if not built:
                return {
                    "success": False,
                    "error":   "Database is empty. Please add suspect photos via Admin panel."
                }

        gray = _load_gray(query_path)
        if gray is None:
            return {"success": False, "error": "Cannot read query image."}

        query_emb = _extract_embedding(gray)

        # Score every entry in index
        scored: dict[str, float] = {}   # name → best raw score
        name_to_file: dict[str, str] = {}

        for entry in self.index:
            sim  = _cosine_similarity(query_emb, entry['embedding'])
            name = entry['name']
            if name not in scored or sim > scored[name]:
                scored[name] = sim
                name_to_file[name] = entry['filename']

        # Sort descending
        ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:top_k]

        matches = []
        for rank, (name, raw_sim) in enumerate(ranked, start=1):
            score_pct = round(raw_sim * 100, 2)
            matches.append({
                "rank":     rank,
                "name":     name,
                "filename": name_to_file[name],
                "score":    score_pct,
                "tier":     _classify_confidence(score_pct),
            })

        best = matches[0] if matches else None
        return {
            "success":    True,
            "matches":    matches,
            "best_match": best["name"]     if best else None,
            "best_score": best["score"]    if best else 0,
            "best_tier":  best["tier"]     if best else "NO RELIABLE MATCH",
            "best_image": best["filename"] if best else None,
        }
