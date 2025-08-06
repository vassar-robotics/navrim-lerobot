#!/usr/bin/env python3
"""
Minimal script to read joint positions from SO101 leader robot.

This script connects to the leader robot (5V) and continuously reads and displays
joint positions at 30 Hz.

Requirements:
- pyserial
- scservo_sdk (for Feetech motors)

Example usage:
```shell
python read_leader_positions.py
```
"""

import argparse
import platform
import time
from typing import Dict, List, Any


def find_robot_ports() -> List[str]:
    """Find USB serial ports that are likely to be robot/motor controllers."""
    try:
        from serial.tools import list_ports
    except ImportError:
        print("ERROR: pyserial not installed. Please install with: pip install pyserial")
        return []
    
    robot_ports = []
    
    if platform.system() == "Darwin":  # macOS
        for port in list_ports.comports():
            if "usbmodem" in port.device or "usbserial" in port.device:
                robot_ports.append(port.device)
    elif platform.system() == "Linux":
        for port in list_ports.comports():
            if "ttyUSB" in port.device or "ttyACM" in port.device:
                robot_ports.append(port.device)
    elif platform.system() == "Windows":
        for port in list_ports.comports():
            if "COM" in port.device:
                robot_ports.append(port.device)
    
    return robot_ports


class LeaderReader:
    """Minimal reader for SO101 leader robot with Feetech STS3215 motors."""
    
    # Feetech register addresses
    PRESENT_POSITION = 56
    PRESENT_VOLTAGE = 62
    
    def __init__(self, port: str, motor_ids: List[int], baudrate: int = 1000000):
        self.port = port
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.connected = False
        self.resolution = 4096  # STS3215 has 4096 resolution (0-4095)
        
        try:
            import scservo_sdk as scs  # type: ignore
            self.scs = scs
        except ImportError:
            raise RuntimeError("scservo_sdk not installed. Please install from Feetech SDK")
            
        self.port_handler: Any = None
        self.packet_handler: Any = None
        
    def connect(self) -> None:
        """Connect to the robot."""
        self.port_handler = self.scs.PortHandler(self.port)
        self.packet_handler = self.scs.PacketHandler(0)  # Protocol 0
        
        if not self.port_handler.openPort():
            raise RuntimeError(f"Failed to open port '{self.port}'")
            
        if not self.port_handler.setBaudRate(self.baudrate):
            raise RuntimeError(f"Failed to set baudrate to {self.baudrate}")
            
        # Test connection by pinging motors
        for motor_id in self.motor_ids:
            model_number, result, error = self.packet_handler.ping(self.port_handler, motor_id)
            if result != self.scs.COMM_SUCCESS:
                raise RuntimeError(f"Failed to ping motor {motor_id}")
                
        self.connected = True
        print(f"Connected to leader robot at {self.port}")
        
    def disconnect(self) -> None:
        """Disconnect from the robot."""
        if self.port_handler:
            self.port_handler.closePort()
        self.connected = False
        
    def read_voltage(self) -> float:
        """Read voltage from the first motor."""
        motor_id = self.motor_ids[0]
        
        read_result = self.packet_handler.read1ByteTxRx(
            self.port_handler, motor_id, self.PRESENT_VOLTAGE)
        
        # Handle different return formats
        if len(read_result) >= 3:
            raw_voltage, result, error = read_result
        elif len(read_result) == 2:
            raw_voltage, result = read_result
            error = 0
        else:
            raise RuntimeError(f"Unexpected read result format: {read_result}")
        
        if result == self.scs.COMM_SUCCESS:
            # Feetech motors report voltage in units of 0.1V
            return raw_voltage / 10.0
        else:
            raise RuntimeError(f"Failed to read voltage")
        
    def read_positions(self) -> Dict[int, int]:
        """Read current positions from all motors."""
        positions = {}
        
        for motor_id in self.motor_ids:
            read_result = self.packet_handler.read2ByteTxRx(
                self.port_handler, motor_id, self.PRESENT_POSITION)
            
            # Handle different return formats
            if len(read_result) >= 3:
                position, result, error = read_result
            elif len(read_result) == 2:
                position, result = read_result
                error = 0
            else:
                continue
            
            if result == self.scs.COMM_SUCCESS:
                positions[motor_id] = position
                
        return positions


def find_leader_port(motor_ids: List[int]) -> str:
    """Find the leader robot port by checking for 5V voltage."""
    ports = find_robot_ports()
    
    if len(ports) == 0:
        raise RuntimeError("No robot ports detected. Please ensure leader robot is connected.")
    
    print(f"Found {len(ports)} potential robot port(s): {ports}")
    print("Checking voltage to identify leader robot (5V)...")
    
    for port in ports:
        try:
            reader = LeaderReader(port, motor_ids)
            reader.connect()
            voltage = reader.read_voltage()
            reader.disconnect()
            
            # Check if this is the leader (5V)
            if 4.5 <= voltage <= 5.5:
                print(f"✓ Found leader robot at {port} (voltage: {voltage:.1f}V)")
                return port
            else:
                print(f"  {port}: {voltage:.1f}V - Not leader")
                
        except Exception as e:
            print(f"  {port}: Failed to check - {e}")
            
    raise RuntimeError("No leader robot (5V) found!")


def display_positions(positions: Dict[int, int], resolution: int) -> None:
    """Display positions in a formatted table."""
    print("\n" + "="*40)
    print(f"{'Motor':<8} | {'Position':>8} | {'Percent':>8}")
    print("-"*40)
    
    for motor_id in sorted(positions.keys()):
        position = positions[motor_id]
        percent = (position / (resolution - 1)) * 100
        print(f"{motor_id:<8} | {position:>8} | {percent:>6.1f}%")
    
    print("="*40)


def move_cursor_up(lines: int) -> None:
    """Move terminal cursor up by specified number of lines."""
    print(f"\033[{lines}A", end="")


def main():
    parser = argparse.ArgumentParser(description="Read positions from SO101 leader robot")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6",
                       help="Comma-separated list of motor IDs (default: 1,2,3,4,5,6)")
    parser.add_argument("--port", type=str,
                       help="Serial port for leader robot (auto-detect if not specified)")
    parser.add_argument("--hz", type=int, default=30,
                       help="Display frequency in Hz (default: 30)")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [int(id.strip()) for id in args.motor_ids.split(",")]
    
    # Find leader port
    if args.port:
        leader_port = args.port
        print(f"Using specified port: {leader_port}")
    else:
        try:
            leader_port = find_leader_port(motor_ids)
        except RuntimeError as e:
            print(f"ERROR: {e}")
            return
    
    # Create reader
    reader = LeaderReader(leader_port, motor_ids)
    
    try:
        # Connect to leader
        reader.connect()
        
        print(f"\nReading positions at {args.hz} Hz")
        print("Press Ctrl+C to stop\n")
        
        # Main loop
        loop_time = 1.0 / args.hz
        first_display = True
        
        while True:
            start_time = time.perf_counter()
            
            # Read positions
            positions = reader.read_positions()
            
            if positions:
                # Display positions
                display_positions(positions, reader.resolution)
                
                # Move cursor up for next iteration (after first display)
                if not first_display:
                    move_cursor_up(len(positions) + 5)
                else:
                    first_display = False
            
            # Maintain loop rate
            elapsed = time.perf_counter() - start_time
            if elapsed < loop_time:
                time.sleep(loop_time - elapsed)
                
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        # Always disconnect
        reader.disconnect()
        print("Disconnected from leader robot")


if __name__ == "__main__":
    main() 