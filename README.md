# SkyWriter-Assist

## ✍️ Air-Writer: Gesture-Based Assistive Text Input System

### Project Goal

Air-Writer is a **Human Activity Recognition (HAR)** proof-of-concept designed as an **assistive technology** tool. It provides an alternative text input method for individuals with writing or typing disabilities. By wearing a wrist-mounted **Arduino Nano 33 IoT**, with the **Inertial Measurement Unit (IMU)** device, users can "write in the air" with gestures that are classified in real-time as alphabet characters. The system uses a robust HAR pipeline running on an Edge-AI architecture (Arduino Nano 33 IoT & Raspberry Pi) to promote independence and inclusivity through a novel form of communication.

---

## ✨ Key Features & Technical Scope

* **Assistive Technology Focus:** Addresses the real-world challenge of limited text input for individuals with fine motor control issues.
* **Gesture Set:** The prototype is scoped to recognise **11 uppercase alphabet characters (P, R, B, D, G, S, C, L, O, V, Z)**.
* **Edge-AI Architecture:**
    * **Sensor Node:** **Arduino Nano 33 IoT** collects raw accelerometer data at **50 Hz** within a **2.5-second capture window**. **[Firmware Code: `arduino_firmware/gesturecollectorble.ino`]**
    * **Wireless Communication:** Uses **Bluetooth Low Energy (BLE)** for low-latency, low-power data transmission.
    * **Edge Device:** **Raspberry Pi** acts as the central hub, performing local data preprocessing and real-time Machine Learning (ML) inference.
* **Data Pipeline:** Raw sensor data is transformed via feature engineering (Time-Domain Statistics like Mean, RMS, Zero-crossing Rate) into compact feature vectors for classification.
* **Machine Learning:** The project explores and evaluates the performance of several models: **KNN, SVM, Decision Tree, and Random Forest**.
* **Performance Objectives:** Targets include achieving **80% classification accuracy** and maintaining a low end-to-end latency of approximately **3 seconds**.

---

## 💾 Data Flow and Model Training Pipeline

### **A. Real-Time Data Collection and Storage (Raspberry Pi $\to$ MongoDB)**

The captured gesture data is continuously stored to build a comprehensive training dataset:

1.  **Real-Time Data Upload:** After a complete gesture window is received and processed on the **Raspberry Pi**, the raw and processed data, along with its label and metadata, are immediately batched and sent to the **MongoDB database** in real-time.
2.  **Data Format:** The data is stored as a **JSON document**. This same structure is mirrored locally in the **`data/`** directory (e.g., `data/pi_gesture_data_merged_all.json`).

### **B. Offline Model Training and Selection**

The $\text{Raspberry Pi}$ utilises this $\text{JSON}$ data for core model development, executed via the `src/train_from_merged.py` script.

1.  **Model Evaluation:** The system trains multiple candidate models, and all trained artifacts (`.pkl` files) are stored in the **`models/`** directory.
2.  **Metrics for Selection:** The optimal model is selected by the user based on comprehensive metrics :
    * **Overall Test Accuracy**
    * **Macro F1-Score:** Crucial for multi-class problems, ensuring performance across **all 11 characters**.
    * **Confusion Matrix:** Used to visually identify **confusable pairs** (e.g., P mistaken for R) to select the model that best handles challenging classifications.

### **C. Project Documentation**

The full, detailed design and proposal report and supplementary materials are included in the dedicated documentation directory.

* **Project Proposal:** Contains the full literature review, proposed methodology, system design rationale, model evaluation plan, and results discussion. **[Located in `docs/SkyWriter-Assist_Final_Report.pdf`]**

---

## 📡 Detailed Gesture Data Capture Pipeline

### **1. Microcontroller Firmware (`arduino_firmware/`)**

The data acquisition is managed by the Arduino firmware, which implements the BLE Peripheral role.

* **Capture Parameters:** Data is recorded for **2.5 seconds** at **50 Hz**, resulting in 125 samples per gesture.
* **Data Packing:** Accelerometer values (G) are converted to **milligravity (mg)** (int16) and packaged into **42 small BLE chunks** to ensure data integrity during transmission.

### **2. BLE Communication and Reassembly (`src/ble_capture_module.py`)**

The Python client on the Raspberry Pi (BLE Central) executes the core logic for data transfer:

* **Initiation:** The Pi sends the CMD_START_CAPTURE command to the Arduino.
* **Status Tracking:** The Pi displays the 3-2-1 countdown and monitors the STATUS_COMPLETE signal.
* **Unpacking:** The Pi's notification handler receives the 42 data chunks, unpacks the 16-bit integers using `struct.unpack('<hhh', ...)`, converts the mg values back into Gs (float), and reassembles them into a complete (125, 3) NumPy array.

---

### 💻 Core Source Code (`src/`)

The Python scripts in the `src/` directory manage the execution of the Edge-AI pipeline:

* **`realtime_predictor.py`**: The main application that loads the final model and scaler from `models/` and orchestrates the live capture and classification loop.
* **`ble_capture_module.py`**: Handles all asynchronous BLE client communication, chunk reassembly, and data type conversion.
* **`features.py`**: Contains the logic to perform **Gravity Compensation** and calculate the **42 Time-Domain Features** (e.g., standard deviation, jerk) from the raw sensor data.
* **`train_from_merged.py`**: Executes the entire offline training pipeline, from loading data in `data/` to generating artifacts in `models/`.

---

## 📁 Repository Structure

The project code and artifacts are organised into clear directories for easy navigation :

| Directory | Content | Role |
| :--- | :--- | :--- |
| **`src/`** | Python scripts (`.py`) | Contains all core Python logic (BLE communication, feature engineering, training, and real-time prediction). |
| **`arduino_firmware/`** | Arduino sketch (`.ino`) | Contains the source code for the sensor node, managing IMU collection and BLE transmission. |
| **`data/`** | JSON data file (`.json`) | Stores the merged, labeled dataset used for offline training. |
| **`models/`** | Trained models (`.pkl`) and metrics (`.png`) | Stores all serialised classifiers, the `scaler.pkl` object, and evaluation results (confusion matrices, comparison chart). |
| **`docs/`** | **Final Report (.pdf or .docx)** | **The full project report, methodology, and evaluation narrative.** |
