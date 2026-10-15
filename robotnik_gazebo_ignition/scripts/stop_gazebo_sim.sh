#!/usr/bin/env bash
set -euo pipefail

FORCE=false
ALL=false

for arg in "$@"; do
  case "$arg" in
    --force)
      FORCE=true
      ;;
    --all)
      ALL=true
      ;;
    -h|--help)
      echo "Usage: $0 [--force] [--all]"
      echo
      echo "Stops lingering Gazebo simulation processes."
      echo "  --force   Send SIGKILL after SIGINT/SIGTERM if processes remain."
      echo "  --all     Also stop common ROS simulation helper processes."
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg"
      exit 1
      ;;
  esac
done

echo "[stop_gazebo_simulation] Stopping Gazebo simulation processes..."

# Gazebo server / GUI. Depending on the Gazebo version, the visible process may
# be either 'gz sim', 'ign gazebo', or a ruby wrapper running gz.
GAZEBO_PATTERNS=(
  "gz sim"
  "ign gazebo"
  "ruby.*gz.*sim"
)

for pattern in "${GAZEBO_PATTERNS[@]}"; do
  pkill -INT -f "$pattern" 2>/dev/null || true
done

sleep 2

for pattern in "${GAZEBO_PATTERNS[@]}"; do
  pkill -TERM -f "$pattern" 2>/dev/null || true
done

if [ "$FORCE" = true ]; then
  sleep 1
  for pattern in "${GAZEBO_PATTERNS[@]}"; do
    pkill -KILL -f "$pattern" 2>/dev/null || true
  done
fi

if [ "$ALL" = true ]; then
  echo "[stop_gazebo_simulation] Stopping common ROS simulation helper processes..."

  ROS_SIM_PATTERNS=(
    "parameter_bridge"
    "robot_state_publisher"
    "rviz2"
    "spawner"
  )

  for pattern in "${ROS_SIM_PATTERNS[@]}"; do
    pkill -INT -f "$pattern" 2>/dev/null || true
  done

  sleep 1

  for pattern in "${ROS_SIM_PATTERNS[@]}"; do
    pkill -TERM -f "$pattern" 2>/dev/null || true
  done

  if [ "$FORCE" = true ]; then
    sleep 1
    for pattern in "${ROS_SIM_PATTERNS[@]}"; do
      pkill -KILL -f "$pattern" 2>/dev/null || true
    done
  fi
fi

echo "[stop_gazebo_simulation] Remaining Gazebo processes:"
pgrep -af "gz sim|ign gazebo|ruby.*gz.*sim" || true

echo "[stop_gazebo_simulation] Remaining ros2_control simulation nodes:"
ros2 node list 2>/dev/null | grep -E "controller_manager|gz_ros_control|joint_state_broadcaster|robotnik_base_control" || true

echo "[stop_gazebo_simulation] Done."
