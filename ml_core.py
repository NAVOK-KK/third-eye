import cv2
import numpy as np
import os
from sklearn.decomposition import PCA
from sklearn.svm import SVC
import joblib 

class ForensicMLSystem:
    def __init__(self, db_path='database'):
        self.db_path = db_path
        # Using PCA for Eigenface Feature Extraction (Dimensionality Reduction)
        self.pca = PCA(n_components=0.95)
        # Using SVM for Classification (Machine Learning)
        self.svm = SVC(kernel='linear', probability=True)
        self.is_trained = False
        self.target_size = (100, 100) # Normalized size for faces
        self.classes = []

    def generate_sketch(self, image_path, save_path=None):
        """ Convert photo to forensic sketch """
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        # Resize image to a maximum dimension to prevent performance issues
        max_dim = 800
        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
            
        # 1. Convert to Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 2. Invert Grayscale Image
        inverted = cv2.bitwise_not(gray)
        
        # 3. Blur the inverted image (Gaussian Blur simulates pencil strokes)
        blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
        
        # 4. Invert the blurred image
        inverted_blur = cv2.bitwise_not(blurred)
        
        # 5. Create pencil sketch by dividing grayscale by inverted blur
        sketch = cv2.divide(gray, inverted_blur, scale=256.0)
        
        if save_path:
            cv2.imwrite(save_path, sketch)
            
        return sketch

    def prepare_data(self):
        """ Train the ML model (PCA + SVM) on the database """
        faces = []
        labels = []
        self.classes = []

        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
            return False

        files = [f for f in os.listdir(self.db_path) if f.endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('_')]
        
        if len(files) < 2:
            return False # Need at least 2 distinct subjects to train

        for idx, filename in enumerate(files):
            filepath = os.path.join(self.db_path, filename)
            # Use filename without extension as label
            name = os.path.splitext(filename)[0]
            self.classes.append(name)

            # 1. Add Original Photo
            img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
            img_resized = cv2.resize(img, self.target_size)
            faces.append(img_resized.flatten())
            labels.append(idx)

            # 2. Add Synthetic Sketch (Cross-Modality Learning)
            sketch_img = self.generate_sketch(filepath)
            sketch_resized = cv2.resize(sketch_img, self.target_size)
            faces.append(sketch_resized.flatten())
            labels.append(idx)

            # 3. Add Flipped versions for Data Augmentation
            faces.append(cv2.flip(img_resized, 1).flatten())
            labels.append(idx)
            faces.append(cv2.flip(sketch_resized, 1).flatten())
            labels.append(idx)

        X = np.array(faces)
        y = np.array(labels)

        # Train PCA (Feature Extraction)
        X_pca = self.pca.fit_transform(X)
        
        # Train SVM (Classifier)
        self.svm.fit(X_pca, y)
        self.is_trained = True
        return True

    def recognize(self, query_img_path):
        """ Recognize a query image (sketch or photo) """
        if not self.is_trained:
            success = self.prepare_data()
            if not success:
                return {"error": "Not enough data to train AI model. Please add at least 2 suspect photos to the database folder."}

        # Load query image as grayscale
        img = cv2.imread(query_img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {"error": "Invalid uploaded image format"}
        
        # Normalize size
        img_resized = cv2.resize(img, self.target_size).flatten().reshape(1, -1)
        
        # Extract features
        img_pca = self.pca.transform(img_resized)
        
        # Predict Class
        prediction = self.svm.predict(img_pca)[0]
        # Predict Probabilities
        probabilities = self.svm.predict_proba(img_pca)[0]
        
        confidence = probabilities[prediction] * 100
        match_name = self.classes[prediction]
        
        # Retrieve the original matched image path
        match_img_path = None
        for ext in ['.png', '.jpg', '.jpeg']:
            test_path = os.path.join(self.db_path, f"{match_name}{ext}")
            if os.path.exists(test_path):
                match_img_path = f"{match_name}{ext}"
                break

        return {
            "match": match_name,
            "confidence": round(confidence, 2),
            "match_image": match_img_path,
            "is_trained": True
        }
