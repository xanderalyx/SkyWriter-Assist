// IAB330 Assignment 2B - Gesture Data Collector
// Collects accelerometer data for sign language letters via Bluetooth

#include <ArduinoBLE.h>
#include <Arduino_LSM6DS3.h>

// Bluetooth IDs for communication with Raspberry Pi
#define SERVICE_UUID        "19B10000-E8F2-537E-4F6C-D104768A1214"
#define COMMAND_UUID        "19B10001-E8F2-537E-4F6C-D104768A1214"  // Receives commands
#define ACCEL_DATA_UUID     "19B10002-E8F2-537E-4F6C-D104768A1214"  // Sends gesture data
#define STATUS_UUID         "19B10003-E8F2-537E-4F6C-D104768A1214"  // Sends status updates

// Settings for gesture capture
const int SAMPLE_RATE_HZ = 50;         // How fast we sample
const float CAPTURE_DURATION_SEC = 2.5; // How long each gesture takes
const int SAMPLES_PER_CAPTURE = 125;    // Total samples per gesture
const int SAMPLE_PERIOD_MS = 20;        // Time between samples

// BLE objects
BLEService gestureService(SERVICE_UUID);
BLEByteCharacteristic commandChar(COMMAND_UUID, BLERead | BLEWrite | BLENotify);
BLECharacteristic accelDataChar(ACCEL_DATA_UUID, BLERead | BLENotify, 240);
BLEByteCharacteristic statusChar(STATUS_UUID, BLERead | BLENotify);

// Command codes from Pi
const byte CMD_IDLE = 0;
const byte CMD_START_CAPTURE = 1;
const byte CMD_BUSY = 2;

// Status codes we send back
const byte STATUS_READY = 0;
const byte STATUS_COUNTDOWN_3 = 1;
const byte STATUS_COUNTDOWN_2 = 2;
const byte STATUS_COUNTDOWN_1 = 3;
const byte STATUS_CAPTURING = 4;
const byte STATUS_COMPLETE = 5;
const byte STATUS_ERROR = 6;

// State variables
bool captureRequested = false;
bool captureInProgress = false;
unsigned long captureStartTime = 0;
int currentSampleIndex = 0;

// Arrays to store gesture data
float accelX[SAMPLES_PER_CAPTURE];
float accelY[SAMPLES_PER_CAPTURE];
float accelZ[SAMPLES_PER_CAPTURE];

// LED for visual feedback
const int LED_PIN = LED_BUILTIN;

void setup() {
  Serial.begin(115200);
  
  // Set up LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Set up accelerometer
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1) {
      blinkError();
    }
  }
  
  // Set up Bluetooth
  if (!BLE.begin()) {
    Serial.println("Failed to initialize BLE!");
    while (1) {
      blinkError();
    }
  }
  
  // Configure Bluetooth settings
  BLE.setLocalName("Nano33IoT");
  BLE.setDeviceName("Nano33IoT");
  BLE.setAdvertisedService(gestureService);
  
  // Add the communication channels
  gestureService.addCharacteristic(commandChar);
  gestureService.addCharacteristic(accelDataChar);
  gestureService.addCharacteristic(statusChar);
  
  // Register the service
  BLE.addService(gestureService);
  
  // Start in idle state
  commandChar.writeValue((byte)CMD_IDLE);
  statusChar.writeValue((byte)STATUS_READY);
  
  // Set up command listener
  commandChar.setEventHandler(BLEWritten, onCommandWritten);
  
  // Make device discoverable
  BLE.advertise();
  
  Serial.println("BLE Gesture Capture Device");
  Serial.println("Waiting for connections...");
}

void loop() {
  // Listen for BLE connections
  BLEDevice central = BLE.central();
  
  if (central) {
    digitalWrite(LED_PIN, HIGH);  // LED on when connected
    
    // Wait a bit then tell Pi we're ready
    delay(1000);
    statusChar.writeValue(STATUS_READY);
    BLE.poll();
    delay(10);
    
    while (central.connected()) {
      // Handle capture request
      if (captureRequested && !captureInProgress) {
        captureRequested = false;
        startCapture();
      }
      
      // Handle ongoing capture
      if (captureInProgress) {
        performCapture();
      }
      
      BLE.poll();
    }
    
    digitalWrite(LED_PIN, LOW);  // LED off when disconnected
  }
}

void onCommandWritten(BLEDevice central, BLECharacteristic characteristic) {
  byte command = 0;
  commandChar.readValue(command);
  
  if (command == CMD_START_CAPTURE && !captureInProgress) {
    captureRequested = true;
  }
}

