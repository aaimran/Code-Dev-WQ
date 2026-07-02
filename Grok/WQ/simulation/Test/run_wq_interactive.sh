#!/bin/bash

echo "========================================"
echo "WaveQlab3D Docker Interactive Session"
echo "========================================"
echo ""

# Create logs directory if it doesn't exist
mkdir -p /work/aimran/logs

# Start Docker daemon (rootless)
echo "Starting Docker daemon..."
/opt/ohpc/pub/apps/docker/start_rootless_docker.sh --quiet
sleep 2

# Verify Docker is running
docker ps > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Docker daemon failed to start"
    exit 1
fi

echo "Docker daemon started successfully"
echo ""

# Set DOCKER_HOST for rootless Docker
export DOCKER_HOST=unix:///scratch/tmp/xdg_runtime_dir_$UID/docker.sock

# Run interactive Docker container
echo "Launching interactive Docker container..."
echo "Inside the container, you can:"
echo "  - Navigate to /scratch/aimran/WQ/simulation/Test"
echo "  - Run: mpirun -np 40 /app/build/waveqlab3d ./input/test-1upx_100m.in"
echo "  - Or: /app/build/waveqlab3d ./input/test-1upx_100m.in (single process)"
echo ""

docker run --rm -it \
    -v /work/aimran:/work \
    -v /scratch/aimran:/scratch \
    -w /scratch/aimran/WQ/simulation/Test \
    wq-app:punakha-cpu-v1 bash

# Stop Docker daemon when exiting container
echo ""
echo "Stopping Docker daemon..."
/opt/ohpc/pub/apps/docker/stop_rootless_docker.sh --quiet 2>/dev/null || true

echo "========================================"
echo "Docker session ended"
echo "========================================"
