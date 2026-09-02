# Saffron India - E-Commerce Platform

A premium Kashmiri saffron e-commerce platform built with Flask, PostgreSQL (Supabase), and modern JavaScript. Prepared for production deployment on **GitHub + Vercel**.

---

## 🌟 Features

- **Authentication & Security:** Secure password hashing (Werkzeug), session-based auth, email OTP verification with rate limiting (60s cooldown, max 5 attempts, hashed OTP storage).
- **Product Catalog & Management:** Public storefront, single product views, and full Admin CRUD for products.
- **Tamper-Proof Orders:** Server-side price calculation directly from database/catalog—client-submitted prices cannot be manipulated.
- **Admin Dashboard & Analytics:** Revenue, gross profit, margin, shipping, monthly/daily trends, top-selling products, and order status management.
- **Email Notifications:** Gmail SMTP integration for OTP registration, order confirmations, and customer order status updates (with non-blocking timeouts).
- **Cloud Database:** Seamless connection to Supabase PostgreSQL with connection pooling.
- **Serverless Ready:** Configured for Vercel deployment with `/api/*` routed to Python serverless functions and static frontend served via edge CDN.

---

## 📁 Project Structure

```
SaffronIndia/
├── api/
│   └── index.py             # Vercel WSGI entry point
├── backend/
│   ├── app.py               # Flask application, models, routes & business logic
│   ├── requirements.txt     # Backend Python dependencies
│   ├── .env.example         # Backend environment variables template
│   ├── setup.ps1            # Local PowerShell setup script
│   └── start_server.ps1     # Local PowerShell start script
├── SaffronIndiaAdmin/
│   └── index.html           # Admin dashboard, order management & analytics
├── .env.example             # Root environment variables template
├── .gitignore               # Git ignore rules (protects .env, venv, cache)
├── vercel.json              # Vercel routing configuration
├── supabase_schema.sql      # Supabase PostgreSQL DDL schema & product seed data
├── requirements.txt         # Root dependencies for Vercel build
├── index.html               # Main storefront homepage
├── products.html            # Product catalog page
├── product.html             # Single product detail page
├── cart.html                # Shopping cart
├── checkout.html            # Checkout & receipt generator
├── login.html               # Login page
├── register.html            # Registration & OTP verification page
├── dashboard.html           # User dashboard
├── profile.html             # User profile
├── script.js                # Frontend client logic & API handlers
├── styles.css               # Global styling
└── README.md                # Project documentation & deployment guide
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.10+ installed
- Git installed

### 2. Create Virtual Environment & Install Dependencies
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (CMD):
venv\Scripts\activate.bat
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the `backend/` directory (or project root):
```bash
cp .env.example .env
```
Populate `.env` with your credentials:
```env
# For local testing, you can connect to your Supabase PostgreSQL database
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[YOUR-HOST]:5432/postgres?sslmode=require

# Persistent secret key for Flask sessions
SECRET_KEY=generate_with_python_secrets

# Environment
FLASK_ENV=development

# Email Configuration (Gmail SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_16_char_gmail_app_password
EMAIL_FROM=your_email@gmail.com
```

### 4. Run the Local Server
```bash
python app.py
```
The server will start at `http://127.0.0.1:5000`. You can access:
- Storefront: `http://127.0.0.1:5000/`
- Admin Panel: `http://127.0.0.1:5000/SaffronIndiaAdmin/index.html`

---

## 🗄️ Supabase PostgreSQL Setup

