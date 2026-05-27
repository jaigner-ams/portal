# Portal — CLAUDE.md

Internal staff portal for America Smiles, served at `portal.americasmiles.com`.
Django 5.2.5 · MariaDB · Apache/mod_wsgi · Tailwind CSS 3.x

---

## Project Structure

```
/var/www/portal/
├── portal/          # Django project package (settings, urls, wsgi)
├── core/            # Main app: dashboard, site messages
├── accounts/        # Custom user model, user management
├── templates/       # Project-level templates (base.html, login.html)
├── theme/           # Tailwind CSS build (npm project)
│   ├── src/input.css
│   └── tailwind.config.js
├── static/          # Collected static files (do not edit directly)
├── media/           # User-uploaded media
└── venv/            # Python virtualenv
```

---

## Environment

- **Python**: `venv/bin/python` — always use this, never system Python
- **Django management**: `venv/bin/python manage.py <command>`
- **Database**: MariaDB, db `portal`, user `portal`@`localhost`
- **Timezone**: `America/Chicago`
- **DEBUG**: `False` in production — errors won't display in browser
- **Superuser**: create interactively with `venv/bin/python manage.py createsuperuser`

---

## Deploying Changes

**After editing Python/templates:**
```bash
touch /var/www/portal/portal/wsgi.py
```
This reloads the mod_wsgi daemon process.

**After editing CSS (Tailwind):**
```bash
cd /var/www/portal/theme && npm run build
venv/bin/python manage.py collectstatic --noinput
chown -R www-data:www-data /var/www/portal/static/
touch /var/www/portal/portal/wsgi.py
```

**After adding/changing models:**
```bash
venv/bin/python manage.py makemigrations
venv/bin/python manage.py migrate
```

**All files must be owned by `www-data:www-data`:**
```bash
chown -R www-data:www-data /var/www/portal/
```

---

## Apps

### `core`
- `models.py` — `SiteMessage` (message, message_type, is_active)
- `views.py` — `home` (dashboard), message CRUD views
- `context_processors.py` — injects active `SiteMessage` as `site_message` into every template
- `urls.py` — `/`, `/messages/`, `/messages/create/`, `/messages/<pk>/edit/`, `/messages/<pk>/toggle/`, `/messages/<pk>/delete/`

### `accounts`
- `models.py` — `User(AbstractUser)` with `role` field (`admin`/`staff`/`lab`) and `phone`
- `decorators.py` — `@admin_required` (redirects unauthenticated, raises 403 for non-admin)
- `views.py` — user list/create/edit/deactivate (all `@admin_required`)
- `urls.py` — `/accounts/users/`, `/accounts/users/create/`, `/accounts/users/<pk>/edit/`, `/accounts/users/<pk>/deactivate/`

---

## Auth & Permissions

- All views require `@login_required` at minimum
- Admin-only views use `@admin_required` from `accounts.decorators`
- `User.role` choices: `admin`, `staff`, `lab`
- Helper properties: `user.is_admin`, `user.is_staff_role`, `user.is_lab`
- `LOGIN_URL` = `/accounts/login/`, `LOGIN_REDIRECT_URL` = `/`, `LOGOUT_REDIRECT_URL` = `/accounts/login/`

---

## Frontend / CSS

- **Tailwind 3.x** with shadcn/ui design tokens as CSS custom properties
- **CSS vars** defined in `theme/src/input.css`: `--background`, `--foreground`, `--primary`, `--secondary`, `--muted`, `--accent`, `--card`, `--border`, `--input`, `--ring`, `--destructive`, `--radius`
- **Component classes** (defined in `input.css`, use these in templates):
  - `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-destructive`, `.btn-ghost`, `.btn-sm`
  - `.card`, `.card-header`, `.card-title`, `.card-description`, `.card-content`, `.card-footer`
  - `.input`, `.label`, `.textarea`
  - `.alert`, `.alert-info`, `.alert-warning`, `.alert-error`, `.alert-success`
  - `.badge`, `.badge-info`, `.badge-warning`, `.badge-error`, `.badge-success`
- **Font**: Inter (loaded from Google Fonts in `base.html`)
- Tailwind config scans all `templates/**/*.html` files
- Built CSS output: `core/static/core/css/styles.css` → collected to `static/`

---

## Templates

- `templates/base.html` — base layout: site message banner, nav, messages toasts, content block
- `templates/registration/login.html` — shadcn-style login card
- `core/templates/core/home.html` — dashboard
- `core/templates/core/message_list.html` — site message management table
- `core/templates/core/message_form.html` — create/edit message form
- `accounts/templates/accounts/user_list.html` — user management table
- `accounts/templates/accounts/user_form.html` — create/edit user form

The `site_message` context variable is available in every template (may be `None`).
Django `messages` framework toasts are rendered in `base.html`.

---

## Server & Infrastructure

- **Apache** with mod_wsgi; WSGI daemon process name: `portal`
- **HTTP vhost**: `/etc/apache2/sites-available/portal.americasmiles.com.conf` (redirects → HTTPS)
- **SSL vhost**: `/etc/apache2/sites-available/portal.americasmiles.com-le-ssl.conf`
- **SSL cert**: `/etc/letsencrypt/live/portal.americasmiles.com/`
- **Error log**: `/var/log/apache2/portal.americasmiles.com-error.log`
- **Caution**: `zzz-lab-sites.conf` is a catch-all vhost (`ServerAlias *`); certbot may deploy certs there — always enable the dedicated SSL vhost explicitly after cert renewal
- Other apps on the same server: `fusion`, `lab-sites`, `prospects.amsfusion.com`, `dlp`
