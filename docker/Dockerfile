FROM osrf/ros:jazzy-desktop AS builder

SHELL ["/bin/bash", "-c"]

ARG USERNAME=robot
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=jazzy
ENV WORKSPACE_DIR=/opt/robotnik_ws
ENV SRC_DIR=/opt/robotnik_ws/src
ENV REPO_ROOT=/opt/robotnik_ws/src/robotnik/robotnik_simulation
ENV EXTERNAL_REPOS_FILE=/opt/robotnik_ws/src/robotnik/robotnik_simulation/dependencies/repos/robotnik_simulation.jazzy.repos

COPY dependencies/requirements/builder/packages.txt /tmp/requirements/builder-packages.txt
COPY dependencies/requirements/base/packages.txt /tmp/requirements/base-packages.txt

RUN builder_packages="$(sed "s/\${ROS_DISTRO}/${ROS_DISTRO}/g" /tmp/requirements/builder-packages.txt | grep -vE '^(#|$)')" \
    && apt-get update \
    && apt-get install -y --no-install-recommends ${builder_packages} \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
    --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
    | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null

RUN base_packages="$(sed "s/\${ROS_DISTRO}/${ROS_DISTRO}/g" /tmp/requirements/base-packages.txt | grep -vE '^(#|$)')" \
    && apt-get update \
    && apt-get install -y --no-install-recommends ${base_packages} \
    && rm -rf /var/lib/apt/lists/*

RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then \
        rosdep init; \
    fi

RUN if ! getent group "${USER_GID}" >/dev/null; then \
        groupadd --gid "${USER_GID}" "${USERNAME}"; \
    fi \
    && if id -u "${USERNAME}" >/dev/null 2>&1; then \
        usermod --uid "${USER_UID}" --gid "${USER_GID}" --home "/home/${USERNAME}" --shell /bin/bash "${USERNAME}"; \
    elif getent passwd "${USER_UID}" >/dev/null; then \
        existing_user="$(getent passwd "${USER_UID}" | cut -d: -f1)"; \
        usermod --login "${USERNAME}" --gid "${USER_GID}" --home "/home/${USERNAME}" --move-home --shell /bin/bash "${existing_user}"; \
    else \
        useradd --uid "${USER_UID}" --gid "${USER_GID}" --create-home --shell /bin/bash "${USERNAME}"; \
    fi \
    && mkdir -p "/home/${USERNAME}" \
    && chown -R "${USER_UID}:${USER_GID}" "/home/${USERNAME}" /etc/ros/rosdep

RUN gosu "${USERNAME}:${USER_GID}" bash -lc '\
      for attempt in 1 2 3; do \
        rosdep update && exit 0; \
        echo "rosdep update failed on attempt ${attempt}, retrying..."; \
        sleep 5; \
      done; \
      exit 1'

WORKDIR ${WORKSPACE_DIR}

RUN mkdir -p "${SRC_DIR}/robotnik"

COPY . ${REPO_ROOT}

RUN awk ' \
      BEGIN { skip = 0 } \
      /^  robotnik\/robotnik_simulation:/ { skip = 1; next } \
      skip && /^  [^[:space:]]/ { skip = 0 } \
      !skip { print } \
    ' "${EXTERNAL_REPOS_FILE}" > /tmp/robotnik_external.repos \
    && vcs import --skip-existing "${SRC_DIR}" < /tmp/robotnik_external.repos

# Fail before building an image whose robot launch cannot expand its description.
RUN test -f "${SRC_DIR}/robotnik/robotnik_description/simulators/gazebo_ignition/robot.urdf.xacro" \
    || { echo "Incompatible robotnik_description revision: integrate description PR #98 into the official compatibility branch and update the pinned .repos manifest." >&2; exit 1; }

RUN if compgen -G "${REPO_ROOT}/debs/*.deb" > /dev/null; then \
        apt-get update \
        && apt-get install -y "${REPO_ROOT}"/debs/*.deb \
        && rm -rf /var/lib/apt/lists/*; \
    else \
        echo "No local Robotnik debs found, skipping deb installation."; \
    fi

RUN source /opt/ros/${ROS_DISTRO}/setup.bash \
    && apt-get update \
    && rosdep install \
        --from-paths "${SRC_DIR}" \
        --ignore-src \
        -r \
        -y \
        --rosdistro "${ROS_DISTRO}" \
    && colcon build \
        --merge-install \
        --base-paths "${SRC_DIR}" \
    && rm -rf /var/lib/apt/lists/*

FROM builder AS runtime

ARG USERNAME=robot
ARG USER_UID=1000
ARG USER_GID=1000

ENV HOME=/home/${USERNAME}
ENV WORKSPACE_DIR=/opt/robotnik_ws

COPY docker/runtime-entrypoint.sh /usr/local/bin/runtime-entrypoint.sh
COPY env /opt/robotnik/config/env

RUN chmod +x /usr/local/bin/runtime-entrypoint.sh \
    && rm -rf "${WORKSPACE_DIR}/build" "${WORKSPACE_DIR}/log" "${WORKSPACE_DIR}/src" \
    && if ! getent group "${USER_GID}" >/dev/null; then \
        groupadd --gid "${USER_GID}" "${USERNAME}"; \
    fi \
    && if id -u "${USERNAME}" >/dev/null 2>&1; then \
        usermod --uid "${USER_UID}" --gid "${USER_GID}" --home "/home/${USERNAME}" --shell /bin/bash "${USERNAME}"; \
    elif getent passwd "${USER_UID}" >/dev/null; then \
        existing_user="$(getent passwd "${USER_UID}" | cut -d: -f1)"; \
        usermod --login "${USERNAME}" --gid "${USER_GID}" --home "/home/${USERNAME}" --move-home --shell /bin/bash "${existing_user}"; \
    else \
        useradd --uid "${USER_UID}" --gid "${USER_GID}" --create-home --shell /bin/bash "${USERNAME}"; \
    fi \
    && usermod -aG sudo,video,dialout "${USERNAME}" \
    && if getent group render >/dev/null; then usermod -aG render "${USERNAME}"; fi \
    && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}" \
    && printf '%s\n' \
      'if [ -f /opt/ros/${ROS_DISTRO}/setup.bash ]; then source /opt/ros/${ROS_DISTRO}/setup.bash; fi' \
      'if [ -f /opt/robotnik_ws/install/setup.bash ]; then source /opt/robotnik_ws/install/setup.bash; fi' \
      > /etc/profile.d/robotnik_ros_setup.sh \
    && chmod 0644 /etc/profile.d/robotnik_ros_setup.sh \
    && chown -R "${USER_UID}:${USER_GID}" /opt/robotnik \
    && printf '%s\n' \
      'source /etc/profile.d/robotnik_ros_setup.sh' \
      >> /root/.bashrc \
    && echo 'source /etc/profile.d/robotnik_ros_setup.sh' >> "/home/${USERNAME}/.bashrc" \
    && chown -R "${USER_UID}:${USER_GID}" "/home/${USERNAME}"

USER ${USERNAME}
WORKDIR /home/${USERNAME}

ENTRYPOINT ["/usr/local/bin/runtime-entrypoint.sh"]
