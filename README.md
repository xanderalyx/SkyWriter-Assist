# SkyWriter-Assist
## ✍️ Air-Writer: Gesture-Based Assistive Text Input System
### Project Goal
### Air-Writer is a Human Activity Recognition (HAR) proof-of-concept designed as an assistive technology tool. It provides an alternative text input method for individuals with writing or typing disabilities. By wearing a wrist-mounted Arduino nano 33 IoT, with the Inertial Measurement Unit (IMU) device, users can "write in the air" with gestures that are classified in real-time as alphabet characters. The system uses a robust HAR pipeline running on an Edge-AI architecture (Arduino Nano 33 IoT & Raspberry Pi) to promote independence and inclusivity through a novel form of communication.
## ✨ Key Features & Technical Scope
* Assistive Technology Focus: Addresses the real-world challenge of limited text input for individuals with fine motor control issues.
* Gesture Set: The prototype is scoped to recognise 11 uppercase alphabet characters (P, R, B, D, G, S, C, L, O, V, Z). This set was specifically chosen to test the model's ability to distinguish between simple, distinct gestures and highly confusable pairs.
* Edge-AI Architecture:
  * Sensor Node: Arduino Nano 33 IoT collects raw accelerometer data at 50 Hz within a 2.5-second capture window.
  * Wireless Communication: Uses Bluetooth Low Energy (BLE) for low-latency, low-power data transmission. The system implements a robust sequence-checking and reassembly protocol to ensure data integrity during transfer.
  * Edge Device: Raspberry Pi acts as the central hub, performing local data preprocessing (smoothing, feature extraction) and real-time Machine Learning (ML) inference.
* Data Pipeline: Raw sensor data is transformed via feature engineering (Time-Domain Statistics like Mean, RMS, Zero-crossing Rate) into compact feature vectors for classification.
* Machine Learning: The project explores and evaluates the performance of several classification models suitable for edge deployment: KNN, SVM, Decision Tree, and Random Forest.
* Performance Objectives: Targets include achieving 80% classification accuracy and maintaining a low end-to-end latency of approximately 3 seconds (2.5s capture transfer/inference).
* Data Management: A MongoDB database is used for long-term storage of labelled gesture data, supporting future model refinement and system monitoring.

# 💾 Data Flow and Model Training Pipeline
### A. Real-Time Data Collection and Storage (Raspberry Pi to MongoDB)
### The captured and processed gesture data is continuously sent to the database to build a comprehensive training dataset:
1. Real-Time Data Upload: After a complete gesture window is received and processed on the Raspberry Pi, the raw and processed data, along with their labels and metadata, are immediately batched and sent to the MongoDB database.
2. Data Format: The data is stored in the database as a JSON document. This flexible structure allows each entry to contain the raw x, y, z accelerometer arrays, the extracted feature vector, the gesture_label (ground truth), and identifiers (e.g., participant_id, arduino_id).
## B. Offline Model Training and Selection
### The Raspberry Pi utilises this JSON data from MongoDB for its core model development, executed via the train_from_merged.py script.
1. Data Ingestion: The train_from_merged.py script pulls the complete dataset (JSON documents) from the MongoDB database.
2. Model Evaluation: The system trains multiple candidate models (KNN, SVM, Decision Tree, Random Forest) and evaluates their performance against a held-out test set.
3. Metrics for Selection: The optimal model is selected by the user based on a combination of classification metrics saved and printed to the console:
   * Overall Test Accuracy: The main headline figure, measuring overall correct classification percentage.
   * Macro F1-Score: Crucial for multi-class problems, as it ensures the model performs well across all 11 characters, preventing one easy-to-classify character from skewing the overall score.
   * Classification Report: Provides Precision (avoiding false positives) and Recall (avoiding false negatives) for each individual letter, highlighting which gestures the model excels or struggles with.
   * Confusion Matrix: A visual heatmap that shows misclassification patterns. The user uses this to identify confusable pairs (e.g., if P is often mistaken for R) to determine the model that handles these challenging cases most effectively.

# 📡 Detailed Gesture Data Capture Pipeline
### The core task is managed by the capture_new_gesture() function in ble_capture_module.py, which executes the asynchronous core logic for data transfer.
### 1. Initialisation and Connection (Raspberry Pi)
* User Input: The main loop in realtime_predictor.py waits for the user to press Enter to trigger a new capture cycle.
* BLE Client Connect: The Raspberry Pi (BLE Central) establishes a connection with the Arduino Nano 33 IoT (BLE Peripheral).
* Start Notifications: The Pi starts listening by subscribing to:
 * ACCEL_DATA_UUID: For receiving and unpacking raw sensor data chunks.
 * STATUS_UUID: For tracking the capture state on the Arduino (e.g., countdown, capturing, complete).
2. Initiating Capture (Pi to Arduino)
* Send Command: The Pi sends the command CMD_START_CAPTURE (\x01 byte) to the COMMAND_UUID characteristic.
* Countdown/Cues: The Arduino begins an internal countdown and sends status codes (1, 2, 3) via the STATUS_UUID. The Pi displays this countdown to the user.
3. Sensor Data Acquisition (Arduino)
* Start Recording: When the countdown completes, the Arduino sends STATUS_CAPTURING. It then records a 2.5-second window of IMU accelerometer data at 50 Hz.
* Data Structure: The window contains 125 samples (2.5s * 50 Hz). Each sample is a 3-axis set (X, Y, Z) of 16-bit integers, representing acceleration in milligravity (mg).
4. Data Transmission and Reassembly
* Chunking: The Arduino sends the data in small packets (notifications) over BLE, including a sequence number for order checking.
* Unpacking: The Pi's data_notification_handler() receives the chunks:
 * It unpacks the 16-bit integers using struct.unpack('<hhh, ...).
 * It converts the mg values back into Gs (float) by dividing by 1000.0.
 * The values are appended to the local gesture_points list.
5. Completion and Hand-Off
* Capture End: Once all 125 samples are sent, the Arduino signals STATUS_COMPLETE.
* Signal Event: This status sets an asyncio.Event on the Pi, exiting the waiting loop.
* Return Data: The Pi returns the complete, reassembled, and unpacked raw data as a NumPy array of shape (125, 3) to realtime_predictor.py.
## 4. 🧠 Post-Capture Processing & Prediction
Once the raw data is received in realtime_predictor.py, it moves into the machine learning pipeline:
1. Feature Extraction features.py:
   * The data is passed to extract_features.
   * Gravity Compensation is performed (window - mean(window)).
   * 42 Time-Domain Features (e.g., Standard Deviation, Variance, Min/Max, Jerk, Zero-crossing Rate, Active Time Fraction) are calculated from the gravity-compensated signal.
2. Scaling: The resulting feature vector is scaled using the pre-loaded StandardScaler to normalise the feature ranges.
3. Inference: The scaled feature vector is passed to the loaded SVC (Support Vector Classifier) model for a real-time prediction.
4. Output: The model returns the predicted letter and its confidence, which is displayed to the user. If confidence is below the CONFIDENCE_THRESHOLD, the system displays the top prediction along with the two closest competing candidates.
