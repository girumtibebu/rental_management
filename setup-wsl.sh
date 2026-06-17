#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  setup-wsl.sh – Install Frappe Bench + ERPNext + rental_management
#  inside WSL 2 and expose the development server on port 8085.
#
#  Tested on Ubuntu 22.04 / 24.04 (WSL 2).
#  Run as a non-root user that has sudo access:
#
#      bash setup-wsl.sh
#
#  After setup, access the site in Windows Chrome at:
#      http://localhost:8085
#
#  Default login:  Administrator / admin
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configurable variables ───────────────────────────────────────
BENCH_DIR="${HOME}/frappe-bench"      # where the bench will be created
SITE_NAME="mysite.localhost"          # Frappe site name
HTTP_PORT=8085                        # port visible from Windows Chrome
ADMIN_PASS="admin"                    # Frappe Administrator password
DB_ROOT_PASS="root"                   # MariaDB root password
FRAPPE_BRANCH="version-15"           # frappe/erpnext branch to use
ERPNEXT_REPO="https://github.com/frappe/erpnext"
RENTAL_REPO="https://github.com/girumtibebu/rental_management"
# ────────────────────────────────────────────────────────────────

BOLD="\033[1m"; RESET="\033[0m"; GREEN="\033[32m"; YELLOW="\033[33m"
info()  { echo -e "${GREEN}[INFO]${RESET}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }

# ── 1. System packages ───────────────────────────────────────────
info "Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    git curl wget python3 python3-pip python3-dev python3-venv \
    build-essential libffi-dev libssl-dev \
    mariadb-server mariadb-client libmariadb-dev \
    redis-server \
    xvfb libfontconfig wkhtmltopdf \
    nodejs npm

# ── 2. Node.js 18 LTS (required by Frappe) ───────────────────────
if ! node --version 2>/dev/null | grep -q "^v18"; then
    info "Installing Node.js 18 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# ── 3. yarn ──────────────────────────────────────────────────────
if ! command -v yarn &>/dev/null; then
    info "Installing yarn..."
    sudo npm install -g yarn
fi

# ── 4. frappe-bench CLI ───────────────────────────────────────────
if ! command -v bench &>/dev/null; then
    info "Installing frappe-bench..."
    pip3 install --user frappe-bench
    # Make sure ~/.local/bin is on PATH
    export PATH="${HOME}/.local/bin:${PATH}"
fi

# ── 5. MariaDB ───────────────────────────────────────────────────
info "Configuring MariaDB..."
sudo service mariadb start || sudo systemctl start mariadb || true

# Set root password and create a user for bench
sudo mariadb -e "
  ALTER USER 'root'@'localhost' IDENTIFIED BY '${DB_ROOT_PASS}';
  FLUSH PRIVILEGES;
" 2>/dev/null || \
sudo mariadb -uroot -p"${DB_ROOT_PASS}" -e "SELECT 1;" 2>/dev/null || true

# Frappe-recommended MariaDB settings
MYCNF="/etc/mysql/mariadb.conf.d/99-frappe.cnf"
if [ ! -f "${MYCNF}" ]; then
    sudo tee "${MYCNF}" > /dev/null <<'MYCNF_EOF'
[mysqld]
character-set-client-handshake = FALSE
character-set-server            = utf8mb4
collation-server                = utf8mb4_unicode_ci

[mysql]
default-character-set = utf8mb4
MYCNF_EOF
    sudo service mariadb restart || sudo systemctl restart mariadb || true
fi

# ── 6. Redis ────────────────────────────────────────────────────
info "Starting Redis..."
sudo service redis-server start || sudo systemctl start redis-server || true

# ── 7. Create bench ──────────────────────────────────────────────
if [ ! -d "${BENCH_DIR}" ]; then
    info "Creating bench at ${BENCH_DIR} (branch ${FRAPPE_BRANCH})..."
    bench init --frappe-branch "${FRAPPE_BRANCH}" "${BENCH_DIR}"
else
    warn "Bench already exists at ${BENCH_DIR} – skipping bench init."
fi

cd "${BENCH_DIR}"

# ── 8. Get ERPNext ───────────────────────────────────────────────
if [ ! -d "apps/erpnext" ]; then
    info "Getting ERPNext..."
    bench get-app --branch "${FRAPPE_BRANCH}" "${ERPNEXT_REPO}"
else
    warn "ERPNext already present – skipping."
fi

# ── 9. Get rental_management ─────────────────────────────────────
if [ ! -d "apps/rental_management" ]; then
    info "Getting rental_management..."
    bench get-app --branch main "${RENTAL_REPO}"
else
    warn "rental_management already present – skipping."
fi

# ── 10. Create site ──────────────────────────────────────────────
if [ ! -d "sites/${SITE_NAME}" ]; then
    info "Creating site ${SITE_NAME}..."
    bench new-site "${SITE_NAME}" \
        --admin-password "${ADMIN_PASS}" \
        --db-root-password "${DB_ROOT_PASS}" \
        --install-app erpnext
    bench --site "${SITE_NAME}" install-app rental_management
    bench use "${SITE_NAME}"
else
    warn "Site ${SITE_NAME} already exists – skipping site creation."
fi

# ── 11. Set port to 8085 ─────────────────────────────────────────
info "Configuring bench to serve on port ${HTTP_PORT}..."
bench set-config -g webserver_port "${HTTP_PORT}"

# Procfile uses port 8000 by default; patch it for direct `bench start`
if [ -f Procfile ]; then
    sed -i "s/--port [0-9][0-9]*/--port ${HTTP_PORT}/" Procfile
fi

# ── 12. Done ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}  Setup complete!${RESET}"
echo ""
echo "  Start the development server:"
echo "      cd ${BENCH_DIR} && bench start"
echo ""
echo "  Then open in Windows Chrome:"
echo "      http://localhost:${HTTP_PORT}"
echo ""
echo "  Login:  Administrator / ${ADMIN_PASS}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
