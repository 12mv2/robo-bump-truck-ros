#!/usr/bin/env python3
"""Publish a folder of image files as sensor_msgs/Image so a perception node can be
tested with recorded frames and no camera.

    python3 tools/replay_images.py /path/to/frames --rate 5 --loop
    python3 tools/replay_images.py /path/to/frames --topic /image_raw --resize 640x480

Frames are sorted by filename and published as bgr8 with a monotonically increasing
header stamp. Needs rclpy, python3-opencv and numpy only (no cv_bridge).
"""
import argparse, os, sys, time
import cv2, numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

EXTS = {".jpg", ".jpeg", ".png", ".bmp"}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--topic", default="/image_raw")
    ap.add_argument("--rate", type=float, default=5.0, help="frames per second (default 5, the truck's capture rate)")
    ap.add_argument("--loop", action="store_true", help="repeat forever instead of stopping at the last frame")
    ap.add_argument("--resize", default=None, help="WxH, e.g. 640x480, to match the node's expected input")
    ap.add_argument("--frame-id", default="camera")
    a = ap.parse_args()

    files = sorted(f for f in os.listdir(a.folder)
                   if os.path.splitext(f)[1].lower() in EXTS and not f.startswith("._"))  # skip macOS AppleDouble files
    if not files:
        sys.exit(f"no image files in {a.folder}")
    size = tuple(int(x) for x in a.resize.lower().split("x")) if a.resize else None

    rclpy.init()
    node = Node("replay_images")
    pub = node.create_publisher(Image, a.topic, 5)
    node.get_logger().info(f"{len(files)} frames from {a.folder} -> {a.topic} at {a.rate} Hz" + (" (loop)" if a.loop else ""))

    period = 1.0 / a.rate
    n = 0
    try:
        while rclpy.ok():
            for f in files:
                t0 = time.monotonic()
                img = cv2.imread(os.path.join(a.folder, f), cv2.IMREAD_COLOR)
                if img is None:
                    node.get_logger().warning(f"unreadable: {f}"); continue
                if size: img = cv2.resize(img, size)
                msg = Image()
                msg.header.stamp = node.get_clock().now().to_msg()
                msg.header.frame_id = a.frame_id
                msg.height, msg.width = img.shape[:2]
                msg.encoding = "bgr8"; msg.is_bigendian = 0; msg.step = msg.width * 3
                msg.data = np.ascontiguousarray(img).tobytes()
                pub.publish(msg); n += 1
                if n % 50 == 0: node.get_logger().info(f"published {n}")
                rclpy.spin_once(node, timeout_sec=0)
                time.sleep(max(0.0, period - (time.monotonic() - t0)))
            if not a.loop: break
        node.get_logger().info(f"done, {n} frames")
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try: rclpy.shutdown()
        except Exception: pass   # already shut down by a signal

if __name__ == "__main__":
    main()
