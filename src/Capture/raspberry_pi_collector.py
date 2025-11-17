#!/usr/bin/env python3
from __future__ import annotations

"""
IAB330 Assignment 2B - Raspberry Pi BLE Data Collector
"""

import asyncio
import json
import os
import struct
import time
from typing import Dict, List, Optional
from datetime import datetime

from bleak import BleakClient, BleakScanner

SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214"
COMMAND_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
ACCEL_DATA_UUID = "19B10002-E8F2-537E-4F6C-D104768A1214"
STATUS_UUID = "19B10003-E8F2-537E-4F6C-D104768A1214"

CMD_IDLE = 0
CMD_START_CAPTURE = 1
CMD_BUSY = 2

STATUS_READY = 0
STATUS_COUNTDOWN_3 = 1
STATUS_COUNTDOWN_2 = 2
STATUS_COUNTDOWN_1 = 3
STATUS_CAPTURING = 4
STATUS_COMPLETE = 5
STATUS_ERROR = 6

EXPECTED_CHUNKS = 42  # 3-sample payloads * 42 ~= 125 samples


class GestureDataCollector:
    def __init__(self, data_file: str = "pi_gesture_data.json") -> None:
        self.client: Optional[BleakClient] = None
        self.device_address: Optional[str] = None
        self.data_file = data_file
        self.data = self.load_existing_data()
        if "data" not in self.data:
            self.data["data"] = {}

        self.capture_in_progress = False
        self.received_chunks: Dict[int, List[List[float]]] = {}
        self.last_capture: Optional[Dict] = None
        self.expected_chunks = EXPECTED_CHUNKS
        self.current_letter: Optional[str] = None

        self.capture_done = asyncio.Event()
        self.capture_done.set()

    # Persistence helpers
    def load_existing_data(self) -> Dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                print(f"Loaded existing data from {self.data_file}")
                return data
            except Exception as exc:
                print(f"Error loading data: {exc}")

        return {
            "project": "IAB330_Assignment_2B",
            "group": 40,
            "created": datetime.now().isoformat(),
            "data": {},
        }

    def save_last_capture(self) -> bool:
        if not self.last_capture:
            print("No capture to save!")
            return False
        if not self.current_letter:
            print("No letter selected for training!")
            return False

        data_root = self.data.setdefault("data", {})
        letter_data = data_root.setdefault(self.current_letter, {"attempts": 0, "captures": []})

        attempt_num = len(letter_data["captures"]) + 1
        letter_data["captures"].append({
            "attempt": attempt_num,
            "timestamp": self.last_capture["timestamp"],
            "x": self.last_capture["x"],
            "y": self.last_capture["y"],
            "z": self.last_capture["z"],
        })
        letter_data["attempts"] = len(letter_data["captures"])
        self.data["last_modified"] = datetime.now().isoformat()

        with open(self.data_file, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2)

        print(f"SAVED: Letter '{self.current_letter}', Attempt #{attempt_num}")
        print(f"Total for {self.current_letter}: {letter_data['attempts']} attempts")
        print(f"File: {os.path.abspath(self.data_file)}")

        self.last_capture = None
        return True

    # BLE lifecycle
    async def scan_for_device(self, timeout: float = 10.0) -> bool:
        print("Scanning for Arduino devices...")
        devices = await BleakScanner.discover(timeout=timeout)
        for device in devices:
            if device.name and "Nano33IoT" in device.name:
                print(f"Found Arduino: {device.name} ({device.address})")
                self.device_address = device.address
                return True
        print("No Arduino device found.")
        return False

    async def connect(self) -> bool:
        if not self.device_address and not await self.scan_for_device():
            return False

        try:
            assert self.device_address
            self.client = BleakClient(self.device_address)
            await self.client.connect()
            print("Setting up BLE notifications...")

            await self.client.start_notify(STATUS_UUID, self.handle_status_change)
            await asyncio.sleep(0.1)

            await self.client.start_notify(ACCEL_DATA_UUID, self.handle_accel_data)
            await asyncio.sleep(0.1)

            try:
                await self.client.start_notify(COMMAND_UUID, self.handle_command_change)
            except:
                pass  # Optional, not critical

            # Give BLE time to stabilize
            await asyncio.sleep(2)

            self.capture_in_progress = False
            self.received_chunks.clear()
            self.capture_done.set()

            print(f"Connected to Arduino at {self.device_address}")
            return True
        except Exception as exc:
            print(f"Connection failed: {exc}")
            return False

    async def disconnect(self) -> None:
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("Disconnected from Arduino")
        self.client = None

    # Notification handlers
    def handle_accel_data(self, _sender: int, data: bytearray) -> None:
        if len(data) < 2:
            return

        sequence_num = data[0]
        sample_count = data[1]

        samples: List[List[float]] = []
        for i in range(sample_count):
            base = 2 + i * 6
            if base + 6 > len(data):
                break
            x = struct.unpack_from('<h', data, base)[0] / 1000.0
            y = struct.unpack_from('<h', data, base + 2)[0] / 1000.0
            z = struct.unpack_from('<h', data, base + 4)[0] / 1000.0
            samples.append([x, y, z])

        self.received_chunks[sequence_num] = samples
        
        # Show progress every 10 chunks
        if (sequence_num + 1) % 10 == 0:
            print(f"Receiving data... {sequence_num + 1}/{self.expected_chunks}")

    def handle_command_change(self, _sender: int, data: bytearray) -> None:
        if not data:
            return
        state = data[0]
        
        if state == CMD_BUSY:
            self.capture_done.clear()
            self.capture_in_progress = True
        elif state == CMD_IDLE:
            self.capture_in_progress = False
            if self.last_capture is not None and not self.capture_done.is_set():
                self.capture_done.set()

    def handle_status_change(self, _sender: int, data: bytearray) -> None:
        if not data:
            return
        status = data[0]

        if status == STATUS_COUNTDOWN_3:
            print("Starting capture in:")
            print("3...")
        elif status == STATUS_COUNTDOWN_2:
            print("2...")
        elif status == STATUS_COUNTDOWN_1:
            print("1...")
        elif status == STATUS_CAPTURING:
            print("GO! Perform your gesture now!")
            if not self.capture_in_progress:
                self.capture_in_progress = True
                self.received_chunks.clear()
                self.capture_done.clear()
        elif status == STATUS_COMPLETE:
            print("\nCapture finished!")
            self.capture_in_progress = False
            self.assemble_complete_capture()
        elif status == STATUS_ERROR:
            print("Capture error!")
            self.capture_in_progress = False
            self.capture_done.set()
        elif status == STATUS_READY:
            # Arduino ready
            self.capture_in_progress = False

    # Capture assembly
    def assemble_complete_capture(self) -> None:
        if not self.received_chunks:
            print("Warning: No data received")
            self.capture_done.set()
            return

        x_values: List[float] = []
        y_values: List[float] = []
        z_values: List[float] = []

        for seq in sorted(self.received_chunks.keys()):
            for x, y, z in self.received_chunks[seq]:
                x_values.append(x)
                y_values.append(y)
                z_values.append(z)

        capture = {
            "timestamp": int(time.time() * 1000),
            "samples": len(x_values),
            "x": x_values,
            "y": y_values,
            "z": z_values,
        }
        print(f"Received {capture['samples']} samples")

        self.last_capture = capture
        self.capture_in_progress = False
        self.received_chunks.clear()

        if not self.capture_done.is_set():
            self.capture_done.set()

        if self.current_letter:
            print(f"\nCapture complete for letter '{self.current_letter}'")
            print("Options:\n  save  - Save this capture\n  retry - Discard and capture again")
        else:
            print("No letter selected - capture discarded")

    # Control helpers
    async def start_capture(self) -> bool:
        if not self.client or not self.client.is_connected:
            print("Not connected to Arduino")
            return False
        if self.capture_in_progress:
            print("Capture already in progress")
            return False

        self.received_chunks.clear()
        self.last_capture = None
        self.capture_done.clear()

        try:
            await self.client.write_gatt_char(COMMAND_UUID, bytes([CMD_START_CAPTURE]))
            return True
        except Exception as exc:
            print(f"Failed to send command: {exc}")
            self.capture_done.set()
            return False

    def reset_state(self) -> None:
        self.capture_in_progress = False
        self.received_chunks.clear()
        self.last_capture = None
        self.capture_done.set()
        print("State reset")

    def print_stats(self) -> None:
        print("\nCollection Progress:")
        print("-" * 20)

        total = 0
        for letter in ['P', 'R', 'B', 'D', 'G', 'S', 'C', 'L', 'O', 'V', 'Z']:
            attempts = len(self.data.get("data", {}).get(letter, {}).get("captures", []))
            total += attempts
            print(f"{letter}: {attempts}/50")

        print(f"\nTotal: {total}/550\n")


