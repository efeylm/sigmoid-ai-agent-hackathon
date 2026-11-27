#!/usr/bin/env bash
# One-shot setup for an Ubuntu VM (Oracle Cloud Always Free, ARM or AMD).
# Run on the VM:  curl -fsSL https://raw.githubusercontent.com/efeylm/sigmoid-ai-agent-hackathon/main/deploy/setup.sh | bash
# Before running, copy your local .env to the VM home folder (~/.env) with scp.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/efeylm/sigmoid-ai-agent-hackathon.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-$HOME/app}"

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mHATA: %s\033[0m\n' "$*" >&2; exit 1; }

# 1) Docker
if ! command -v docker >/dev/null 2>&1; then
  say "Docker kuruluyor..."
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$(whoami)" || true
fi
DOCKER="docker"; docker info >/dev/null 2>&1 || DOCKER="sudo docker"

# 2) Firewall inside the VM (Oracle Ubuntu images reject everything except SSH)
say "80/443 portlari aciliyor (VM ici guvenlik duvari)..."
for port in 80 443; do
  sudo iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null \
    || sudo iptables -I INPUT 1 -p tcp -m state --state NEW --dport "$port" -j ACCEPT
done
if command -v netfilter-persistent >/dev/null 2>&1; then
  sudo netfilter-persistent save >/dev/null 2>&1 || true
else
  sudo sh -c 'iptables-save > /etc/iptables/rules.v4' 2>/dev/null || true
fi

# 3) Swap on small machines (Chromium image build needs memory)
mem_kb=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
if [ "$mem_kb" -lt 4000000 ] && ! swapon --show | grep -q swapfile; then
  say "Az RAM var, 4 GB swap ekleniyor..."
  sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null && sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

# 4) Code
if [ -d "$APP_DIR/.git" ]; then
  say "Kod guncelleniyor..."
  git -C "$APP_DIR" fetch --depth 1 origin "$BRANCH"
  git -C "$APP_DIR" checkout -q -B "$BRANCH" FETCH_HEAD
else
  say "Kod indiriliyor..."
  sudo apt-get install -y git >/dev/null 2>&1 || true
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

# 5) .env
if [ ! -f .env ]; then
  [ -f "$HOME/.env" ] || die "~/.env bulunamadi. Once bilgisayarindan .env dosyasini scp ile VM'e kopyala, sonra bu komutu tekrar calistir."
  cp "$HOME/.env" .env
fi
chmod 600 .env

set_env() {  # set_env KEY VALUE  (only if missing or empty)
  if grep -qE "^$1=.+" .env; then return; fi
  sed -i "/^$1=/d" .env
  printf '%s=%s\n' "$1" "$2" >> .env
}
public_ip=$(curl -fsS https://api.ipify.org || curl -fsS https://ifconfig.me)
[ -n "$public_ip" ] || die "Public IP bulunamadi."
set_env DOMAIN "$(echo "$public_ip" | tr . -).sslip.io"
set_env POSTGRES_PASSWORD "$(openssl rand -hex 16)"
set_env CORS_ORIGIN_REGEX 'https://.*\.vercel\.app'
DOMAIN=$(grep -E '^DOMAIN=' .env | cut -d= -f2-)

# 6) Start
say "Container'lar derleniyor ve baslatiliyor (ilk sefer 5-15 dk surebilir)..."
$DOCKER compose -f docker-compose.prod.yml up -d --build

say "Backend ayaga kalkiyor, kontrol ediliyor..."
for i in $(seq 1 60); do
  if curl -fsS "https://$DOMAIN/health" >/dev/null 2>&1; then
    say "HAZIR! API adresi: https://$DOMAIN"
    echo "   Saglik kontrolu: https://$DOMAIN/health"
    echo "   API dokumani:    https://$DOMAIN/docs"
    echo "   Vercel'de NEXT_PUBLIC_API_URL = https://$DOMAIN"
    exit 0
  fi
  sleep 5
done
echo
echo "HTTPS henuz cevap vermiyor. Muhtemel sebepler:"
echo " - Oracle konsolunda 80 ve 443 icin Ingress Rule eklenmedi (Security List)."
echo " - Sertifika daha alinmadi; 1-2 dk sonra tekrar dene: curl https://$DOMAIN/health"
echo "Loglar: $DOCKER compose -f docker-compose.prod.yml logs --tail 50"
exit 1
