"""
sketch_service.py — Pipeline 1: Eyewitness Description → Forensic Composite Sketch

Generates an anatomically-proportioned, greyscale forensic composite sketch
from structured eyewitness attribute inputs using OpenCV drawing primitives.
Part of the THIRD EYE AI Forensic System.
"""

import cv2
import numpy as np
import os


# ──────────────────────────────────────────────────────────────────────────────
# Canvas constants
# ──────────────────────────────────────────────────────────────────────────────
W, H = 512, 640          # canvas width x height
CX, CY = W // 2, H // 2 # centre of face

# Greyscale palette
BG       = 255   # white background
FACE_COL = 230   # light skin base
SHADOW   = 160   # shading/shadow
DARK     = 60    # dark lines / pupils / hair
MID      = 110   # mid tones


def _blank() -> np.ndarray:
    return np.full((H, W), BG, dtype=np.uint8)


def _apply_skin_tone(canvas: np.ndarray, tone: str) -> np.ndarray:
    """Overlay a greyscale skin-tone wash over the face ellipse."""
    tone_map = {
        'fair': 240, 'light': 230, 'medium': 200,
        'olive': 185, 'tan': 175, 'dark': 140, 'deep': 110
    }
    tone_val = tone_map.get(tone.lower().strip(), 220)

    mask = np.zeros((H, W), dtype=np.uint8)
    cv2.ellipse(mask, (CX, CY + 20), (130, 160), 0, 0, 360, 255, -1)
    canvas = canvas.copy()
    canvas[mask == 255] = tone_val
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Face shape
# ──────────────────────────────────────────────────────────────────────────────
FACE_SHAPES = {
    'oval':      (125, 160),
    'round':     (145, 145),
    'square':    (140, 150),
    'heart':     (140, 155),
    'oblong':    (110, 175),
    'diamond':   (120, 158),
    'rectangle': (135, 165),
}

def _draw_face(canvas: np.ndarray, shape: str) -> np.ndarray:
    rx, ry = FACE_SHAPES.get(shape.lower().strip(), (125, 160))
    # Main face ellipse
    cv2.ellipse(canvas, (CX, CY + 20), (rx, ry), 0, 0, 360, SHADOW, 2)
    # Jawline accent for square/rectangle
    if shape.lower() in ('square', 'rectangle'):
        cv2.line(canvas, (CX - rx, CY + 80), (CX - rx, CY + 20 + ry - 20), SHADOW, 2)
        cv2.line(canvas, (CX + rx, CY + 80), (CX + rx, CY + 20 + ry - 20), SHADOW, 2)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Eyes
# ──────────────────────────────────────────────────────────────────────────────
EYE_LEFT  = (CX - 55, CY - 25)
EYE_RIGHT = (CX + 55, CY - 25)

EYE_SIZES = {
    'small':  (18, 8),
    'medium': (24, 10),
    'large':  (30, 13),
    'narrow': (26, 7),
    'wide':   (32, 12),
    'almond': (28, 9),
}

def _draw_eyes(canvas: np.ndarray, desc: str) -> np.ndarray:
    rx, ry = EYE_SIZES.get(desc.lower().split()[0] if desc else 'medium', (24, 10))
    for cx, cy in [EYE_LEFT, EYE_RIGHT]:
        # Eye outline
        cv2.ellipse(canvas, (cx, cy), (rx, ry), 0, 0, 360, DARK, 1)
        # Iris
        cv2.circle(canvas, (cx, cy), int(ry * 0.85), SHADOW, 1)
        # Pupil
        cv2.circle(canvas, (cx, cy), int(ry * 0.45), DARK, -1)
        # Highlight
        cv2.circle(canvas, (cx - 3, cy - 3), 2, BG, -1)
        # Upper lash line
        cv2.ellipse(canvas, (cx, cy), (rx, ry), 0, 200, 340, DARK, 2)
        # Eyebrow (default medium arch)
        bx1, bx2 = cx - rx - 5, cx + rx + 5
        by = cy - ry - 10
        pts = np.array([[bx1, by + 4], [cx, by - 3], [bx2, by + 4]], np.int32)
        cv2.polylines(canvas, [pts], False, DARK, 2)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Eyebrows
