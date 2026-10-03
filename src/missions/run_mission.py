import sys
import time
import math
from pymavlink import mavutil

def log(msg):
    print(msg, flush=True)

def get_current_position(master):
    """Wait for and return the latest local position (x, y, z) in meters."""
    msg = master.recv_match(type='LOCAL_POSITION_NED', blocking=True, timeout=2.0)
    if msg:
        return msg.x, msg.y, msg.z
    return None

def send_setpoint(master, target_x, target_y, target_z):
    """Stream setpoint to vehicle using local NED coordinate frame."""
    master.mav.set_position_target_local_ned_send(
        0, master.target_system, master.target_component,
        mavutil.mavlink.MAV_FRAME_LOCAL_NED,
        0b0000111111111000,  # Control position only
        target_x, target_y, target_z,
        0, 0, 0,             # Velocities
        0, 0, 0,             # Accelerations
        0, 0                 # Yaw, Yaw rate
    )

def navigate_to(master, target_x, target_y, target_z, tolerance=0.5, timeout=25.0):
    """Stream setpoints until within tolerance radius of target coordinate."""
    start_time = time.time()
    log(f"Navigating to Target: x={target_x}m, y={target_y}m, z={target_z}m (Radius: {tolerance}m)")

    while True:
        # Stream setpoint continuously (PX4 requires >= 2Hz stream)
        send_setpoint(master, target_x, target_y, target_z)

        pos = get_current_position(master)
        if pos:
            cur_x, cur_y, cur_z = pos
            dist = math.sqrt((cur_x - target_x)**2 + (cur_y - target_y)**2 + (cur_z - target_z)**2)

            # Distance feedback every 1 second
            if int(time.time() * 2) % 2 == 0:
                print(f"\r  Current: ({cur_x:.1f}, {cur_y:.1f}, {cur_z:.1f}) -> Target Dist: {dist:.2f}m   ", end="", flush=True)

            if dist <= tolerance:
                print()  # newline
                log(f"Reached Target: ({cur_x:.2f}, {cur_y:.2f}, {cur_z:.2f})")
                break

        if (time.time() - start_time) > timeout:
            print()
            log(f"Warning: Waypoint timed out after {timeout}s.")
            break

        time.sleep(0.1)  # 10Hz loop rate

def run_flight():
    log("Connecting to PX4 SITL on UDP 14540...")
    master = mavutil.mavlink_connection('udpin:0.0.0.0:14540')
    master.wait_heartbeat()
    log("Heartbeat detected.")

    # 1. Arm vehicle
    log("Arming...")
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 1, 0, 0, 0, 0, 0, 0
    )
    time.sleep(2)

    # 2. Takeoff
    log("Commanding Takeoff to 5m...")
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, 0, 0, 0, 5
    )
    # Wait until vehicle reaches ~5m altitude
    navigate_to(master, target_x=0.0, target_y=0.0, target_z=-5.0, tolerance=0.5, timeout=12.0)

    # 3. Stream initial setpoint before switching to OFFBOARD mode
    log("Streaming initial setpoint to prime Offboard mode...")
    for _ in range(15):
        send_setpoint(master, 0.0, 0.0, -5.0)
        time.sleep(0.1)

    # 4. Switch to OFFBOARD mode
    log("Switching to OFFBOARD mode...")
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        6,  # PX4 Custom Main Mode: OFFBOARD = 6
        0, 0, 0, 0, 0
    )
    time.sleep(1)

    # 5. Execute 10m x 10m Waypoint Box Pattern
    waypoints = [
        (10.0,  0.0, -5.0),
        (10.0, 10.0, -5.0),
        ( 0.0, 10.0, -5.0),
        ( 0.0,  0.0, -5.0)
    ]

    for wp in waypoints:
        navigate_to(master, target_x=wp[0], target_y=wp[1], target_z=wp[2], tolerance=0.5, timeout=10.0)
        time.sleep(1.0)  # Brief hover stability check at vertex

    # 6. Land
    log("Mission complete. Commanding Land...")
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    log("Landed. Flight routine finished.")

if __name__ == '__main__':
    run_flight()
