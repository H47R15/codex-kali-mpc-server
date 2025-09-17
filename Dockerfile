
FROM kalilinux/kali-rolling

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Install Kali toolchain components and Python tooling
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        aircrack-ng \
        nmap \
        theharvester \
        dnsenum \
        nikto \
        sqlmap && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python3 -m venv "${VIRTUAL_ENV}" && \
    "${VIRTUAL_ENV}/bin/pip" install --no-cache-dir -r requirements.txt

COPY kali_server.py ./

RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app

USER mcpuser

CMD ["python", "kali_server.py"]
