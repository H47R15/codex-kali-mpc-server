ARG KALI_IMAGE=kalilinux/kali-rolling
FROM ${KALI_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Install Kali toolchain components. Attempt to install every meta package, skipping ones
# that are unavailable on the current architecture (some Kali meta packages do not exist
# on arm64 builds, for example).
ENV KALI_TOOL_METAPACKAGES="kali-tools-top10 kali-tools-web kali-tools-information-gathering kali-tools-wireless kali-tools-bluetooth kali-tools-sniffing-spoofing kali-tools-social-engineering kali-tools-exploitation kali-tools-fuzzing kali-tools-reverse-engineering kali-tools-hardware kali-tools-sdr kali-tools-vehicle kali-tools-voip kali-tools-forensics kali-tools-crypto-stego kali-tools-maintaining-access kali-tools-reporting"

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv kali-linux-headless; \
    for pkg in $KALI_TOOL_METAPACKAGES; do \
        if apt-cache show "$pkg" >/dev/null 2>&1; then \
            apt-get install -y --no-install-recommends "$pkg"; \
        else \
            echo "Skipping unavailable meta-package: $pkg"; \
        fi; \
    done; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python3 -m venv "${VIRTUAL_ENV}" && \
    "${VIRTUAL_ENV}/bin/pip" install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY src ./src
COPY kali_server.py ./
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app

USER mcpuser

ENTRYPOINT ["/entrypoint.sh"]
CMD ["kali-mcp-server"]
