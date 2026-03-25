FROM python:3.13-slim

# Sistem bagimliliklari + Node.js (Claude Code CLI icin)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git jq openssh-client iputils-ping iproute2 procps \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Python bagimliliklari
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Non-root kullanici olustur (Claude Code root ile --dangerously-skip-permissions izin vermiyor)
RUN useradd -m -s /bin/bash botuser \
    && mkdir -p /workspace /app /home/botuser/.claude \
    && chown -R botuser:botuser /workspace /app /home/botuser

# Uygulama kodu
COPY --chown=botuser:botuser . .

# Git konfigurasyonu
RUN git config --global user.email "bot@claude-telegram.local" \
    && git config --global user.name "Claude Bot"

USER botuser

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('https://api.telegram.org')"

CMD ["python", "bot.py"]
