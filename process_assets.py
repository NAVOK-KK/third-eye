import cv2
import glob
import numpy as np
import os

paths = glob.glob(r"c:\Users\Admin\Downloads\third-eye\third-eye\static\assets\*\*.png")
for p in paths:
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is None:
        continue
    
    # Convert to BGRA
    if len(img.shape) == 3 and img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        
    # Get grayscale representation to identify white background
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    
    # Smooth inverse threshold for Pencil sketches to make the white paper transparent
    # Everything dark (graphs) gets full opacity (255). 
    # Everything perfectly white (255) gets 0 opacity.
    # A multiplier makes the strokes stronger.
    alpha = np.clip(255 - (gray * 1.0), 0, 255).astype(np.uint8)
    
    # Optionally override RGB to raw graphite color to ensure it looks like a pure pencil stroke 
    # without weird lighting artifacts from DALL-E, matching standard IDenti-Kit forensic composite looks.
    img[:, :, 0] = 50 
    img[:, :, 1] = 50
    img[:, :, 2] = 50
    img[:, :, 3] = alpha

    cv2.imwrite(p, img)
    print(f"Processed: {os.path.basename(p)}")