# ──────────────────────────────────────────────────────────────────────────────
def _draw_eyebrows(canvas: np.ndarray, desc: str) -> np.ndarray:
    """
    Redraw / refine brows based on description.
    Called AFTER _draw_eyes so we override the default brow.
    """
    desc_l = (desc or '').lower()
    thickness = 3 if 'thick' in desc_l or 'bushy' in desc_l else 2
    arch = -6 if 'arched' in desc_l else (-3 if 'flat' in desc_l else -4)

    for cx, cy in [EYE_LEFT, EYE_RIGHT]:
        rx = 28
        ry_eye = 10
        bx1, bx2 = cx - rx - 5, cx + rx + 5
        by = cy - ry_eye - 10
        pts = np.array([[bx1, by + 4], [cx, by + arch], [bx2, by + 4]], np.int32)
        # Erase old brow area first
        cv2.polylines(canvas, [pts], False, FACE_COL, 4)
        cv2.polylines(canvas, [pts], False, DARK, thickness)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Nose
# ──────────────────────────────────────────────────────────────────────────────
NOSE_Y_TOP = CY + 10
NOSE_Y_BOT = CY + 55

NOSE_TYPES = {
    'narrow':  30, 'wide': 55, 'broad': 58,
    'pointed': 28, 'flat': 52, 'bulbous': 50,
    'medium':  40, 'small': 34, 'large': 50,
    'roman':   38, 'button': 32, 'straight': 38,
}

def _draw_nose(canvas: np.ndarray, desc: str) -> np.ndarray:
    key = (desc or '').lower().split()[0]
    nw = NOSE_TYPES.get(key, 40)
    half = nw // 2

    # Bridge line
    cv2.line(canvas, (CX - 5, NOSE_Y_TOP), (CX - 5, NOSE_Y_BOT - 10), MID, 1)
    cv2.line(canvas, (CX + 5, NOSE_Y_TOP), (CX + 5, NOSE_Y_BOT - 10), MID, 1)

    # Nostrils
    cv2.ellipse(canvas, (CX - half + 8, NOSE_Y_BOT), (12, 8), 15, 0, 200, SHADOW, 1)
    cv2.ellipse(canvas, (CX + half - 8, NOSE_Y_BOT), (12, 8), -15, -20, 180, SHADOW, 1)

    # Nose tip
    cv2.ellipse(canvas, (CX, NOSE_Y_BOT - 5), (half - 4, 10), 0, 0, 360, MID, 1)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Lips / Mouth
# ──────────────────────────────────────────────────────────────────────────────
MOUTH_Y = CY + 90

MOUTH_WIDTHS = {
    'thin':    35, 'medium': 45, 'full': 55,
    'thick':   55, 'small':  35, 'large': 58,
    'wide':    60, 'narrow': 32, 'pouty': 50,
}

