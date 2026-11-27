import os

BASE_URL = "https://www.ticaretsicil.gov.tr"
LOGIN_URL = f"{BASE_URL}/index.php"
SEARCH_URL = f"{BASE_URL}/view/hizlierisim/unvansorgulama.php"
VIEW_URL = f"{BASE_URL}/view/hizlierisim/ilangoruntuleme.php"

# Environment Variable'dan çekmek en güvenlisidir
USER_EMAIL = os.getenv("SICIL_USER", "hikmettopak17@gmail.com") 
USER_PASS = os.getenv("SICIL_PASS", "TicaretGazetesi34")

# Docker içinde /app/gazeteler yolunu kullanacağız
DOWNLOAD_DIR = "/app/gazeteler"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)