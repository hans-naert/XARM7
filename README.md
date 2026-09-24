# xArm7 ROS 2 Simulation

A Docker-based simulation environment for the xArm7 robotic arm using ROS 2 Humble and MoveIt 2.

## Demo

https://github.com/user-attachments/assets/cb43e891-b189-4561-9a3b-d466995449d2
> *Drag the interactive marker to set a goal pose, then click "Plan & Execute"*

## Prerequisites

- Windows 10/11 with WSL2
- Docker Desktop with WSL2 backend
- WSLg (included in Windows 11, or Windows 10 build 21364+)

## Quick Start

```bash
# Build the container
docker-compose build

# Start the simulation
docker-compose up
```

With no arguments provided the simulation launches:
- **RViz2** - Visualization and motion planning interface
- **MoveIt 2** - Motion planning framework
- **ros2_control** - Robot controller interface

Open a shell in a second terminal window, to test your scripts.
```bash
# Start a bash shell into your container
docker exec -it xarm7-sim bash

# Source ROS inside the new shell
source /opt/ros/humble/setup.bash
source /home/ubuntu/ros2_ws/install/setup.bash
```

## Moving the Robot

### Method 1: RViz Interactive Markers (Recommended)

1. In RViz, look for the **interactive marker** (colored sphere/arrows) at the robot's end effector
2. **Drag the marker** to set a target pose
3. Click **"Plan & Execute"** in the MotionPlanning panel (left side)

### Method 2: MoveIt Motion Planning Panel

1. In RViz's **MotionPlanning** panel:
   - Go to the **"Planning"** tab
   - Set **Goal State** to a predefined pose or "random valid"
   - Click **"Plan"** to preview the trajectory
   - Click **"Execute"** to move the robot

### Method 3: Command Line (ros2 action)

Open a terminal inside the container:

```bash
docker exec -it xarm7-sim bash
```

Then send a joint trajectory goal:

```bash
# Source the workspace
source /opt/ros/humble/setup.bash
source /home/ubuntu/ros2_ws/install/setup.bash

# Move to a specific joint configuration (7 joints, in radians)
ros2 action send_goal /xarm7_traj_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{
    trajectory: {
      joint_names: [joint1, joint2, joint3, joint4, joint5, joint6, joint7],
      points: [
        { positions: [0.0, 0.0, 0.0, 0.5, 0.0, 0.5, 0.0], time_from_start: { sec: 3 } }
      ]
    }
  }"
```

### Method 4: Python Script

Create a Python script inside the container:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from moveit_msgs.action import MoveGroup
from geometry_msgs.msg import PoseStamped

# Use MoveIt's Python API for more complex motion planning
# See: https://moveit.picknik.ai/main/doc/examples/examples.html
```

## Useful Commands

```bash
# Enter the container
docker exec -it xarm7-sim bash

# List available topics
ros2 topic list

# View joint states
ros2 topic echo /joint_states

# List available actions
ros2 action list

# Check controller status
ros2 control list_controllers
```

## File Structure

```
XARM7/
├── docker-compose.yml   # Container configuration
├── Dockerfile           # Image build instructions
├── cyclonedds.xml       # DDS configuration (optional)
├── entrypoint.sh        # Startup script
└── README.md            # This file
```

## Troubleshooting

### RViz doesn't display / black screen
- Ensure WSLg is working: `echo $DISPLAY` should show `:0`
- Try: `export LIBGL_ALWAYS_SOFTWARE=1`

### Nodes crash with SIGABRT
- Check Docker has enough memory (Settings → Resources → 4GB+)
- Ensure `ipc: host` is set in docker-compose.yml

### Cannot connect to robot
- This is a **simulation** - no real robot connection needed
- The fake controller simulates joint movements

## Stopping the Simulation

```bash
docker-compose down
```

## License

This project uses:
- [xarm_ros2](https://github.com/xArm-Developer/xarm_ros2) - xArm ROS 2 packages
- [MoveIt 2](https://moveit.ros.org/) - Motion planning framework
- [ROS 2 Humble](https://docs.ros.org/en/humble/) - Robot Operating System