void startCapture() {
  // Tell Pi we're busy
  commandChar.writeValue((byte)CMD_BUSY);
  BLE.poll();
  delay(10);
  
  // Start countdown
  statusChar.writeValue(STATUS_COUNTDOWN_3);
  BLE.poll();
  delay(1000);
  
  // Two
  statusChar.writeValue(STATUS_COUNTDOWN_2);
  BLE.poll();
  delay(1000);
  
  // One
  statusChar.writeValue(STATUS_COUNTDOWN_1);
  BLE.poll();
  delay(1000);
  
  // Start recording
  statusChar.writeValue(STATUS_CAPTURING);
  BLE.poll();
  
  captureInProgress = true;
  captureStartTime = millis();
  currentSampleIndex = 0;
  
  // Quick LED blink
  digitalWrite(LED_PIN, LOW);
  delay(100);
  digitalWrite(LED_PIN, HIGH);
}

void performCapture() {
  unsigned long currentTime = millis();
  unsigned long elapsedTime = currentTime - captureStartTime;
  
  // Time to take next sample?
  if (elapsedTime >= currentSampleIndex * SAMPLE_PERIOD_MS) {
    if (currentSampleIndex < SAMPLES_PER_CAPTURE) {
      float x, y, z;
      
      if (IMU.accelerationAvailable()) {
        IMU.readAcceleration(x, y, z);
        
        // Save the reading
        accelX[currentSampleIndex] = x;
        accelY[currentSampleIndex] = y;
        accelZ[currentSampleIndex] = z;
        
        currentSampleIndex++;
        
      }
    }
  }
  
  // Done capturing?
  if (currentSampleIndex >= SAMPLES_PER_CAPTURE) {
    captureInProgress = false;
    // Double blink to show we're done
    for (int i = 0; i < 2; i++) {
      digitalWrite(LED_PIN, LOW);
      delay(100);
      digitalWrite(LED_PIN, HIGH);
      delay(100);
    }
    
    // Send the data to Pi
    sendDataOverBLE();
    
    // Ready for next gesture
    statusChar.writeValue(STATUS_READY);
  }
}

void sendDataOverBLE() {
  // Send status first to wake up connection
  statusChar.writeValue(STATUS_CAPTURING);
  BLE.poll();
  delay(10);
  
  // Split data into small chunks for Bluetooth
  const int SAMPLES_PER_CHUNK = 3;
  const int TOTAL_CHUNKS = (SAMPLES_PER_CAPTURE + SAMPLES_PER_CHUNK - 1) / SAMPLES_PER_CHUNK;
  
  byte buffer[20];
  int samplesSent = 0;
  
  for (int chunk = 0; chunk < TOTAL_CHUNKS; chunk++) {
    int samplesInChunk = min(SAMPLES_PER_CHUNK, SAMPLES_PER_CAPTURE - samplesSent);
    
    // Chunk header
    buffer[0] = chunk;
    buffer[1] = samplesInChunk;
    
    // Pack samples as int16 (millig)
    int bufferIndex = 2;
    for (int i = 0; i < samplesInChunk; i++) {
      int sampleIndex = samplesSent + i;
      
      // Convert to integers (millig)
      int16_t x_mg = (int16_t)(accelX[sampleIndex] * 1000);
      int16_t y_mg = (int16_t)(accelY[sampleIndex] * 1000);
      int16_t z_mg = (int16_t)(accelZ[sampleIndex] * 1000);
      
      // Pack as bytes
      buffer[bufferIndex++] = x_mg & 0xFF;
      buffer[bufferIndex++] = (x_mg >> 8) & 0xFF;
      buffer[bufferIndex++] = y_mg & 0xFF;
      buffer[bufferIndex++] = (y_mg >> 8) & 0xFF;
      buffer[bufferIndex++] = z_mg & 0xFF;
      buffer[bufferIndex++] = (z_mg >> 8) & 0xFF;
    }
    
    accelDataChar.writeValue(buffer, bufferIndex);
    BLE.poll();
    delay(10);
    samplesSent += samplesInChunk;
    
    // Keep connection alive every 10 chunks
    if ((chunk + 1) % 10 == 0) {
      statusChar.writeValue(STATUS_CAPTURING);
      BLE.poll();
      delay(10);
    }
  }
  
  // Make sure everything gets sent
  unsigned long tflush = millis();
  while (millis() - tflush < 60) {
    BLE.poll();
    delay(5);
  }
  
  // Tell Pi we're done
  statusChar.writeValue(STATUS_COMPLETE);
  BLE.poll();
  delay(10);
  
  // Reset command state
  commandChar.writeValue((byte)CMD_IDLE);
  BLE.poll();
  delay(10);
}

void blinkError() {
  digitalWrite(LED_PIN, HIGH);
  delay(100);
  digitalWrite(LED_PIN, LOW);
  delay(100);
}
