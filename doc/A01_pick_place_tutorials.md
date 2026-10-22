# MoveIt attach/detach tutorials

The tutorials below use the simulated Panda arm supplied by MoveIt, not the
xArm7. They all run two ROS launch files in two shells **inside the same
container**.

## One-time setup

Build the image and the tutorial packages from the repository root:

```bash
docker compose build
docker compose run --rm xarm7-ctl bash -lc \
  'cd /home/ubuntu/overlay_ws && colcon build --symlink-install'
```

The overlay build is stored in the `overlay_ws` Docker volume. Rebuild it after
changing tutorial C++ code or adding packages. When the build finishes, this
temporary container exits and `--rm` removes it automatically. There is no
running container to enter at this point.

## Two-terminal workflow

Choose one of the demos below and run its terminal 1 command first. That command
creates a container for the `xarm7-ctl` Compose service and keeps it running
while its MoveIt backend is active.

Only after terminal 1 is running, open host terminal 2 and enter the same
service container with:

```bash
docker compose exec xarm7-ctl bash
```

`docker compose exec` does not invoke this image's entrypoint, so source all
three workspaces in the second shell:

```bash
source /opt/ros/humble/setup.bash
source /home/ubuntu/ros2_ws/install/setup.bash
source /home/ubuntu/overlay_ws/install/setup.bash
```

This works without knowing the generated container name because Compose tracks
the container by its `xarm7-ctl` service label. It assumes only one running
container for that service; stop old tutorial containers first if Compose finds
more than one.

## 1. Planning Scene ROS API

This is the smallest attach/detach example. It adds a box to the planning
scene, attaches it to the Panda hand, detaches it, and removes it. The arm does
not transport the box.

In host terminal 1, start MoveIt and RViz:

```bash
docker compose run --rm xarm7-ctl \
  ros2 launch moveit2_tutorials move_group.launch.py
```

After terminal 1 is running, open host terminal 2, enter the service container
and source the workspaces as described in the two-terminal workflow above.
Then run:

```bash
ros2 launch moveit2_tutorials planning_scene_ros_api_tutorial.launch.py
```

Advance the demo with **Next** in the RViz **RvizVisualToolsGui** panel. You can
also select RViz's **Key Tool** and press `0` while RViz has focus.

## 2. Move Group Interface

This broader MoveGroupInterface demonstration plans several arm motions, adds
a collision box, plans around it, attaches an object to the wrist, moves the
arm while carrying it, then detaches and removes the objects.

In host terminal 1, start MoveIt and RViz:

```bash
docker compose run --rm xarm7-ctl \
  ros2 launch moveit2_tutorials move_group.launch.py
```

After terminal 1 is running, open host terminal 2, enter the service container
and source the workspaces as described in the two-terminal workflow above.
Then run:

```bash
ros2 launch moveit2_tutorials move_group_interface_tutorial.launch.py
```

Advance each stage with **Next** in **RvizVisualToolsGui**, or with the RViz
**Key Tool** and the `0` key.

## 3. MoveIt Task Constructor pick and place

This is the most complete example. It plans a staged pick-and-place task:
approach the object, open and close the gripper, attach and lift the object,
transport it, place and detach it, retreat, and return home.

In host terminal 1, start the MTC-enabled MoveIt backend and RViz:

```bash
docker compose run --rm xarm7-ctl \
  ros2 launch moveit2_tutorials mtc_demo.launch.py
```

After terminal 1 is running, open host terminal 2, enter the service container
and source the workspaces as described in the two-terminal workflow above.
Then run:

```bash
ros2 launch moveit2_tutorials pick_place_demo.launch.py
```

The node plans the task and executes its first solution. The RViz **Motion
Planning Tasks** panel shows the individual stages and candidate solutions.

## Stopping a demo

Stop the tutorial in terminal 2 with `Ctrl+C`, then stop the backend in terminal
1 with `Ctrl+C`. Because the container was started with `--rm`, Docker removes
it after the backend exits.
