# 📊 data/

This directory is the storage location for the raw, merged, and labeled accelerometer data used exclusively for **model training and evaluation** by the `src/train_from_merged.py` script.

## 1. Data File

* **`pi_gesture_data_merged_all.json`**

This file contains the entire corpus of collected gestures for all $\text{11}$ target characters ($\text{P, R, B, D, G, S, C, L, O, V, Z}$). The data was captured via the Bluetooth Low Energy (BLE) pipeline from the Arduino Nano 33 IoT.

## 2. Data Structure and Format

The data is stored as a single **JSON document**, where each record represents one complete gesture capture. This flexible format allows for easy ingestion and processing by the Python training script.

Each individual record in the $\text{JSON}$ document contains the following key fields:

| Field Name | Type | Description |
| :--- | :--- | :--- |
| **`accelerometer_data`** | Array of Arrays | The **raw, reassembled $\text{x, y, z}$ accelerometer values** (125 samples, shape $\text{[125, 3]}$) after conversion from milligravity ($\text{mg}$) to Gs ($\text{float}$). |
| **`gesture_label`** | String | The **ground truth** label (e.g., 'P', 'R', 'B') assigned to the gesture during data collection. |
| **`participant_id`** | String | Identifier for the user who performed the gesture. |
| **`metadata`** | Object | Timestamp and other session-specific details. |

## 3. Usage

The `src/train_from_merged.py` script pulls this entire dataset from the `data/` folder, performs feature extraction, and uses it to train and evaluate the $\text{SVC, KNN, Random Forest,}$ and $\text{Decision Tree}$ models.