async def main() -> None:
    print("=" * 50)
    print("  RASPBERRY PI GESTURE COLLECTOR")
    print("  Data Collection Only")
    print("=" * 50)

    collector = GestureDataCollector()
    if not await collector.connect():
        print("Failed to connect to Arduino")
        return

    print("\nCommands:")
    print("  train <LETTER>  - Set letter for training")
    print("  capture         - Start capture")
    print("  save            - Save last capture")
    print("  retry           - Retry last capture")
    print("  reset           - Reset capture state")
    print("  stats           - Show progress")
    print("  quit            - Exit")

    try:
        while True:
            cmd = (await asyncio.to_thread(input, "Command> ")).strip()

            if cmd == "quit":
                break
            if cmd.startswith("train "):
                letter = cmd.split()[1]
                if len(letter) == 1 and letter.isalpha():
                    collector.current_letter = letter.upper()
                    print(f"Training mode: Letter '{collector.current_letter}'")
                else:
                    print("Invalid letter")
                continue
            if cmd == "capture":
                if await collector.start_capture():
                    await collector.capture_done.wait()
                    print("Capture finished. Review status updates for details.")
                continue
            if cmd == "save":
                collector.save_last_capture()
                continue
            if cmd == "retry":
                if collector.last_capture and collector.current_letter:
                    print(f"Retrying capture for '{collector.current_letter}'...")
                    if await collector.start_capture():
                        await collector.capture_done.wait()
                        print("Capture finished. Review status updates for details.")
                else:
                    print("No capture to retry")
                continue
            if cmd == "stats":
                collector.print_stats()
                continue
            if cmd == "reset":
                collector.reset_state()
                continue

            print("Unknown command")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        await collector.disconnect()


if __name__ == "__main__":
    print("Requirements: pip install bleak")
    asyncio.run(main())
