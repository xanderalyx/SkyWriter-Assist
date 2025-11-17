import joblib
import numpy as np
import json
from pathlib import Path
from sklearn.model_selection import train_test_split 
from sklearn.metrics import accuracy_score

# === CRITICAL IMPORTS ===
# 1. Feature logic (must be in features.py)
from features import extract_features 
# 2. The BLE capture function (must be in ble_capture_module.py)
from ble_capture_module import capture_new_gesture 
# ========================

# === Configuration ===
# Enabled confidence threshold for real-time use.
# % 99 confidence required to show both 2 top contenders
# NO TIME TO CHANGE CODE
CONFIDENCE_THRESHOLD = 0.99 

# === Paths ===
MODEL_DIR = Path("models")
# Using the best-performing model (SVC_C10) 
# *** CHANGE this to test other models ***
MODEL_PATH = MODEL_DIR / "SVC_BEST_SVC_C100_gesture_model.pkl" 
SCALER_PATH = MODEL_DIR / "scaler.pkl"
# Re-adding DATA_PATH for the required run_validation_test function 
DATA_PATH = Path("data/merged_sitting_lying.json") # *** Make sure this is the SAME as train_from_merged.py ***

model = None
scaler = None

# === Load Model and Scaler ===
try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print(f"✅ Loaded model: {MODEL_PATH.name}")
    print(f"✅ Loaded scaler: {SCALER_PATH.name}")
except Exception as e:
    # NOTE: If this fails, check your training script's save path/name
    print(f"FATAL ERROR: Could not load files. Ensure training completed. {e}")
    exit()


def run_validation_test(data_path: Path):
    """Diagnostic check to confirm model integrity against the test set."""
    print("\n--- Running Validation Test on Original Data ---")
    
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)["data"]
    except FileNotFoundError:
        print(f"Validation failed: Data file not found at {data_path}")
        return

    # Feature extraction (must be same as training)
    X, y = [], []
    for letter, content in data.items():
        for cap in content["captures"]:
            x = np.array([cap["x"], cap["y"], cap["z"]]).T
            feats = extract_features(x)
            X.append(feats)
            y.append(letter)

    X = np.array(X)
    y = np.array(y)
    
    # Use SAME random_state=42 and test_size=0.2 as training
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # Transform test data using the loaded scaler
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    test_accuracy = accuracy_score(y_test, y_pred)

    print("-" * 50)
    print(f"Deployment integrity checked on {len(X_test)} test samples.")
    print(f"MODEL ACCURACY ON TEST SET: {test_accuracy * 100:.3f}%")
    print("-" * 50)


def predict_gesture(raw_gesture_data: np.ndarray):
    """
    Processes raw (N, 3) gesture data and predicts the letter and confidence.
    
    NOTE: This version always returns the top prediction, regardless of confidence.
          The display logic (UNSURE vs. CONFIDENT) is handled in __main__.
          
    Returns: A tuple (top_prediction, top_confidences) where top_confidences 
             is a list of (label, confidence) for the top 3 results.
    """
    
    if raw_gesture_data.shape[0] == 0:
        return "NO_DATA", []

    # 1. Feature Extraction and Reshaping (1, F)
    try:
        features = extract_features(raw_gesture_data)
        X_new = features.reshape(1, -1) 
    except Exception as e:
        print(f"Error during feature extraction: {e}")
        return "FEATURE_ERROR", []

    # 2. Scaling: Use the LOADED scaler
    X_new_scaled = scaler.transform(X_new)
    
    # 3. Prediction and Probability
    # Get the predicted label (the one with the highest probability)
    prediction = model.predict(X_new_scaled)[0] 
    
    top_confidences = []

    # Check for probability support and extract top predictions
    if hasattr(model, 'predict_proba'):
        probabilities = model.predict_proba(X_new_scaled)[0]
        
        # Get class labels from the model
        classes = model.classes_
        
        # Combine probabilities and classes, then sort by probability (descending)
        sorted_indices = np.argsort(probabilities)[::-1]
        
        # Extract top N predictions (up to 3)
        for i in range(min(3, len(classes))):
            label = classes[sorted_indices[i]]
            conf = probabilities[sorted_indices[i]]
            top_confidences.append((label, conf))
        
    # Return the highest probability prediction and the list of top confidences
    return prediction, top_confidences


if __name__ == "__main__":
    
    # Run a quick check on known test data
    run_validation_test(DATA_PATH)
    
    print("\n\n" + "="*50)
    print("             --- SkyWriter Assist ---")
    print(" --- The Future of Writing Assistive Technology ---")
    print("="*50)

    while True:
        try:
            print("\nWaiting for user to press ENTER to start a new live gesture capture...")
            input()
            
            # 1. CAPTURE INPUT (Calls the BLE function)
            raw_data = capture_new_gesture() 
            
            if raw_data is None:
                print("Capture failed or timed out, please retry.")
                continue 
            
            print(f"\n[INPUT RECEIVED] Gesture captured with {raw_data.shape[0]} points.")
            
            # 2. PREDICT
            # predicted_letter is now always the highest confidence label
            predicted_letter, top_confidences = predict_gesture(raw_data)
            
            # Extract max confidence for decision making (0.0 if empty)
            max_confidence = top_confidences[0][1] if top_confidences else 0.0

            # 3. DISPLAY RESULTS TO TERMINAL
            print("\n" + "#" * 55)

            if predicted_letter in ["NO_DATA", "FEATURE_ERROR"]:
                # Fallback for errors or NO_DATA
                print(f"STATUS: {predicted_letter}")
            
            elif max_confidence >= CONFIDENCE_THRESHOLD:
                # Case 1: High Confidence (show the predicted letter and its confidence)
                print(f"PREDICTED LETTER: {predicted_letter}") 
                print(f"CONFIDENCE:       {max_confidence * 100:.2f}%")
            
            elif max_confidence < CONFIDENCE_THRESHOLD and len(top_confidences) >= 2:
                # Case 2: Low Confidence (show top prediction + warning + top 2 candidates)
                # This implements the user's requested display pattern logic
                print(f"PREDICTED LETTER: {predicted_letter}")
                print("\nTop competing candidates are:")
                
                # Show top 2 predictions
                for label, conf in top_confidences[:2]:
                    print(f"  - {label:<5}: {conf * 100:.2f}%")
            
            else:
                # General fallback (e.g., if predict_proba fails to return enough candidates)
                print(f"PREDICTED LETTER: {predicted_letter}")
                print("CONFIDENCE: UNKNOWN (Failed to determine probability breakdown)")


            print("#" * 55)
            
        except KeyboardInterrupt:
            print("\nExiting predictor.")
            break
        except Exception as e:
            print(f"An unexpected error occurred during the loop: {e}")
            break
