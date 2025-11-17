# 📡 Data Capture and Collection Code

This directory contains the essential code required to perform **labeled data collection** for the gesture recognition system. It consists of the firmware that runs on the sensor node (Arduino) and the Python client that runs on the edge device (Raspberry Pi).

## 1. ⚙️ Arduino Firmware (`gesturecollectorble.ino`)

This is the **BLE Peripheral** device, responsible for running the IMU, listening for commands, and transmitting the raw sensor data in chunks.

| Specification | Value | Description |
| :--- | :--- | :--- |
| **Microcontroller** | Arduino Nano 33 IoT | Contains the IMU (LSM6DS3) and BLE module. |
| **Sensor Data** | 3-axis Accelerometer | Uses the `IMU.readAcceleration(x, y, z)` function. |
| **Capture Window** | **2.5 seconds** | The fixed time duration for one gesture recording. |
| **Sample Rate** | **50 Hz** ($\text{20ms}$ period) | Totaling **125 samples** per capture ($\text{2.5s} \times \text{50Hz}$). |
| **Data Format** | int16_ (signed 16-bit integer) | Raw floating-point G-force values are converted to **milligravity (mg)** by multiplying by 1000 before packing. |
| **Chunking** | **3 samples** per BLE Notification | To ensure reliable transmission, data is split and sent in small packets (18 bytes of sensor data + 2 bytes header). |
| **Total Chunks** | **42** | Approximately $\text{125 samples} / \text{3 samples per chunk}$. |

### BLE Characteristics (Channels)

The communication relies on four standard BLE characteristics:

| UUID | Characteristic | Direction | Purpose |
| :--- | :--- | :--- | :--- |
| $\text{19B10001}$ | `COMMAND_UUID` | Pi $\to$ Arduino | Receives CMD_START_CAPTURE command (1) to begin recording. |
| $\text{19B10003}$ | `STATUS_UUID` | Arduino $\to$ Pi | Sends state updates: Countdown ($\text{1, 2, 3}$), Capturing ($\text{4}$), Complete ($\text{5}$). |
| $\text{19B10002}$ | `ACCEL_DATA_UUID`| Arduino $\to$ Pi | Sends the chunked raw sensor data payload for reassembly. |

## 2. 💻 Raspberry Pi Collector (`raspberry_pi_collector.py`)

This is the **BLE Central** device, implemented in Python using the `bleak` library. It manages the connection, triggers the capture, and performs data reassembly and persistence.

### Key Functions

| Function | Role |
| :--- | :--- |
| **`scan_for_device()`** | Scans for an available BLE peripheral device named **"Nano33IoT"**. |
| **`start_notify()`** | Subscribes to the STATUS_UUID and ACCEL_DATA_UUID to start listening for data and state changes. |
| **`handle_accel_data()`** | **Data Reassembly Logic:** Receives the raw byte chunks. It uses the `struct.unpack_from('<h', ...)` function to unpack the 16-bit integers (milligravity) and converts them back to **Gs ($\text{float}$)** by dividing by 1000.0. |
| **`assemble_complete_capture()`** | After receiving STATUS_COMPLETE, it sorts the received chunks by sequence number and merges the x, y, z samples into three complete arrays. |
| **`save_last_capture()`** | Writes the complete, assembled $\text{x, y, z}$ arrays, along with the assigned gesture label, to the **`pi_gesture_data.json`** file for later model training. |

### Console Commands

The script runs a command-line interface to facilitate data collection for training:

| Command | Action |
| :--- | :--- |
| **`train <LETTER>`** | Sets the label for the next set of captures (e.g., `train P`). |
| **`capture`** | Sends CMD_START_CAPTURE to the Arduino to begin the 3-2-1 countdown and data recording sequence. |
| **`save`** | Saves the last successfully captured gesture to the $\text{JSON}$ data file under the current letter. |
| **`retry`** | Discards the last capture and immediately starts a new capture cycle. |
| **`stats`** | Prints the current count of captured attempts for all 11 target letters. |
