FROM python:3.12-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      jq \
      lib32gcc-s1 \
      lib32stdc++6 \
      libicu72 \
      procps \
      rsync \
      tar \
      tini \
      unzip \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/steamcmd \
    && curl -fsSL https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz \
      | tar -xz -C /opt/steamcmd \
    && chmod +x /opt/steamcmd/steamcmd.sh

RUN useradd --create-home --home-dir /home/steam --shell /bin/bash steam

WORKDIR /opt/cs2-platform
COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY image/entrypoint.sh /entrypoint.sh
COPY image/scripts /opt/cs2-platform/image/scripts
RUN chmod +x /entrypoint.sh /opt/cs2-platform/image/scripts/*.sh \
    && pip install --no-cache-dir .

ENV CS2_ROOT=/home/steam/cs2 \
    CONFIG_ROOT=/opt/cs2-platform/configs \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
