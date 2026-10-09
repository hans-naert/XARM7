#!/usr/bin/env python3
"""Hold a key to jog the xArm. Releasing the key stops that motion.

Start the arm with MoveIt Servo first:

    docker compose run --rm xarm7-sim servo

Then, in another shell inside that container:

    python3 /home/ubuntu/src/keypad_ctrl.py

Keys, in the robot base frame (link_base):

    8  forward     2  backward
    4  left        6  right
    -  up          +  down   (the = key also moves down)

Numpad keys and the number row both work. q quits.
"""

import fcntl
import glob
import os
import select
import struct
import sys
import termios
import threading
import time
import tty

import rclpy
from geometry_msgs.msg import TwistStamped
from std_srvs.srv import Trigger

# Flip an axis when you are sitting in front of the robot and that
# direction comes out backwards.
SWAP_UP_DOWN = False
SWAP_FORWARD_BACKWARD = False
SWAP_LEFT_RIGHT = False

LINEAR_SPEED = 0.05  # m/s
PUBLISH_HZ = 30.0
COMMAND_FRAME = "link_base"
TWIST_TOPIC = "/servo_server/delta_twist_cmds"

# Linux evdev codes. Press and release are separate events, so a held
# key keeps the arm moving and a release stops it on the next cycle.
KEY_ESC = 1
KEY_2 = 3
KEY_4 = 5
KEY_6 = 7
KEY_8 = 9
KEY_MINUS = 12
KEY_EQUAL = 13
KEY_Q = 16
KEY_KP2 = 80
KEY_KP4 = 75
KEY_KP6 = 77
KEY_KP8 = 72
KEY_KPMINUS = 74
KEY_KPPLUS = 78

# axis, sign. +x is forward, +y is the robot's left, +z is up.
KEY_TO_MOTION = {
    KEY_8: ("x", 1.0),
    KEY_KP8: ("x", 1.0),
    KEY_2: ("x", -1.0),
    KEY_KP2: ("x", -1.0),
    KEY_4: ("y", 1.0),
    KEY_KP4: ("y", 1.0),
    KEY_6: ("y", -1.0),
    KEY_KP6: ("y", -1.0),
    KEY_MINUS: ("z", 1.0),
    KEY_KPMINUS: ("z", 1.0),
    KEY_EQUAL: ("z", -1.0),
    KEY_KPPLUS: ("z", -1.0),
}

# Used only when /dev/input is not available. A terminal reports key
# repeat, not key-up, so motion stops once repeats stop arriving.
CHAR_TO_MOTION = {
    "8": ("x", 1.0),
    "2": ("x", -1.0),
    "4": ("y", 1.0),
    "6": ("y", -1.0),
    "-": ("z", 1.0),
    "+": ("z", -1.0),
    "=": ("z", -1.0),
}
RELEASE_TIMEOUT = 0.15

EV_KEY = 0x01
EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)


def scaled(axis, direction):
    if axis == "x" and SWAP_FORWARD_BACKWARD:
        direction = -direction
    elif axis == "y" and SWAP_LEFT_RIGHT:
        direction = -direction
    elif axis == "z" and SWAP_UP_DOWN:
        direction = -direction
    return direction * LINEAR_SPEED


class MotionState:
    def __init__(self):
        self._lock = threading.Lock()
        self._held = {}
        self._last_char = None
        self._last_char_time = 0.0
        self.use_terminal = False
        self.quit = False

    def set_key(self, code, down):
        with self._lock:
            if down:
                if code in KEY_TO_MOTION:
                    self._held[code] = KEY_TO_MOTION[code]
            else:
                self._held.pop(code, None)

    def set_char(self, char):
        with self._lock:
            self._last_char = CHAR_TO_MOTION.get(char)
            self._last_char_time = time.monotonic()

    def velocity(self):
        vx = vy = vz = 0.0
        with self._lock:
            if self.use_terminal:
                motions = []
                if self._last_char and time.monotonic() - self._last_char_time <= RELEASE_TIMEOUT:
                    motions = [self._last_char]
            else:
                motions = list(self._held.values())
        for axis, direction in motions:
            speed = scaled(axis, direction)
            if axis == "x":
                vx += speed
            elif axis == "y":
                vy += speed
            else:
                vz += speed
        return vx, vy, vz


def _eviocgbit(ev, length):
    return (2 << 30) | (length << 16) | (ord("E") << 8) | (0x20 + ev)


