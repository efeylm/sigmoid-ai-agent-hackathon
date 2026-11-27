# Oracle Cloud'a Deploy (Always Free)

Backend + PostgreSQL tek bir Oracle Cloud VM'inde Docker Compose ile çalışır.
Caddy, `<ip>.sslip.io` alan adı için otomatik HTTPS sertifikası alır. Frontend Vercel'de.

## 1. VM oluştur (Oracle konsolu)
- Compute → Instances → **Create instance**
- Image: **Canonical Ubuntu 24.04** (veya 22.04)
- Shape: **Ampere → VM.Standard.A1.Flex**, 2 OCPU / 12 GB (Always Free sınırı 4 OCPU / 24 GB)
  - "Out of capacity" hatası: başka Availability Domain seç, 1 OCPU / 6 GB dene, ya da
    **VM.Standard.E2.1.Micro** (AMD, 1 GB RAM; setup.sh swap ekler, ama yavaş olur).
- Networking: yeni VCN + **public subnet**, "Assign a public IPv4 address" açık.
- SSH keys: **Generate a key pair for me** → *Save private key* (Downloads'a iner).
- Create → durum **Running** olunca *Public IP address*'i not al.

## 2. 80/443 portlarını aç (Oracle konsolu)
Instance sayfası → Primary VNIC → Subnet → **Security Lists** → Default Security List →
**Add Ingress Rules**: Source CIDR `0.0.0.0/0`, IP Protocol TCP, Destination Port Range `80,443`.

## 3. Sunucuya kur (Windows PowerShell)
```powershell
# Anahtar ve .env'i VM'e kopyala
scp -i $HOME\Downloads\ssh-key-XXXX.key D:\sigmoid-ai-agent-hackathon\.env ubuntu@<IP>:~/.env
# Bağlan
ssh -i $HOME\Downloads\ssh-key-XXXX.key ubuntu@<IP>
```
VM içinde:
```bash
curl -fsSL https://raw.githubusercontent.com/efeylm/sigmoid-ai-agent-hackathon/main/deploy/setup.sh | bash
```
Sonunda `HAZIR! API adresi: https://<ip-tireli>.sslip.io` yazar.

> Windows "UNPROTECTED PRIVATE KEY FILE" hatası verirse:
> `icacls $HOME\Downloads\ssh-key-XXXX.key /inheritance:r /grant:r "$($env:USERNAME):R"`

## 4. Vercel
- Root Directory: `frontend`
- Environment Variable: `NEXT_PUBLIC_API_URL = https://<ip-tireli>.sslip.io`
- CORS: `*.vercel.app` varsayılan olarak izinli. Özel alan adı kullanırsan VM'deki `.env`'e
  `CORS_ORIGINS=https://alanadin.com` ekleyip setup.sh'ı tekrar çalıştır.

## 5. Erişim kodu (maliyet koruması)
VM'deki `~/app/.env` dosyasına ekle, sonra setup.sh'ı tekrar çalıştır:
```
APP_ACCESS_CODE=kodun-buraya
REPORT_DAILY_LIMIT_PER_IP=5
REPORT_DAILY_LIMIT_TOTAL=30
```
- Kod boşsa uygulama herkese açıktır. Doluysa site önce kod sorar, backend de kodsuz her `/api` isteğini reddeder.
- Birden fazla kod virgülle verilebilir (`APP_ACCESS_CODE=cv2026,mulakat`): birini kaldırınca sadece o kod geçersiz olur.
- Doğrudan açılan link: `https://<vercel-adresin>/?code=kodun-buraya` (kod tarayıcıda saklanır, adres çubuğundan silinir).
- Limitler günlük, gece yarısı sıfırlanır; `0` sınırsız demektir.

## Güncelleme / bakım
```bash
# Yeni kodu çek ve yeniden başlat
curl -fsSL https://raw.githubusercontent.com/efeylm/sigmoid-ai-agent-hackathon/main/deploy/setup.sh | bash
# Loglar
cd ~/app && sudo docker compose -f docker-compose.prod.yml logs -f backend
```
`.env` sadece VM'de durur, repoya asla commit edilmez.
