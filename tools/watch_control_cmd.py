#!/usr/bin/env python3
"""Print every control_interfaces/ControlMsg on a topic with its arrival rate.
Use it to confirm a perception node is publishing while frames are replayed.

    python3 tools/watch_control_cmd.py                 # listens on /control_cmd
    python3 tools/watch_control_cmd.py --topic /x/cmd --seconds 30
"""
import argparse, time
import rclpy
from rclpy.node import Node
from control_interfaces.msg import ControlMsg

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="/control_cmd")
    ap.add_argument("--seconds", type=float, default=0, help="stop after N seconds (0 = until Ctrl-C)")
    a = ap.parse_args()
    rclpy.init(); node = Node("watch_control_cmd")
    st = {"n": 0, "valid": 0, "t0": time.monotonic(), "last": None}
    def cb(m):
        st["n"] += 1; st["valid"] += int(m.listen_to_steering)
        dt = time.monotonic() - st["t0"]
        print(f"#{st['n']:5d} {dt:7.2f}s  curvature={m.desired_curvature:+.4f} 1/m  speed={m.desired_speed:.2f} m/s  "
              f"steer={int(m.listen_to_steering)} speed_ok={int(m.listen_to_speed)}  avg {st['n']/dt:.2f} Hz")
    node.create_subscription(ControlMsg, a.topic, cb, 10)
    print(f"listening on {a.topic} ...")
    try:
        while rclpy.ok() and (a.seconds == 0 or time.monotonic() - st["t0"] < a.seconds):
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        pass
    dt = time.monotonic() - st["t0"]
    print(f"\n{st['n']} messages in {dt:.1f}s = {st['n']/dt if dt else 0:.2f} Hz; {st['valid']} with listen_to_steering=true")
    node.destroy_node()
    try: rclpy.shutdown()
    except Exception: pass

if __name__ == "__main__":
    main()
