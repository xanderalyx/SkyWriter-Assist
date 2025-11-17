import numpy as np
from scipy.stats import median_abs_deviation as mad
from scipy.signal import find_peaks

# --- Configuration for Active Time Fraction ---
# The threshold should be determined experimentally, often 0.2g to 0.5g
ACTIVITY_THRESHOLD_G = 0.5 # Example: 0.3g (300 mg)
# ---------------------------------------------

def extract_features(window: np.ndarray) -> np.ndarray:
    """
    Computes the 42 required time-domain features from an IMU window (X, Y, Z).
    
    This version replaces the redundant per-axis Mean feature (near zero after
    compensation) with Max Absolute Jerk, to better distinguish between sharp
    (S, B) and smooth (D) gestures.
    
    Args:
        window: An array of shape (N, 3) containing [X, Y, Z] acceleration data (in Gs).
        
    Returns:
        A 1D feature vector of length 42.
    """
    feats = []

    # --- 1. Gravity Compensation ---
    # The mean of the signal window approximates the static gravity vector.
    gravity_vector = np.mean(window, axis=0) 
    window_compensated = window - gravity_vector
    
    # 2. Orientation-Independent Signal: Magnitude (Calculated from RAW signal)
    # The magnitude still includes the 1G component, useful for Signal Energy.
    magnitude = np.sqrt(np.sum(window**2, axis=1))

    # --- A. Per-Axis Statistics (33 Features - Uses COMPENSATED Signal) ---
    for axis in range(3):
        # *** USING The GRAVITY-COMPENSATED SIGNAL HERE ***
        x = window_compensated[:, axis]
        
        # --- Feature Swaps for Robustness ---        
        # ADDED: Jerk features (derivative of the difference)
        # Jerk is the second difference (rate of change of acceleration)
        diff_x = np.diff(x)
        jerk_x = np.diff(diff_x)
        # 1. Max Absolute Jerk (Helps distinguish smooth vs sharp motions)
        feats.append(np.max(np.abs(jerk_x))) 
        
        # Standard Deviation (variability/spread)
        feats.append(np.std(x))
        
        # Variance
        feats.append(np.var(x))
        
        # Min, Max, Peak-to-Peak Range (overall scale)
        feats.append(np.min(x))
        feats.append(np.max(x))
        feats.append(np.ptp(x))
        
        # RMS and Signal Energy
        feats.append(np.sqrt(np.mean(x**2))) # RMS
        feats.append(np.sum(x**2))           # Energy
        
        # First-Difference Statistics (sharpness/jerk)
        feats.append(np.mean(np.abs(diff_x))) # Mean Absolute Difference (|Δ|)
        feats.append(np.max(np.abs(diff_x)))  # Max Absolute Difference (|Δ|)
        
        # Zero-crossing Rate (directional reversals)
        # Uses the compensated signal which is now centered around zero.
        zero_crossings = np.sum((x[:-1] * x[1:]) < 0)
        feats.append(zero_crossings)
        
        # Total per-axis features: 11 features/axis * 3 axes = 33

    # --- B. Magnitude Statistics (7 Features - Uses RAW Magnitude Signal) ---
    feats.append(np.mean(magnitude))
    feats.append(np.median(magnitude))
    feats.append(np.std(magnitude))
    feats.append(np.var(magnitude))
    feats.append(np.ptp(magnitude))
    feats.append(np.sqrt(np.mean(magnitude**2))) # RMS of Magnitude
    feats.append(np.sum(magnitude**2))           # Energy of Magnitude

    # --- C. Global & Composite Features (2 Features) ---

    # Dominant-axis Ratio (compares variability across COMPENSATED axes)
    stds_compensated = [np.std(window_compensated[:, i]) for i in range(3)]
    # Add a small epsilon (1e-6) to prevent division by zero
    feats.append(max(stds_compensated) / (min(stds_compensated) + 1e-6))
    
    # Active Time Fraction (proportion of time above a threshold)
    active_samples = np.sum(magnitude > ACTIVITY_THRESHOLD_G)
    active_time_fraction = active_samples / len(magnitude)
    feats.append(active_time_fraction)
    
    # Final feature count remains 42
    return np.array(feats)