1. Log in to [Supabase](https://supabase.com) and create a new project.
2. Under **Project Settings -> Database**:
   - Find your **Connection string -> URI**.
   - Supabase provides pooled (`port 6543`) and direct (`port 5432`) connections. Both work with `psycopg2-binary`.
   - Ensure the prefix is `postgresql://` and set `sslmode=require`.
   - Replace `[YOUR-PASSWORD]` with your actual database password.
3. In the Supabase Dashboard, open **SQL Editor**:
   - Click **New Query**.
   - Copy the entire contents of [`supabase_schema.sql`](supabase_schema.sql).
   - Paste into the editor and click **Run**.
4. This will create:
   - `users`, `products`, `orders`, `order_items` tables.
   - Foreign keys and cascade delete rules.
   - Indexes for high-speed queries.
   - Seed products (`Imperial Threads 2g`, `Reserve Threads 5g`, `Ceremonial Hamper`, `Noor Wellness Elixir`).

---

## 📧 Gmail SMTP & App Password

To send OTP verification emails and order confirmations reliably:
1. Log in to your Google Account and visit **Security** -> **2-Step Verification**.
2. Enable 2-Step Verification if not already active.
3. Search for **App passwords** (or visit `https://myaccount.google.com/apppasswords`).
4. Generate a new App password:
   - App name: `Saffron India`
5. Google will provide a 16-character password (e.g., `abcd efgh ijkl mnop`).
6. Set this 16-character code as `EMAIL_PASSWORD` in your `.env` (and in Vercel environment variables).
   > **Note:** Never use your personal Google account password.

---

## 🔒 Security Implementations

1. **Server-Side Price Calculation:** The backend queries each item's price directly from the database (or verified catalog) upon checkout. Any modified client price or subtotal is discarded.
2. **Hashed OTPs:** OTPs are hashed using Werkzeug scrypt/pbkdf2 before storing in the database. Raw OTPs are never stored or exposed in API responses.
3. **Brute Force & Cooldown Protection:** OTP requests enforce a 60-second cooldown between resends and lockout after 5 failed verification attempts.
4. **HTML Sanitization in Emails:** All customer inputs inserted into email templates are escaped using `html.escape()` to prevent HTML/XSS injection.
5. **Stateless Signed Sessions:** Flask sessions use HTTPOnly, SameSite=Lax, and Secure cookie flags in production.
6. **Non-Blocking Email Deliveries:** SMTP operations use a 10-second timeout and are wrapped in exception handlers so email failures never crash customer checkout or registration.

---

## 📦 Pushing to GitHub

1. Ensure `.env` is **NOT** committed:
   ```bash
   git status
   ```
   (Verify `.env` is listed under untracked or ignored files, never staged).

2. Stage and commit your changes:
   ```bash
   git add .
   git commit -m "Configure Supabase PostgreSQL, production security, and Vercel deployment"
   ```

3. Push to your GitHub repository:
   ```bash
   git remote add origin https://github.com/[YOUR-USERNAME]/[YOUR-REPO].git
   git branch -M main
   git push -u origin main
   ```

---

## ☁️ Deploying to Vercel

1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Select and import your GitHub repository.
4. In the **Configure Project** screen:
   - **Framework Preset:** Select `Other` (or leave default).
   - **Root Directory:** `./`
5. Open **Environment Variables** and add:

| Variable Name | Description | Example / Note |
|---|---|---|
| `DATABASE_URL` | Supabase PostgreSQL URI | `postgresql://postgres:[PWD]@db.[REF].supabase.co:5432/postgres?sslmode=require` |
| `SECRET_KEY` | Flask Session Key | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | Environment mode | `production` |
| `FRONTEND_URL` | Production Domain (Optional) | `https://your-project.vercel.app` |
| `EMAIL_HOST` | SMTP Host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP Port | `587` |
| `EMAIL_USER` | Gmail Address | `your_email@gmail.com` |
| `EMAIL_PASSWORD` | 16-char App Password | `xxxx xxxx xxxx xxxx` |
| `EMAIL_FROM` | Sender Address | `your_email@gmail.com` |

6. Click **Deploy**.
7. Vercel will build the Python environment and deploy:
   - Static assets (`*.html`, `*.css`, `*.js`) served directly from edge locations.
   - Dynamic `/api/*` requests routed to `api/index.py` serverless functions.
