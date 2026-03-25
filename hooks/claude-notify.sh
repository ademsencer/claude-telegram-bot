#!/bin/bash
# Claude Code Hook -> Telegram Bildirim Scripti
# PostToolUse ve Notification event'lerinde calisir
# stdin'den JSON okur, Turkce mesaj olusturur, Telegram'a gonderir
#
# Gereksinimler: jq, curl
# Ortam degiskenleri: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# .env dosyasindan oku (eger ortam degiskenleri yoksa)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"
if [ -f "$ENV_FILE" ] && [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Token kontrolu
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    exit 0
fi

# stdin'den hook verisini oku
input=$(cat)

hook_event=$(echo "$input" | jq -r '.hook_event_name // "unknown"')
tool_name=$(echo "$input" | jq -r '.tool_name // ""')
session_id=$(echo "$input" | jq -r '.session_id // ""' | cut -c1-8)

# Event turune gore mesaj olustur
case "$hook_event" in
    "PostToolUse")
        # Tool bilgilerini al
        tool_input=$(echo "$input" | jq -r '.tool_input // {}')

        case "$tool_name" in
            "Write")
                file_path=$(echo "$tool_input" | jq -r '.file_path // "?"')
                file_name=$(basename "$file_path")
                msg="📝 Dosya olusturuldu: <code>${file_name}</code>"
                ;;
            "Edit")
                file_path=$(echo "$tool_input" | jq -r '.file_path // "?"')
                file_name=$(basename "$file_path")
                msg="✏️ Dosya duzenlendi: <code>${file_name}</code>"
                ;;
            "Read")
                file_path=$(echo "$tool_input" | jq -r '.file_path // "?"')
                file_name=$(basename "$file_path")
                msg="📖 Dosya okundu: <code>${file_name}</code>"
                ;;
            "Bash")
                command=$(echo "$tool_input" | jq -r '.command // "?"' | head -c 80)
                msg="⚡ Komut: <code>${command}</code>"
                ;;
            "Glob")
                pattern=$(echo "$tool_input" | jq -r '.pattern // "?"')
                msg="🔍 Dosya arandi: <code>${pattern}</code>"
                ;;
            "Grep")
                pattern=$(echo "$tool_input" | jq -r '.pattern // "?"')
                msg="🔎 Icerik arandi: <code>${pattern}</code>"
                ;;
            "Agent")
                desc=$(echo "$tool_input" | jq -r '.description // "?"')
                msg="🤖 Alt agent: ${desc}"
                ;;
            "TodoWrite")
                msg="📋 Gorev listesi guncellendi"
                ;;
            *)
                # Bilinmeyen tool - kisa bilgi
                msg="🔧 ${tool_name}"
                ;;
        esac
        ;;
    "Notification")
        message=$(echo "$input" | jq -r '.message // "Bildirim"')
        msg="🔔 ${message}"
        ;;
    "SessionStart")
        cwd=$(echo "$input" | jq -r '.cwd // "?"')
        dir_name=$(basename "$cwd")
        msg="🚀 Yeni oturum basladi: <code>${dir_name}</code>"
        ;;
    "SessionEnd")
        msg="👋 Oturum sonlandi"
        ;;
    "Stop")
        reason=$(echo "$input" | jq -r '.reason // ""')
        msg="✅ Gorev tamamlandi"
        [ -n "$reason" ] && msg="${msg}: ${reason}"
        ;;
    *)
        msg="📌 ${hook_event}: ${tool_name}"
        ;;
esac

# Oturum ID'sini ekle
[ -n "$session_id" ] && msg="[${session_id}] ${msg}"

# Telegram'a gonder (arka planda, hook'u yavaslatmamak icin)
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{
        \"chat_id\": \"${TELEGRAM_CHAT_ID}\",
        \"text\": \"${msg}\",
        \"parse_mode\": \"HTML\",
        \"disable_notification\": false
    }" > /dev/null 2>&1 &

exit 0
