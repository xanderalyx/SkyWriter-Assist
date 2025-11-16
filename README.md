# SkyWriter-Assist
## Air-Writer: Gesture-Based Assistive Text Input System
### Project Goal
### Air-Writer is a Human Activity Recognition (HAR) proof-of-concept designed as an assistive technology tool. It provides an alternative text input method for individuals with writing or typing disabilities. By wearing a wrist-mounted Inertial Measurement Unit (IMU) device, users can "write in the air" with gestures that are classified in real-time as alphabet characters. Our system uses a robust HAR pipeline running on an Edge-AI architecture (Arduino Nano 33 IoT & Raspberry Pi) to promote independence and inclusivity through a novel form of communication.
## ✨ Key Features & Technical Scope
* Assistive Technology Focus: Addresses the real-world challenge of limited text input for individuals with fine motor control issues.
* Gesture Set: The prototype is scoped to recognize 11 uppercase alphabet characters (P, R, B, D, G, S, C, L, O, V, Z). This set was specifically chosen to test the model's ability to distinguish between simple, distinct gestures and highly confusable pairs.
* Edge-AI Architecture:
  * Sensor Node: Arduino Nano 33 IoT collects raw accelerometer data at 50 Hz within a 2.5-second capture window.
  * Wireless Communication: Uses Bluetooth Low Energy (BLE) for low-latency, low-power data transmission. The system implements a robust sequence-checking and reassembly protocol to ensure data integrity during transfer.
  * Edge Device: Raspberry Pi acts as the central hub, performing local data preprocessing (smoothing, feature extraction) and real-time Machine Learning (ML) inference.
* Data Pipeline: Raw sensor data is transformed via feature engineering (Time-Domain Statistics like Mean, RMS, Zero-crossing Rate) into compact feature vectors for classification.
* Machine Learning: The project explores and evaluates the performance of several classification models suitable for edge deployment: KNN, SVM, Decision Tree, and Random Forest.
* Performance Objectives: Targets include achieving 80% classification accuracy and maintaining a low end-to-end latency of approximately 3 seconds (2.5s capture transfer/inference).
* Data Management: A MongoDB database is used for long-term storage of labelled gesture data, supporting future model refinement and system monitoring.