def _has_key(fd, code):
    nbytes = (code // 8) + 1
    buf = bytearray(nbytes)
    fcntl.ioctl(fd, _eviocgbit(EV_KEY, nbytes), buf)
    return bool(buf[code // 8] & (1 << (code % 8)))


def keyboard_devices():
    found = []
    for path in sorted(glob.glob("/dev/input/event*")):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            continue
        try:
            if _has_key(fd, KEY_8) or _has_key(fd, KEY_KP8):
                found.append(fd)
            else:
                os.close(fd)
        except OSError:
            os.close(fd)
    return found


def read_evdev(state, fds):
    while not state.quit:
        readable, _, _ = select.select(fds, [], [], 0.05)
        for fd in readable:
            try:
                data = os.read(fd, EVENT_SIZE * 64)
            except OSError:
                continue
            for offset in range(0, len(data) - EVENT_SIZE + 1, EVENT_SIZE):
                _, _, ev_type, code, value = struct.unpack_from(EVENT_FORMAT, data, offset)
                if ev_type != EV_KEY:
                    continue
                if code in (KEY_Q, KEY_ESC) and value == 1:
                    state.quit = True
                    return
                if code in KEY_TO_MOTION:
                    state.set_key(code, value != 0)


def read_terminal(state, fd):
    while not state.quit:
        readable, _, _ = select.select([fd], [], [], 0.05)
        if not readable:
            continue
        char = os.read(fd, 1).decode("utf-8", errors="ignore")
        if char in ("q", "Q", "\x03", "\x1b"):
            state.quit = True
            return
        if char in CHAR_TO_MOTION:
            state.set_char(char)


def send_twist(node, publisher, vx, vy, vz):
    msg = TwistStamped()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.header.frame_id = COMMAND_FRAME
    msg.twist.linear.x = vx
    msg.twist.linear.y = vy
    msg.twist.linear.z = vz
    publisher.publish(msg)


def on_timer(node, publisher, state):
    if state.quit:
        send_twist(node, publisher, 0.0, 0.0, 0.0)
        rclpy.shutdown()
        return
    vx, vy, vz = state.velocity()
    send_twist(node, publisher, vx, vy, vz)


def start_servo(node):
    client = node.create_client(Trigger, "/servo_server/start_servo")
    print("Waiting for MoveIt Servo...")
    if not client.wait_for_service(timeout_sec=15.0):
        print("Servo is not running.")
        print("Start it with: docker compose run --rm xarm7-sim servo")
        return False
    future = client.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, future, timeout_sec=5.0)
    return True


def main():
    rclpy.init()
    node = rclpy.create_node("keypad_ctrl")
    publisher = node.create_publisher(TwistStamped, TWIST_TOPIC, 10)
    if not start_servo(node):
        node.destroy_node()
        rclpy.shutdown()
        return 1

    state = MotionState()
    fds = keyboard_devices()
    saved_term = None
    stdin_fd = None
    if fds:
        print("Reading the keyboard directly. Release a key and the arm stops.")
        print("Keys move the arm even when this terminal is not focused.")
        thread = threading.Thread(target=read_evdev, args=(state, fds), daemon=True)
    else:
        if not sys.stdin.isatty():
            print("No keyboard device, and this shell is not interactive.")
            print("Run: docker exec -it <container-name> bash")
            node.destroy_node()
            rclpy.shutdown()
            return 1
        print("No keyboard device found. Using this terminal.")
        print("Hold a key until it repeats. The arm stops when the repeats stop.")
        state.use_terminal = True
        stdin_fd = sys.stdin.fileno()
        saved_term = termios.tcgetattr(stdin_fd)
        tty.setcbreak(stdin_fd)
        thread = threading.Thread(target=read_terminal, args=(state, stdin_fd), daemon=True)

    print("8/2 forward/back   4/6 left/right   -/+= up/down   q quits")
    thread.start()
    node.create_timer(1.0 / PUBLISH_HZ, lambda: on_timer(node, publisher, state))
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        state.quit = True
    finally:
        state.quit = True
        thread.join(timeout=0.3)
        if saved_term is not None:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, saved_term)
        for fd in fds:
            os.close(fd)
        if rclpy.ok():
            for _ in range(5):
                send_twist(node, publisher, 0.0, 0.0, 0.0)
                time.sleep(0.02)
            node.destroy_node()
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
