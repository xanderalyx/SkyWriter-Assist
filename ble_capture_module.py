import asyncio
import numpy as np
import struct
import sys # Added for flushing print statements 1.. 2.. 3.. example
from bleak import BleakClient
from typing import List

# === CONFIGURATION ===
ARDUINO_ADDRESS = "30:C6:F7:02:AA:C6" # <<< REPLACE THIS WITH YOUR DEVICE ADDRESS! >>>

# BLE UUIDs (Must match the Arduino sketch)
COMMAND_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
ACCEL_DATA_UUID = "19B10002-E8F2-537E-4F6C-D104768A1214"
STATUS_UUID = "19B10003-E8F2-537E-4F6C-D104768A1214"

# Command and Status Codes
CMD_START_CAPTURE = b'\x01' # Corresponds to CMD_START_CAPTURE = 1
STATUS_CAPTURING = 4        # Corresponds to STATUS_CAPTURING = 4
STATUS_COMPLETE = 5         # Corresponds to STATUS_COMPLETE = 5
SAMPLES_PER_CAPTURE = 125   # Corresponds to SAMPLES_PER_CAPTURE = 125

async def capture_new_gesture_async(address: str):
    """
    Asynchronous core function to manage the BLE connection and data transfer.
    State (gesture_points and status_event) is now LOCAL to this function, 
    ensuring they are bound correctly to the current event loop.
    """
    
    # === LOCAL STATE INIT (Bound to the current event loop) ===
    gesture_points = []
    status_event = asyncio.Event()
    # ==========================================================

    def display_status(status_code: int):
        """Prints user-facing status messages based on the received status code."""
        # Use carriage return (\r) to overwrite the previous line for countdown
        
        if status_code == 1:
            print("Status: Countdown 3...", end='\r')
            sys.stdout.flush()
        elif status_code == 2:
            print("Status: Countdown 2...", end='\r')
            sys.stdout.flush()
        elif status_code == 3:
            print("Status: Countdown 1...", end='\r')
            sys.stdout.flush()
        elif status_code == STATUS_CAPTURING:
            # Print a clear, new line for the start of capture
            print(" " * 40, end='\r') # Clear previous countdown line
            print("====================================")
            print("==> BEGIN WRITING NOW - CAPTURING...")
            print("====================================")
            sys.stdout.flush()
        elif status_code == STATUS_COMPLETE:
            # Print a final message before prediction starts
            print("Capture complete. Data received and processing...")
            sys.stdout.flush()

    # 1. Define data handler as a closure
    def data_notification_handler(sender: int, data: bytearray):
        """Callback for receiving gesture data chunks, modifies the local 'gesture_points'."""
        if len(data) < 2: return 
        
        samples_in_chunk = data[1]
        payload = data[2:]
        bytes_per_sample = 6 
        
        try:
            for i in range(samples_in_chunk):
                start = i * bytes_per_sample
                end = start + bytes_per_sample
                
                # Unpack 3 short integers (x_mg, y_mg, z_mg)
                x_mg, y_mg, z_mg = struct.unpack('<hhh', payload[start:end])
                
                # Convert from milligravity (mg) back to Gs (float)
                x_g = x_mg / 1000.0
                y_g = y_mg / 1000.0 
                z_g = z_mg / 1000.0
                
                # Append to the local list
                gesture_points.append((x_g, y_g, z_g)) 
                
        except struct.error:
            # This handles cases where a chunk might be partial or corrupted.
            # It prevents the error from propagating up and killing the BLE message loop.
            return

    # 2. Define status handler as a closure
    def status_notification_handler(sender: int, data: bytearray):
        """Callback for receiving status updates, sets the local 'status_event'."""
        if len(data) >= 1:
            status_code = data[0]
            display_status(status_code) # Print status update
            
            # Check if the status byte matches STATUS_COMPLETE (5)
            if status_code == STATUS_COMPLETE:
                status_event.set()

    # 3. Connection and data transfer logic
    try:
        async with BleakClient(address) as client:
            if not client.is_connected:
                print("BLE ERROR: Failed to connect.")
                return None
            
            # Print status update
            print("Connection established. Waiting for countdown...")
            sys.stdout.flush()

            # Start listening using the locally defined handlers
            await client.start_notify(ACCEL_DATA_UUID, data_notification_handler)
            await client.start_notify(STATUS_UUID, status_notification_handler)
            
            # Send the START_CAPTURE command
            await client.write_gatt_char(COMMAND_UUID, CMD_START_CAPTURE, response=True)
            
            # Wait for the status_event (local and correctly bound)
            await asyncio.wait_for(status_event.wait(), timeout=15.0) # Increased timeout slightly for safety

            # Stop listeners
            await client.stop_notify(ACCEL_DATA_UUID)
            await client.stop_notify(STATUS_UUID)
            
            # Return the local data
            return np.array(gesture_points)

    except asyncio.TimeoutError:
        print("\nBLE ERROR: Capture timed out (15s limit reached). Check Arduino status and range.")
        return None
    except Exception as e:
        # Catch other connection/BLE errors
        print(f"\nBLE COMMUNICATION ERROR: {e}")
        return None


def capture_new_gesture() -> np.ndarray:
    """Synchronous wrapper: The function realtime_predictor.py will call."""
    return asyncio.run(capture_new_gesture_async(ARDUINO_ADDRESS))
