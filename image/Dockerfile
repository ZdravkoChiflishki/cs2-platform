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

ARG METAMOD_URL=https://mms.alliedmods.net/mmsdrop/2.0/mmsource-2.0.0-git1467-linux.tar.gz
ARG METAMOD_SHA256=f3dd81999e93ef86d45ed8f0f451c93806ad7fba1514dafd5f2623c61ca637a2
ARG CSSHARP_URL=https://github.com/roflmuffin/CounterStrikeSharp/releases/download/v1.0.375/counterstrikesharp-with-runtime-linux-1.0.375.zip
ARG CSSHARP_SHA256=26f9259ec7b584cb0afb464652423e88f9841ed3a675ba6db4871af07406947f

RUN mkdir -p /opt/cs2-platform/plugin-runtime /tmp/cs2-plugin-runtime \
    && curl -fsSL "$METAMOD_URL" -o /tmp/cs2-plugin-runtime/metamod.tar.gz \
    && echo "$METAMOD_SHA256  /tmp/cs2-plugin-runtime/metamod.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/cs2-plugin-runtime/metamod.tar.gz -C /opt/cs2-platform/plugin-runtime \
    && curl -fsSL "$CSSHARP_URL" -o /tmp/cs2-plugin-runtime/counterstrikesharp.zip \
    && echo "$CSSHARP_SHA256  /tmp/cs2-plugin-runtime/counterstrikesharp.zip" | sha256sum -c - \
    && unzip -q /tmp/cs2-plugin-runtime/counterstrikesharp.zip -d /opt/cs2-platform/plugin-runtime \
    && rm -rf /tmp/cs2-plugin-runtime

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
