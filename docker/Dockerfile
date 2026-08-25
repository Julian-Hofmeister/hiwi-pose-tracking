FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive \
    SHELL=/bin/bash \
    PYTHONUNBUFFERED=1 \
    RTMPOSE_VENV=/opt/rtmpose

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-colcon-common-extensions \
        python3-numpy \
        python3-opencv \
        python3-pytest \
        python3-venv \
        python3-pip \
        python3-dev \
        git \
        ninja-build \
        build-essential \
        libgl1 \
        libglib2.0-0 \
        wget \
        ca-certificates \
        ros-jazzy-cv-bridge \
        ros-jazzy-launch-ros \
        ros-jazzy-sensor-msgs \
    && rm -rf /var/lib/apt/lists/*

COPY docker/install-mmpose.sh /tmp/install-mmpose.sh
RUN chmod +x /tmp/install-mmpose.sh && bash /tmp/install-mmpose.sh \
    && rm -rf /root/.cache/pip

WORKDIR /ws

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
