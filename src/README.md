# 📂 src/

This directory contains the **core Python source code** for the SkyWriter Assist system, running on the Raspberry Pi (Edge Device). These scripts handle the Bluetooth Low Energy (BLE) communication, feature engineering, model training, and real-time inference.

| File | Role in the System |
| :--- | :--- |
| **`ble_capture_module.py`** | **BLE Communication & Data Acquisition.** Contains the asynchronous logic (`capture_new_gesture_async`) for connecting to the Arduino, sending the START command, and receiving/reassembling the raw 3-axis accelerometer data chunks via BLE notifications. |
| **`features.py`** | **Feature Engineering Logic.** Defines the `extract_features()` function used to transform the raw $\text{(N, 3)}$ accelerometer data into a $\text{1D}$ feature vector (42 features). This includes gravity compensation, calculating RMS, Jerk, Zero-Crossing Rate, and other time-domain statistics. |
| **`train_from_merged.py`** | **Offline Model Training & Evaluation.** Reads the JSON dataset from the `data/` directory, extracts features, performs scaling, trains multiple classifier models ($\text{SVM, RF, KNN, DT}$), and evaluates performance to select the best model for deployment. |
| **`realtime_predictor.py`** | **Real-Time Deployment & Inference.** The main execution script. It loads the best-trained model and scaler, continuously calls the BLE capture function, performs feature extraction on the live data, and predicts the gesture in real-time. |

---

### **Dependencies**

This code relies on external libraries including `numpy`, `scipy.stats`, `scipy.signal`, `sklearn`, and the asynchronous BLE library `bleak`.
