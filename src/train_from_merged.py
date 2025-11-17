import json
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, cross_val_score
import joblib

# NOTE: This requires the 'features.py' file with the 'extract_features' function defined.
from features import extract_features

# === Paths ===
DATA_PATH = Path("data/merged_sitting_lying.json") # *** Make sure the SAME as realtime_predictor.py ***
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

print(f"Loading dataset from: {DATA_PATH}")

# === Load and Process Data ===
try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)["data"]
except Exception as e:
    print(f"Error loading data: {e}. Please ensure data/pi_gesture_data_merged_all.json exists and is valid.")
    exit()

X, y = [], []

# Convert gestures to feature vectors
for letter, content in data.items():
    for cap in content["captures"]:
        if len(cap["x"]) > 0:
            x = np.array([cap["x"], cap["y"], cap["z"]]).T  # shape: (N,3)
            # Assuming extract_features returns a 1D feature vector
            feats = extract_features(x)
            X.append(feats)
            y.append(letter)

if not X:
    print("Error: No features extracted. Exiting.")
    exit()

X = np.array(X)
y = np.array(y)

# Define LABELS
LABELS = sorted(np.unique(y))

print(f"Total samples: {len(y)} | Features per sample: {X.shape[1]}")
print(f"Classes: {LABELS}")

# === Split and scale ===
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Save scaler once
joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
print(f"✅ Saved scaler in {MODEL_DIR}/scaler.pkl")


# --- Model Training and Evaluation Function ---
def train_eval_model(model, X_train, y_train, X_test, y_test, LABELS):
    """Trains, evaluates, and saves a model, including report and confusion matrix."""
    model_name = model.__class__.__name__
    
    # Check if we are testing a specific SVM C parameter
    if model_name == 'SVC' and hasattr(model, 'C'):
        model_name = f"SVC_C{int(model.C)}"

    print(f"\n" + "="*70)
    print(f"--- Training and Evaluating {model_name} ---")
    print("="*70)
    
    # 1. Train Model
    model.fit(X_train, y_train)
    
    # 2. Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, n_jobs=-1)
    print(f"CV accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # 3. Test set prediction & Accuracy
    y_pred = model.predict(X_test)
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc:.3f}")

    # 4. Classification Report to terminal
    print("\n" + "-"*30 + " Classification Report " + "-"*30)
    # Filter out warnings if classes exist in report but not in y_pred
    report = classification_report(y_test, y_pred, labels=LABELS, zero_division=0)
    print(report)

    # 5. Save Confusion Matrix as PNG Heatmap
    cm = confusion_matrix(y_test, y_pred, labels=LABELS)

    plt.rcParams.update({'font.size': 12})
    plt.figure(figsize=(10,8))
    sns.heatmap(
        cm, annot=True, fmt='d', cmap='YlGnBu',
        xticklabels=LABELS, yticklabels=LABELS, cbar=False,
        linewidths=.5, linecolor='gray', annot_kws={"fontsize": 10}
    )
    plt.title(f'Confusion Matrix: {model_name} (Acc: {test_acc:.3f})')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()

    cm_filename = MODEL_DIR / f"{model_name}_confusion_matrix.png"
    plt.savefig(cm_filename)
    plt.close()
    print(f"Confusion matrix saved to: {cm_filename}") 

    # 6. Save Model (Only save the best SVM iteration later)
    if not model_name.startswith('SVC_C'):
        joblib.dump(model, MODEL_DIR / f"{model_name}_gesture_model.pkl")
        print(f"✅ Saved model {model_name} in {MODEL_DIR}/")
    
    return model_name, test_acc, model, cv_scores.mean()


# --- Initialize and Run All Models ---

# Run SVM with multiple C values to manually find a good parameter
svm_candidates = [
    SVC(kernel='rbf', C=1.0, random_state=42, probability=True),
    SVC(kernel='rbf', C=10.0, random_state=42, probability=True),
    SVC(kernel='rbf', C=100.0, random_state=42, probability=True),
]

# Primary models list (RF, DT, KNN, and the best-performing SVM)
models_to_run = [
    RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
    DecisionTreeClassifier(max_depth=10, random_state=42),
    KNeighborsClassifier(n_neighbors=5, n_jobs=-1),
]

# Track results for comparison chart
results = []
best_svm_acc = 0
best_svm_model = None
best_svm_name = ""

# 1. Run primary models
for model in models_to_run:
    name, acc, _, _ = train_eval_model(model, X_train_scaled, y_train, X_test_scaled, y_test, LABELS)
    results.append({'model': name, 'accuracy': acc})

# 2. Run SVM candidates and find the best one
print("\n" + "#"*70)
print("--- Evaluating SVM Hyperparameter C (1, 10, 100) ---")
print("#"*70)
for svm in svm_candidates:
    name, acc, trained_model, _ = train_eval_model(svm, X_train_scaled, y_train, X_test_scaled, y_test, LABELS)
    
    if acc > best_svm_acc:
        best_svm_acc = acc
        best_svm_model = trained_model
        best_svm_name = name.replace("SVM_", "") # e.g., "C10"

# 3. Save the best SVM model
if best_svm_model:
    final_svm_name = f"SVC_BEST_{best_svm_name}"
    joblib.dump(best_svm_model, MODEL_DIR / f"{final_svm_name}_gesture_model.pkl")
    print(f"✅ Saved best SVM model ({final_svm_name}) in {MODEL_DIR}/")
    results.append({'model': final_svm_name, 'accuracy': best_svm_acc})

# --- Final Model Comparison Visualization ---

model_names = [r['model'] for r in results]
accuracies = [r['accuracy'] for r in results]

plt.figure(figsize=(10, 6))
# Ensure the colors are consistent and visually appealing
colors = sns.color_palette("viridis", len(model_names))
sns.barplot(x=model_names, y=accuracies, palette=colors)

plt.title('Gesture Classifier Model Comparison (Test Accuracy)')
plt.ylabel('Test Accuracy Score')
plt.xlabel('Model')
plt.ylim(min(accuracies) * 0.95, 1.0) # Set Y-axis scale based on min accuracy
plt.xticks(rotation=45, ha='right')

# Add accuracy values on top of bars
for i, acc in enumerate(accuracies):
    plt.text(i, acc + 0.005, f'{acc:.3f}', ha='center')

plt.tight_layout()
comparison_filename = MODEL_DIR / "model_comparison_chart.png"
plt.savefig(comparison_filename)
plt.close()

print(f"\nGenerated Model Comparison Chart at: {comparison_filename}")
