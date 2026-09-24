#!/usr/bin/env python3

import rclpy
from geometry_msgs.msg import Pose
from xarm_msgs.srv import PlanSingleStraight, PlanExec

rclpy.init()
node = rclpy.create_node("test_move")

plan = node.create_client(PlanSingleStraight, "/xarm_straight_plan")
execute = node.create_client(PlanExec, "/xarm_exec_plan")

plan.wait_for_service()
execute.wait_for_service()

target = Pose()
target.position.x = 0.4
target.position.y = 0.0
target.position.z = 0.3

target.orientation.x = 1.0
target.orientation.w = 0.0

req = PlanSingleStraight.Request()
req.target = target

future = plan.call_async(req)
rclpy.spin_until_future_complete(node, future)

if future.result().success:
    exec_req = PlanExec.Request()
    exec_req.wait = True

    future = execute.call_async(exec_req)
    rclpy.spin_until_future_complete(node, future)

rclpy.shutdown()