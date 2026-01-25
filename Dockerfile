# syntax=docker/dockerfile:1
FROM tiryoh/ros2-desktop-vnc:humble

# Step 1: Install core tools + Stability components (CycloneDDS)
RUN apt-get update && apt-get install -y \
    git \
    python3-rosdep \
    ros-humble-moveit \
    ros-humble-ros2-control \
    ros-humble-ros2-controllers \
    ros-humble-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*

# Step 2: Build the xArm workspace INTO the image
WORKDIR /home/ubuntu/ros2_ws
RUN mkdir src && cd src && \
    git clone --depth 1 https://github.com/xArm-Developer/xarm_ros2.git --recursive

# Install dependencies and build
RUN rosdep update && \
    rosdep install --from-paths src --ignore-src -y --rosdistro humble || true && \
    /bin/bash -c "source /opt/ros/humble/setup.bash && colcon build --symlink-install"

# Step 3: Copy config files (changes here trigger fast rebuild)
COPY cyclonedds.xml /cyclonedds.xml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]