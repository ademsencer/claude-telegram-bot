# Claude Telegram Bot

Telegram uzerinden Claude Code'a komut gonder, sonuclari al. Docker container icinde 7/24 calisir.

## Ozellikler

- **Claude Code Entegrasyonu**: Telegram'dan Claude'a gorev ver, sonuclari canli takip et
- **Proje Yonetimi**: Git repo'larini klonla, projeler uzerinde Claude'u calistir
- **Sistem Monitoring**: VPN/WiFi durumunu izle, kopmalarda bildirim al
- **Claude Code Hooks**: Claude calisirken adim adim Turkce bildirimler

## Hizli Baslangic

### 1. Bot Olustur

Telegram'da [@BotFather](https://t.me/botfather)'a `/newbot` yaz ve token'ini al.

### 2. Konfigürasyon

```bash
cp .env.example .env
# .env dosyasini duzenle:
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHAT_ID (bot'a /start yazinca ogrenirsin)
# - ANTHROPIC_API_KEY (console.anthropic.com)
```

### 3. Docker ile Calistir

```bash
docker compose up -d
```

### 4. Guncelle

```bash
docker compose pull && docker compose up -d
```

## Komutlar

| Komut | Aciklama |
|-------|----------|
| `/start` | Bot'u baslat, Chat ID'ni ogren |
| `/help` | Tum komutlari listele |
| `/ping` | Bot canli mi? |
| `/ask <soru>` | Claude'a soru sor |
| `/task <proje> <gorev>` | Projede Claude'a gorev ver |
| `/task status` | Aktif gorev durumu |
| `/task cancel` | Gorevi iptal et |
| `/project clone <url>` | Git repo klonla |
| `/project list` | Projeleri listele |
| `/project delete <ad>` | Projeyi sil |
| `/mode <skip\|auto\|ask>` | Claude izin modu |
| `/log` | Son Claude ciktisi |
| `/status` | Sistem durumu |
| `/vpn` | VPN durumu |
| `/wifi` | WiFi durumu |

## Mimari

```
Docker Container
+-----------------+  +------------------+
| Telegram Bot    |  | Claude Code CLI  |
| (Python)        |--| (Node.js)        |
| - Komutlar      |  | - --print mode   |
| - Streaming     |  | - stream-json    |
+-----------------+  +------------------+
       |                    |
  Telegram API        /workspace/
                   (git clone projeler)
```

## Ortam Degiskenleri

| Degisken | Aciklama | Zorunlu |
|----------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | BotFather'dan alinan token | Evet |
| `TELEGRAM_CHAT_ID` | Bildirim gonderilecek chat | Evet |
| `ALLOWED_CHAT_IDS` | Yetkili kullanicilar (virgul ile) | Evet |
| `ANTHROPIC_API_KEY` | Anthropic API anahtari | Evet |
| `CLAUDE_MODEL` | Claude modeli (default: claude-sonnet-4-6) | Hayir |
| `CLAUDE_MAX_TURNS` | Maks tur sayisi (default: 50) | Hayir |
| `CLAUDE_PERMISSIONS` | Izin modu: skip/auto/ask | Hayir |
| `VPN_CHECK_INTERVAL` | VPN kontrol araligi (sn) | Hayir |
| `WIFI_CHECK_INTERVAL` | WiFi kontrol araligi (sn) | Hayir |

## Claude Code Hook Kurulumu (Opsiyonel)

Claude Code calisirken Telegram'a bildirim gondermek icin:

```bash
bash hooks/install-hooks.sh
```

Bu, Claude Code'un her tool kullandiginda Telegram'a bildirim atar.

## Lisans

MIT
