# 01 Beispiel: Proxy-Daten (anpassen!)
PROXY_HOST="10.237.47.97"
PROXY_PORT="3128"

# Wenn kein Benutzer/Passwort benötigt wird:
PROXY_URL="http://${PROXY_HOST}:${PROXY_PORT}"

# Falls Benutzer/Passwort benötigt:
# PROXY_URL="http://USER:PASSWORD@${PROXY_HOST}:${PROXY_PORT}"

# 02 In /etc/environment global eintragen

sudo nano /etc/environment

# Folgende Zeilen hinzufügen oder anpassen:

http_proxy="${PROXY_URL}"
https_proxy="${PROXY_URL}"
ftp_proxy="${PROXY_URL}"
no_proxy="localhost,127.0.0.1,::1"

# 03 Für APT explizit konfigurieren
sudo nano /etc/apt/apt.conf.d/95proxies

# Inhalt:
Acquire::http::Proxy "${PROXY_URL}/";
Acquire::https::Proxy "${PROXY_URL}/";

# 04 Für wget (optional)
sudo nano /etc/wgetrc

# Füge hinzu oder ändere:
use_proxy = on
http_proxy = ${PROXY_URL}
https_proxy = ${PROXY_URL}

# 05 Für git (falls GitLab Zugriff über Proxy nötig ist)
git config --global http.proxy ${PROXY_URL}
git config --global https.proxy ${PROXY_URL}

# 06 Änderungen aktivieren
source /etc/environment

# 07 Test: Verbindung prüfen
curl -v http://example.com
