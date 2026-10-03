import time
import math
from gz.transport13 import Node
from gz.msgs10.navsat_pb2 import NavSat

R_EARTH = 6378137.0  # WGS-84 equatorial radius


class GNSSSpooferNode:
    def __init__(self, mode="nominal", attack_start_time=25.0):
        # Collection clock: elapsed wall time after the first NavSat message.
        self.node = Node()
        self.mode = mode.lower()
        self.t_start = attack_start_time
        self.init_time = None
        self.last_log_time = 0.0
        self.msg_count = 0

        self.sub_topic = "/world/default/model/x500_0/link/base_link/sensor/navsat_sensor/navsat_raw"
        self.pub_topic = "/world/default/model/x500_0/link/base_link/sensor/navsat_sensor/navsat"

        self.pub = self.node.advertise(self.pub_topic, NavSat)
        self.node.subscribe(NavSat, self.sub_topic, self.callback)
        print(f"[*] GNSS Spoofer initialized in [{self.mode.upper()}] mode.")

    def compute_offsets(self, t_rel):
        """Returns (d_east_meters, v_east_mps)"""
        if self.mode == "nominal" or t_rel <= 0.0:
            return 0.0, 0.0

        if self.mode == "step_attack":
            return 15.0, 5.0
        elif self.mode == "ramp_attack":
            a = 0.25
            d_east = 0.5 * a * (t_rel ** 2)
            v_east = a * t_rel
            return d_east, v_east
        elif self.mode == "stealth_attack":
            a = 0.05
            d_east = 0.5 * a * (t_rel ** 2)
            v_east = a * t_rel
            return d_east, v_east
        else:
            return 0.0, 0.0

    def callback(self, msg: NavSat):
        now = time.time()
        if self.init_time is None:
            self.init_time = now
            print("[+] Interceptor connected! Forwarding NavSat packets to PX4...")

        t_rel = now - (self.init_time + self.t_start)
        d_east, v_east = self.compute_offsets(t_rel)

        spoofed_msg = NavSat()
        spoofed_msg.CopyFrom(msg)

        if d_east > 0.0:
            lat_rad = math.radians(msg.latitude_deg)
            # Standard equirectangular projection for local metric offset
            delta_lon_deg = (d_east / (R_EARTH * math.cos(lat_rad))) * (180.0 / math.pi)

            # Apply position and velocity spoofing directly
            spoofed_msg.longitude_deg += delta_lon_deg
            spoofed_msg.velocity_east += v_east

        self.pub.publish(spoofed_msg)
        self.msg_count += 1

        # Periodic status logger
        if now - self.last_log_time >= 5.0:
            status = "ATTACK ACTIVE" if (self.mode != "nominal" and t_rel > 0) else "NOMINAL"
            print(f"[{status}] Pkts: {self.msg_count} | d_east: {d_east:.2f} m | v_east: {v_east:.2f} m/s")
            self.last_log_time = now

if __name__ == "__main__":
    import sys
    attack_type = sys.argv[1] if len(sys.argv) > 1 else "nominal"
    spoofer = GNSSSpooferNode(mode=attack_type, attack_start_time=25.0)

    try:
        while True:
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("[!] Stopping Spoofer.")