def _draw_lips(canvas: np.ndarray, desc: str) -> np.ndarray:
    key = (desc or '').lower().split()[0]
    mw = MOUTH_WIDTHS.get(key, 45)
    half = mw // 2
    upper_h = 8 if 'full' in (desc or '').lower() or 'thick' in (desc or '').lower() else 6
    lower_h = upper_h + 3

    # Upper lip
    cv2.ellipse(canvas, (CX - half // 2, MOUTH_Y), (half // 2, upper_h), 0, 180, 360, DARK, 1)
    cv2.ellipse(canvas, (CX + half // 2, MOUTH_Y), (half // 2, upper_h), 0, 180, 360, DARK, 1)
    # Cupid's bow
    cv2.line(canvas, (CX - half, MOUTH_Y), (CX - half // 2, MOUTH_Y - upper_h + 1), DARK, 1)
    cv2.line(canvas, (CX + half, MOUTH_Y), (CX + half // 2, MOUTH_Y - upper_h + 1), DARK, 1)

    # Lower lip
    cv2.ellipse(canvas, (CX, MOUTH_Y + 2), (half, lower_h), 0, 0, 180, DARK, 1)

    # Lip line (philtrum base)
    cv2.line(canvas, (CX - half, MOUTH_Y), (CX + half, MOUTH_Y), MID, 1)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Hair
# ──────────────────────────────────────────────────────────────────────────────
def _draw_hair(canvas: np.ndarray, desc: str, face_rx: int = 125, face_ry: int = 160) -> np.ndarray:
    desc_l = (desc or '').lower()
    top_y = CY + 20 - face_ry  # top of face ellipse

    if 'bald' in desc_l:
        return canvas

    if 'short' in desc_l or 'crew' in desc_l or 'buzz' in desc_l:
        # Short close-cropped hair cap
        cv2.ellipse(canvas, (CX, top_y + 20), (face_rx + 10, 50), 0, 180, 360, DARK, -1)
        cv2.ellipse(canvas, (CX, top_y + 20), (face_rx + 10, 50), 0, 180, 360, SHADOW, 1)

    elif 'wavy' in desc_l or 'curly' in desc_l:
        # Wavy / curly — draw bumpy hair cap
        pts = []
        for angle in range(180, 361, 5):
            rad = np.radians(angle)
            wave = 10 * np.sin(np.radians(angle * 4))
            x = int(CX + (face_rx + 20 + wave) * np.cos(rad))
            y = int((top_y + 10) + (70 + wave) * np.sin(rad))
            pts.append([x, y])
        cv2.fillPoly(canvas, [np.array(pts, np.int32)], DARK)
        cv2.polylines(canvas, [np.array(pts, np.int32)], False, SHADOW, 1)

    elif 'long' in desc_l:
        # Long straight — side curtains + top
        cv2.ellipse(canvas, (CX, top_y + 15), (face_rx + 18, 55), 0, 180, 360, DARK, -1)
        # Side strands
        cv2.rectangle(canvas, (CX - face_rx - 18, top_y + 15), (CX - face_rx - 2, CY + 20 + 80), DARK, -1)
        cv2.rectangle(canvas, (CX + face_rx + 2,  top_y + 15), (CX + face_rx + 18, CY + 20 + 80), DARK, -1)
        # Strand texture
        for x_off in range(-face_rx - 15, face_rx + 16, 8):
            cv2.line(canvas, (CX + x_off, top_y + 15), (CX + x_off, CY + 20 + 75), SHADOW, 1)

    else:  # default: medium straight hair
        cv2.ellipse(canvas, (CX, top_y + 18), (face_rx + 14, 52), 0, 180, 360, DARK, -1)
        # Hairline texture
        for angle in range(185, 355, 12):
            rad = np.radians(angle)
            x = int(CX + (face_rx + 14) * np.cos(rad))
            y = int(top_y + 18 + 52 * np.sin(rad))
            cv2.line(canvas, (CX, top_y - 20), (x, y), SHADOW, 1)

    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Facial hair
# ──────────────────────────────────────────────────────────────────────────────
def _draw_facial_hair(canvas: np.ndarray, desc: str) -> np.ndarray:
    desc_l = (desc or '').lower()
    if not desc_l or 'none' in desc_l or 'clean' in desc_l:
        return canvas

    if 'beard' in desc_l or 'full' in desc_l:
        # Full beard — chin ellipse shaded
        cv2.ellipse(canvas, (CX, MOUTH_Y + 50), (75, 50), 0, 0, 180, SHADOW, -1)
        for i in range(-60, 61, 8):
            cv2.line(canvas, (CX + i, MOUTH_Y + 15), (CX + i, MOUTH_Y + 90), MID, 1)
    elif 'moustache' in desc_l or 'mustache' in desc_l:
        cv2.ellipse(canvas, (CX, MOUTH_Y - 8), (32, 10), 0, 0, 180, SHADOW, -1)
    elif 'stubble' in desc_l or 'goatee' in desc_l:
        # Stubble dots below lips
        for dx in range(-45, 46, 6):
            for dy in range(0, 35, 6):
                cv2.circle(canvas, (CX + dx, MOUTH_Y + 10 + dy), 1, MID, -1)

    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Distinguishing marks
# ──────────────────────────────────────────────────────────────────────────────
def _draw_marks(canvas: np.ndarray, desc: str) -> np.ndarray:
    desc_l = (desc or '').lower()
    if 'scar' in desc_l:
        cv2.line(canvas, (CX + 50, CY - 10), (CX + 65, CY + 15), DARK, 2)
    if 'mole' in desc_l:
        cv2.circle(canvas, (CX - 30, CY + 30), 3, DARK, -1)
    if 'freckles' in desc_l or 'freckle' in desc_l:
        np.random.seed(42)
        for _ in range(18):
            fx = int(np.random.uniform(CX - 80, CX + 80))
            fy = int(np.random.uniform(CY - 40, CY + 60))
            cv2.circle(canvas, (fx, fy), 1, MID, -1)
    if 'tattoo' in desc_l:
        # Simple neck tattoo indicator
        cv2.putText(canvas, 'TAT', (CX + 80, CY + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.3, SHADOW, 1)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Accessories
# ──────────────────────────────────────────────────────────────────────────────
def _draw_accessories(canvas: np.ndarray, desc: str) -> np.ndarray:
    desc_l = (desc or '').lower()
    if 'glasses' in desc_l or 'spectacles' in desc_l:
        # Left lens
        cv2.rectangle(canvas, (EYE_LEFT[0] - 32, EYE_LEFT[1] - 16),
                      (EYE_LEFT[0] + 32, EYE_LEFT[1] + 16), DARK, 2)
        # Right lens
        cv2.rectangle(canvas, (EYE_RIGHT[0] - 32, EYE_RIGHT[1] - 16),
                      (EYE_RIGHT[0] + 32, EYE_RIGHT[1] + 16), DARK, 2)
        # Bridge
        cv2.line(canvas, (EYE_LEFT[0] + 32, EYE_LEFT[1]),
                 (EYE_RIGHT[0] - 32, EYE_RIGHT[1]), DARK, 2)
    if 'hat' in desc_l or 'cap' in desc_l:
        face_rx, face_ry = 125, 160
        top_y = CY + 20 - face_ry
        # Hat brim
        cv2.rectangle(canvas, (CX - face_rx - 20, top_y + 10),
                      (CX + face_rx + 20, top_y + 30), SHADOW, -1)
        cv2.rectangle(canvas, (CX - face_rx, top_y - 40),
                      (CX + face_rx, top_y + 12), DARK, -1)
    if 'earring' in desc_l:
        cv2.circle(canvas, (CX - 130, CY + 30), 5, SHADOW, -1)
        cv2.circle(canvas, (CX + 130, CY + 30), 5, SHADOW, -1)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Shading & finishing
# ──────────────────────────────────────────────────────────────────────────────
def _add_shading(canvas: np.ndarray) -> np.ndarray:
    """Add subtle bilateral-filter smoothing to give a pencil-sketch feel."""
    smoothed = cv2.bilateralFilter(canvas, 9, 75, 75)
    # Slight edge sharpening
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(smoothed, -1, kernel)
    return sharpened


def _add_age_lines(canvas: np.ndarray, age: int) -> np.ndarray:
    """Add fine wrinkle lines proportional to age."""
    if age < 30:
        return canvas
    # Forehead lines
    n_lines = min((age - 25) // 10, 4)
    for i in range(n_lines):
        y = CY - 80 + i * 12
        cv2.line(canvas, (CX - 60 + (i * 5), y), (CX + 60 - (i * 5), y), MID, 1)
    # Crow's feet
    if age > 40:
        for side in [-1, 1]:
            ex = EYE_LEFT[0] if side == -1 else EYE_RIGHT[0]
            ey = EYE_LEFT[1]
            for k in range(3):
                cv2.line(canvas, (ex + side * 28, ey - 5 + k * 5),
                         (ex + side * 45, ey - 8 + k * 6), MID, 1)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def generate_composite(attrs: dict, save_path: str | None = None) -> np.ndarray:
    """
    Generate a forensic composite sketch from a structured attribute dict.

    Expected keys (all optional, safe defaults applied):
        age, gender, face_shape, eyes, nose, lips, hair,
        facial_hair, skin_tone, marks, accessories

    Returns a greyscale numpy array (H × W).
    """
    age        = int(attrs.get('age') or 35)
    face_shape = attrs.get('face_shape') or 'oval'
    eyes_desc  = attrs.get('eyes')       or 'medium'
    nose_desc  = attrs.get('nose')       or 'medium'
    lips_desc  = attrs.get('lips')       or 'medium'
    hair_desc  = attrs.get('hair')       or 'medium'
    fhair_desc = attrs.get('facial_hair') or 'none'
    skin_tone  = attrs.get('skin_tone')  or 'medium'
    marks_desc = attrs.get('marks')      or ''
    acc_desc   = attrs.get('accessories') or ''
    brows_desc = attrs.get('eyebrows')   or 'medium'

    canvas = _blank()
    canvas = _apply_skin_tone(canvas, skin_tone)
    canvas = _draw_face(canvas, face_shape)
    canvas = _draw_hair(canvas, hair_desc,
                        *FACE_SHAPES.get(face_shape.lower().strip(), (125, 160)))
    canvas = _draw_eyes(canvas, eyes_desc)
    canvas = _draw_eyebrows(canvas, brows_desc)
    canvas = _draw_nose(canvas, nose_desc)
    canvas = _draw_lips(canvas, lips_desc)
    canvas = _draw_facial_hair(canvas, fhair_desc)
    canvas = _draw_marks(canvas, marks_desc)
    canvas = _draw_accessories(canvas, acc_desc)
    canvas = _add_age_lines(canvas, age)
    canvas = _add_shading(canvas)

    if save_path:
        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
        cv2.imwrite(save_path, canvas)

    return canvas
