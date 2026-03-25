#!/bin/bash
# Claude Code Hook Kurulum Scripti
# Bu script, Claude Code'un settings dosyasina Telegram bildirim hook'larini ekler.
#
# Kullanim: bash install-hooks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK_SCRIPT="${SCRIPT_DIR}/claude-notify.sh"
SETTINGS_FILE="${HOME}/.claude/settings.json"

echo "📦 Claude Code Telegram Hook Kurulumu"
echo "======================================"

# Hook scriptinin varligini kontrol et
if [ ! -f "$HOOK_SCRIPT" ]; then
    echo "❌ Hook scripti bulunamadi: $HOOK_SCRIPT"
    exit 1
fi

# jq kontrolu
if ! command -v jq &> /dev/null; then
    echo "❌ jq yuklu degil. Kurulum:"
    echo "  macOS: brew install jq"
    echo "  Linux: sudo apt install jq"
    exit 1
fi

# .env kontrolu
ENV_FILE="${SCRIPT_DIR}/../.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  .env dosyasi bulunamadi. Olusturuluyor..."
    cp "${SCRIPT_DIR}/../.env.example" "$ENV_FILE"
    echo "📝 ${ENV_FILE} dosyasini duzenle ve token/chat_id ekle."
    echo ""
fi

# Settings dosyasini olustur veya guncelle
if [ ! -f "$SETTINGS_FILE" ]; then
    echo "📄 Settings dosyasi olusturuluyor: $SETTINGS_FILE"
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    echo '{}' > "$SETTINGS_FILE"
fi

echo "🔧 Hook konfigurasyonu ekleniyor..."

# Hook konfigurasyonunu ekle
HOOK_CONFIG=$(cat <<EOF
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|Bash|Agent|TodoWrite",
        "hooks": [
          {
            "type": "command",
            "command": "${HOOK_SCRIPT}",
            "timeout": 5
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "${HOOK_SCRIPT}",
            "timeout": 5
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "${HOOK_SCRIPT}",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "${HOOK_SCRIPT}",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
EOF
)

# Mevcut settings ile merge et
CURRENT=$(cat "$SETTINGS_FILE")
MERGED=$(echo "$CURRENT" | jq --argjson hooks "$HOOK_CONFIG" '. * $hooks')
echo "$MERGED" | jq '.' > "$SETTINGS_FILE"

echo "✅ Hook konfigurasyonu eklendi: $SETTINGS_FILE"
echo ""
echo "📋 Sonraki adimlar:"
echo "1. .env dosyasina TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID ekle"
echo "2. Claude Code'u yeniden baslat (hook'lar yuklensin)"
echo "3. Bir dosya duzenleyerek hook'un calistigini test et"
echo ""
echo "🧪 Manuel test:"
echo "  echo '{\"tool_name\":\"Write\",\"hook_event_name\":\"PostToolUse\",\"tool_input\":{\"file_path\":\"/test/file.txt\"}}' | bash ${HOOK_SCRIPT}"
