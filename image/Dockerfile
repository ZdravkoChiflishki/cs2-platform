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
ARG CS2RCON_URL=https://github.com/LordFetznschaedl/CS2Rcon/releases/download/1.2.0/CS2Rcon-1.2.0.zip
ARG CS2RCON_SHA256=311425a06d7a4af980c6dfab188b8b60a598c2edae1fa33828bcb25b47b85639
ARG SIMPLEADMIN_URL=https://github.com/daffyyyy/CS2-SimpleAdmin/releases/download/build-1.8.2b/CS2-SimpleAdmin-1.8.2b.zip
ARG SIMPLEADMIN_SHA256=3879f74a000582c407f9795be62f718cb1d512e58ba9c81accf12d691696c201
ARG MENUMANAGER_URL=https://github.com/NickFox007/MenuManagerCS2/releases/download/1.4.1/MenuManager.zip
ARG MENUMANAGER_SHA256=2ae011c6cebe3ca279d3cb5d15a568f13ae63398be82a98bd65e204a043a13b3
ARG PLAYERSETTINGS_URL=https://github.com/NickFox007/PlayerSettingsCS2/releases/download/0.9.4/PlayerSettings.zip
ARG PLAYERSETTINGS_SHA256=6d6645f728dbe07ca37264ab55f228ab4dcb3740cba02c52fbb27ef15faed0ac
ARG ANYBASELIB_URL=https://github.com/NickFox007/AnyBaseLibCS2/releases/download/0.9.4/AnyBaseLib.zip
ARG ANYBASELIB_SHA256=ab3190f43d7afc95d609bbb755279552fba0283ce0a2681c371601a4bd7867ff

RUN mkdir -p /opt/cs2-platform/plugin-runtime /tmp/cs2-plugin-runtime \
    && curl -fsSL "$METAMOD_URL" -o /tmp/cs2-plugin-runtime/metamod.tar.gz \
    && echo "$METAMOD_SHA256  /tmp/cs2-plugin-runtime/metamod.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/cs2-plugin-runtime/metamod.tar.gz -C /opt/cs2-platform/plugin-runtime \
    && curl -fsSL "$CSSHARP_URL" -o /tmp/cs2-plugin-runtime/counterstrikesharp.zip \
    && echo "$CSSHARP_SHA256  /tmp/cs2-plugin-runtime/counterstrikesharp.zip" | sha256sum -c - \
    && unzip -q /tmp/cs2-plugin-runtime/counterstrikesharp.zip -d /opt/cs2-platform/plugin-runtime \
    && curl -fsSL "$CS2RCON_URL" -o /tmp/cs2-plugin-runtime/cs2rcon.zip \
    && echo "$CS2RCON_SHA256  /tmp/cs2-plugin-runtime/cs2rcon.zip" | sha256sum -c - \
    && unzip -q /tmp/cs2-plugin-runtime/cs2rcon.zip -d /tmp/cs2-plugin-runtime/cs2rcon \
    && cp -a /tmp/cs2-plugin-runtime/cs2rcon/CS2Rcon-1.2.0/addons /opt/cs2-platform/plugin-runtime/ \
    && curl -fsSL "$SIMPLEADMIN_URL" -o /tmp/cs2-plugin-runtime/simpleadmin.zip \
    && echo "$SIMPLEADMIN_SHA256  /tmp/cs2-plugin-runtime/simpleadmin.zip" | sha256sum -c - \
    && unzip -q /tmp/cs2-plugin-runtime/simpleadmin.zip -d /tmp/cs2-plugin-runtime/simpleadmin \
    && mkdir -p /opt/cs2-platform/plugin-runtime/addons/counterstrikesharp/plugins /opt/cs2-platform/plugin-runtime/addons/counterstrikesharp/shared \
    && cp -a /tmp/cs2-plugin-runtime/simpleadmin/counterstrikesharp/plugins/CS2-SimpleAdmin /opt/cs2-platform/plugin-runtime/addons/counterstrikesharp/plugins/ \
    && cp -a /tmp/cs2-plugin-runtime/simpleadmin/counterstrikesharp/shared/CS2-SimpleAdminApi /opt/cs2-platform/plugin-runtime/addons/counterstrikesharp/shared/ \
    && curl -fsSL "$MENUMANAGER_URL" -o /tmp/cs2-plugin-runtime/menumanager.zip \
    && echo "$MENUMANAGER_SHA256  /tmp/cs2-plugin-runtime/menumanager.zip" | sha256sum -c - \
    && unzip -q /tmp/cs2-plugin-runtime/menumanager.zip -d /opt/cs2-platform/plugin-runtime \
    && curl -fsSL "$PLAYERSETTINGS_URL" -o /tmp/cs2-plugin-runtime/playersettings.zip \
    && echo "$PLAYERSETTINGS_SHA256  /tmp/cs2-plugin-runtime/playersettings.zip" | sha256sum -c - \
    && unzip -q /tmp/cs2-plugin-runtime/playersettings.zip -d /opt/cs2-platform/plugin-runtime \
    && curl -fsSL "$ANYBASELIB_URL" -o /tmp/cs2-plugin-runtime/anybaselib.zip \
    && echo "$ANYBASELIB_SHA256  /tmp/cs2-plugin-runtime/anybaselib.zip" | sha256sum -c - \
    && unzip -q /tmp/cs2-plugin-runtime/anybaselib.zip -d /opt/cs2-platform/plugin-runtime \
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
