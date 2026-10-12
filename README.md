### Rental Management

Rental Management app by emc

---

### Local Development on WSL 2 (accessible on Windows Chrome at port 8085)

Two methods are provided. Pick the one that fits your workflow.

---

#### Method 1 – Docker Compose (recommended, no manual dependency setup)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and WSL 2 integration enabled.

```bash
# 1. Clone the repo (if you haven't already)
git clone https://github.com/girumtibebu/rental_management.git
cd rental_management

# 2. Create your local .env from the example
cp .env.example .env
#    Edit .env if you want to change passwords, the site name, or the port.
#    Default: HTTP_PORT=8085, ADMIN_PASSWORD=admin, SITE_NAME=mysite.localhost

# 3. Build and start the full stack (first run takes ~5–10 min)
docker compose up --build -d

# 4. Watch site creation progress
docker compose logs -f create-site
#    Wait until you see: ✓ Site mysite.localhost created and apps installed.

# 5. Open Windows Chrome and go to:
#       http://localhost:8085
#    Login: Administrator / admin  (or whatever you set in .env)
```

**Useful commands:**

```bash
# Stop the stack (data is preserved in Docker volumes)
docker compose down

# Stop AND delete all data (fresh start)
docker compose down -v

# Rebuild after code changes
docker compose up --build -d
```

---

#### Method 2 – Native Frappe Bench inside WSL 2

**Prerequisites:** WSL 2 with Ubuntu 22.04 or 24.04.

```bash
# 1. Clone the repo
git clone https://github.com/girumtibebu/rental_management.git
cd rental_management

# 2. Run the automated setup script (takes 10–20 min on first run)
bash setup-wsl.sh
#    The script installs Node, MariaDB, Redis, frappe-bench, ERPNext,
#    and this app, then configures port 8085.

# 3. Start the development server
cd ~/frappe-bench
bench start

# 4. Open Windows Chrome and go to:
#       http://localhost:8085
#    Login: Administrator / admin
```

> **WSL 2 port forwarding note:** WSL 2 automatically mirrors all listening
> ports to `localhost` on Windows, so no extra `netsh` or firewall rules are
> needed as long as you're on Windows 10 (2004+) or Windows 11.

---

### Standard Installation (existing bench)

You can install this app into an existing bench using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/girumtibebu/rental_management --branch main
bench install-app rental_management
```

---

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/rental_management
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

---

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request...


