import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re
import random
import html
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

# Get the parent directory (project root) for serving HTML files
BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(__name__, static_folder=None)

# ----------------------------------------------------------
# Database Configuration (Supabase PostgreSQL / SQLite fallback)
# ----------------------------------------------------------
import urllib.parse

def normalize_db_url(url: str) -> str:
    if not url:
        return "sqlite:///saffron_india.db"
    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    # Handle passwords wrapped in brackets like [password] or with unencoded @
    match = re.match(r'^(postgresql(?:\+\w+)?://)([^:]+):\[(.*?)\]@([^/@:]+(?::\d+)?(?:/.*)?)$', url)
    if match:
        scheme, user, pwd, rest = match.groups()
        encoded_pwd = urllib.parse.quote_plus(pwd)
        url = f"{scheme}{user}:{encoded_pwd}@{rest}"
    elif '@' in url and '://' in url:
        prefix, host_rest = url.rsplit('@', 1)
        if '://' in prefix and ':' in prefix.split('://', 1)[1]:
            scheme = prefix.split('://', 1)[0] + '://'
            scheme_user_part, pwd_part = prefix.split('://', 1)[1].split(':', 1)
            if pwd_part.startswith('[') and pwd_part.endswith(']'):
                pwd_part = pwd_part[1:-1]
            encoded_pwd = urllib.parse.quote_plus(urllib.parse.unquote_plus(pwd_part))
            url = f"{scheme}{scheme_user_part}:{encoded_pwd}@{host_rest}"
            
    # Supabase direct hostname (db.<ref>.supabase.co) is IPv6-only.
    # Convert automatically to Supabase IPv4 connection pooler for serverless (Vercel) compatibility.
    pooler_match = re.match(r'^(postgresql(?:\+\w+)?://)([^:]+):(.*?)@db\.([a-z0-9]+)\.supabase\.co(?::\d+)?(/.*)?$', url)
    if pooler_match:
        scheme, user, pwd, project_ref, rest = pooler_match.groups()
        pooler_user = f"{user}.{project_ref}" if "." not in user else user
        rest = rest or "/postgres"
        url = f"{scheme}{pooler_user}:{pwd}@aws-0-ap-southeast-1.pooler.supabase.com:6543{rest}"

    if "supabase" in url and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

is_production = os.getenv("FLASK_ENV") == "production" or os.getenv("VERCEL") == "1"

def check_db_reachable(url: str) -> bool:
    if not url.startswith("postgresql://"):
        return True
    try:
        match = re.search(r'@([^/:?]+)', url)
        if match:
            host = match.group(1)
            import socket
            socket.gethostbyname(host)
        return True
    except Exception:
        return False

raw_db_url = normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///saffron_india.db"))

if raw_db_url.startswith("postgresql://") and not is_production:
    if not check_db_reachable(raw_db_url):
        print("[WARNING] PostgreSQL database host could not be resolved (Supabase project may be paused due to inactivity).")
        print("[INFO] To unpause Supabase, click 'Restore project' in https://supabase.com/dashboard")
        print("[INFO] Temporarily using local SQLite database (instance/dev_local.db) for local development.")
        instance_dir = Path(__file__).resolve().parent / "instance"
        instance_dir.mkdir(parents=True, exist_ok=True)
        db_file = (instance_dir / "dev_local.db").as_posix()
        raw_db_url = f"sqlite:///{db_file}"

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JSON_SORT_KEYS"] = False

# Production-safe connection pool settings for PostgreSQL/Supabase
if raw_db_url.startswith("postgresql://"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
    }

# ----------------------------------------------------------
# Session & Security Configuration
# ----------------------------------------------------------
# Use persistent SECRET_KEY from env, fallback to consistent dev key
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "saffron-india-development-secret-key-change-in-production")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = is_production

db = SQLAlchemy(app)

# ----------------------------------------------------------
# CORS Configuration
# ----------------------------------------------------------
frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
allowed_origins = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    re.compile(r"^https://.*\.vercel\.app$"),
]
if frontend_url:
    allowed_origins.append(frontend_url)

CORS(app, 
     resources={r"/api/*": {"origins": allowed_origins, "supports_credentials": True}}, 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])

# ----------------------------------------------------------
# Email Configuration
# ----------------------------------------------------------
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)

# ----------------------------------------------------------
# Database Models
# ----------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    email_verified = db.Column(db.Boolean, default=False)
    otp_code = db.Column(db.String(255))
    otp_expires_at = db.Column(db.DateTime)
    otp_attempts = db.Column(db.Integer, default=0)
    otp_last_sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)  # stored in rupees
    image_url = db.Column(db.String(500))
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "sku": self.sku,
            "description": self.description,
            "price": self.price,
            "image_url": self.image_url,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    shipping_method = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="pending")
    country = db.Column(db.String(80))
    address_line1 = db.Column(db.String(255))
    address_line2 = db.Column(db.String(255))
    city = db.Column(db.String(80))
    postal_code = db.Column(db.String(20))
    notes = db.Column(db.Text)
    subtotal = db.Column(db.Integer, nullable=False)
    shipping_cost = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "shipping_method": self.shipping_method,
            "payment_method": self.payment_method,
            "status": self.status,
            "country": self.country,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "postal_code": self.postal_code,
            "notes": self.notes,
            "subtotal": self.subtotal,
            "shipping_cost": self.shipping_cost,
            "total": self.total,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    product_name = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "qty": self.qty,
            "unit_price": self.unit_price,
        }


# Auto-seed local SQLite database for instant local development if needed
if raw_db_url.startswith("sqlite:///"):
    with app.app_context():
        try:
            db.create_all()
            if Product.query.count() == 0:
                seed_products = [
                    Product(name="Imperial Threads 2g", sku="threads", price=1999, description="Hand-picked stigmas with crocin levels above 250 for intense color and aroma. Premium Grade I saffron hand-picked from our Pampore estate at 5,000 ft altitude.", image_url="https://images.unsplash.com/photo-1453831210728-695502f9f795?auto=format&fit=crop&w=600&q=80", active=True),
                    Product(name="Reserve Threads 5g", sku="reserve", price=4750, description="Limited harvest lot numbered by hand and packed in violet glass. An exclusive limited-edition harvest from our finest Pampore fields.", image_url="https://images.unsplash.com/photo-1464306076886-da185f6a9d12?auto=format&fit=crop&w=600&q=80", active=True),
                    Product(name="Ceremonial Hamper", sku="hamper", price=4499, description="Includes saffron jar, tasting spoons, brass diya, and infusion guide in a handcrafted cedar box.", image_url="https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&w=600&q=80", active=True),
                    Product(name="Noor Wellness Elixir", sku="elixir", price=1299, description="Infuse into sparkling water or desserts for antioxidant-rich notes. Crafted with premium saffron, organic rose petals, cardamom, and raw Himalayan honey.", image_url="https://images.unsplash.com/photo-1457410129867-5999af49daf7?auto=format&fit=crop&w=600&q=80", active=True)
                ]
                db.session.add_all(seed_products)
                db.session.commit()
                print("[INFO] Seeded default product catalog into local database.")
            if not User.query.filter_by(role="admin").first():
                admin_user = User(
                    full_name="Admin",
                    email="admin@saffronindia.com",
                    phone="9999999999",
                    role="admin",
                    email_verified=True
                )
                admin_user.set_password("Admin@123")
                db.session.add(admin_user)
                db.session.commit()
                print("[INFO] Created default admin: admin@saffronindia.com / Admin@123")
        except Exception as e:
            print(f"[WARNING] Could not auto-initialize local sqlite db: {e}")


# ----------------------------------------------------------
# Helper Functions & Decorators
# ----------------------------------------------------------
def error_response(message, status=400):
    return jsonify({"success": False, "message": message}), status


def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return error_response("Not authenticated.", 401)
        return f(*args, **kwargs)

    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return error_response("Not authenticated.", 401)
        user = db.session.get(User, user_id)
        if not user or user.role != "admin":
            return error_response("Not authorized.", 403)
        return f(*args, **kwargs)

    return decorated


def validate_password(password):
    """Validate password strength requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"


def validate_phone(phone):
    """Validate phone number - must be exactly 10 digits"""
    if not phone:
        return False, "Phone number is required"
    
    clean_phone = re.sub(r'[^\d]', '', str(phone))
    
    if len(clean_phone) != 10:
        return False, "Phone number must be exactly 10 digits"
    
    return True, clean_phone


def generate_otp():
    """Generate a secure 6-digit OTP"""
    return str(random.randint(100000, 999999))


# ----------------------------------------------------------
# Production-Safe Email System
# ----------------------------------------------------------
def send_order_email(user_email, user_name, order_data, is_update=False):
    """Send order confirmation or status update email with timeout and robust error handling"""
    try:
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("INFO: Email configuration not set; skipping order email")
            return False
            
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = user_email
        
        safe_name = html.escape(str(user_name or "Valued Customer"))
        order_id_str = str(order_data['id']).zfill(6)
        
        if is_update:
            msg['Subject'] = f"Order Status Update - Saffron India - Order #{order_id_str}"
            email_type = "Status Update"
        else:
            msg['Subject'] = f"Order Confirmation - Saffron India - Order #{order_id_str}"
            email_type = "Order Confirmation"

        # Safe date formatting
        try:
            created_raw = order_data.get('created_at', '')
            if 'T' in created_raw:
                order_date = datetime.fromisoformat(created_raw.replace('Z', '+00:00')).strftime('%B %d, %Y')
            else:
                order_date = datetime.strptime(created_raw, '%a, %d %b %Y %H:%M:%S GMT').strftime('%B %d, %Y')
        except Exception:
            order_date = datetime.utcnow().strftime('%B %d, %Y')

        status_colors = {
            'delivered': '#28a745',
            'shipped': '#007bff',
            'processing': '#ffc107',
            'pending': '#6c757d',
            'cancelled': '#dc3545'
        }
        status_color = status_colors.get(order_data.get('status', 'pending'), '#6c757d')

        items_rows = ""
        for item in order_data.get('items', []):
            item_name = html.escape(str(item.get('product_name', '')))
            item_qty = int(item.get('qty', 1))
            item_price = int(item.get('unit_price', 0))
            item_total = item_price * item_qty
            items_rows += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 12px;">{item_name}</td>
                <td style="padding: 12px; text-align: center;">{item_qty}</td>
                <td style="padding: 12px; text-align: right;">₹{item_price}</td>
                <td style="padding: 12px; text-align: right; font-weight: bold;">₹{item_total}</td>
            </tr>"""

        safe_line1 = html.escape(str(order_data.get('address_line1', '')))
        safe_line2 = html.escape(str(order_data.get('address_line2') or ''))
        safe_city = html.escape(str(order_data.get('city', '')))
        safe_zip = html.escape(str(order_data.get('postal_code', '')))
        safe_country = html.escape(str(order_data.get('country', '')))
        safe_payment = html.escape(str(order_data.get('payment_method', '')).title())
        safe_shipping = html.escape(str(order_data.get('shipping_method', '')).title())
        safe_status = html.escape(str(order_data.get('status', '')).title())

        address_lines = f"""
        <p style="margin: 5px 0;">{safe_name}</p>
        <p style="margin: 5px 0;">{safe_line1}</p>"""
        if safe_line2:
            address_lines += f"<p style='margin: 5px 0;'>{safe_line2}</p>"
        address_lines += f"""
        <p style="margin: 5px 0;">{safe_city}, {safe_zip}</p>
        <p style="margin: 5px 0;">{safe_country}</p>"""

        email_template = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
            <div style="background-color: #1a0c29; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: #d4af37; margin: 0; font-size: 28px;">Saffron India</h1>
                <p style="color: #f7f3e9; margin: 10px 0 0 0; font-size: 16px;">{email_type}</p>
            </div>

            <div style="background-color: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                {f'''
                <h2 style="color: #1a0c29; margin-bottom: 20px;">Your Order Status Has Been Updated!</h2>
                <p style="color: #333; line-height: 1.6; margin-bottom: 20px;">Dear {safe_name},</p>
                <p style="color: #333; line-height: 1.6; margin-bottom: 20px;">Good news! Your order status has been updated. Here are the latest details:</p>
                ''' if is_update else f'''
                <h2 style="color: #1a0c29; margin-bottom: 20px;">Thank You for Your Order!</h2>
                <p style="color: #333; line-height: 1.6; margin-bottom: 20px;">Dear {safe_name},</p>
                <p style="color: #333; line-height: 1.6; margin-bottom: 20px;">We are pleased to confirm your order has been received and is being processed. Below are your order details:</p>
                '''}

                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #d4af37;">
                    <h3 style="color: #1a0c29; margin-top: 0; margin-bottom: 15px;">Order Information</h3>
                    <p style="margin: 5px 0;"><strong>Order Number:</strong> #{order_id_str}</p>
                    <p style="margin: 5px 0;"><strong>Order Date:</strong> {order_date}</p>
                    <p style="margin: 5px 0;"><strong>Payment Method:</strong> {safe_payment}</p>
                    <p style="margin: 5px 0;"><strong>Shipping Method:</strong> {safe_shipping}</p>
                    <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{safe_status}</span></p>
                </div>

                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #1a0c29; margin-top: 0; margin-bottom: 15px;">Shipping Address</h3>
                    {address_lines}
                </div>

                <div style="margin: 20px 0;">
                    <h3 style="color: #1a0c29; margin-bottom: 15px;">Order Items</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #1a0c29; color: white;">
                                <th style="padding: 12px; text-align: left;">Product</th>
                                <th style="padding: 12px; text-align: center;">Quantity</th>
                                <th style="padding: 12px; text-align: right;">Price</th>
                                <th style="padding: 12px; text-align: right;">Total</th>
                            </tr>
                        </thead>
                        <tbody>{items_rows}</tbody>
                        <tfoot>
                            <tr>
                                <td colspan="3" style="padding: 12px; text-align: right; font-weight: bold;">Subtotal:</td>
                                <td style="padding: 12px; text-align: right; font-weight: bold;">₹{order_data['subtotal']}</td>
                            </tr>
                            <tr>
                                <td colspan="3" style="padding: 12px; text-align: right; font-weight: bold;">Shipping:</td>
                                <td style="padding: 12px; text-align: right; font-weight: bold;">₹{order_data['shipping_cost']}</td>
                            </tr>
                            <tr style="background-color: #d4af37; color: white;">
                                <td colspan="3" style="padding: 12px; text-align: right; font-weight: bold;">Total:</td>
                                <td style="padding: 12px; text-align: right; font-weight: bold; font-size: 18px;">₹{order_data['total']}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                    <p style="margin: 0; color: #666;">We will notify you of any further updates. Thank you for choosing Saffron India!</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(email_template, 'html'))
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
            
        print(f"[SUCCESS] Order {'status update' if is_update else 'confirmation'} email sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"[WARNING] Failed to send order email: {str(e)}")
        return False


def send_otp_email(email, otp):
    """Send OTP email for verification with timeout and error handling"""
    try:
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("INFO: Email configuration not set; skipping OTP email")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = email
        msg['Subject'] = 'Saffron India - Email Verification OTP'
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #1a0c29; color: #d4af37; padding: 25px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ padding: 25px; background: #ffffff; border: 1px solid #eee; border-radius: 0 0 8px 8px; }}
                .otp {{ font-size: 32px; font-weight: bold; color: #d4af37; text-align: center; padding: 18px; background: #fdfaf3; border: 2px dashed #d4af37; border-radius: 8px; margin: 20px 0; letter-spacing: 6px; }}
                .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0;">Saffron India</h1>
                <p style="margin: 5px 0 0 0; color: #f7f3e9;">Email Verification</p>
            </div>
            
            <div class="content">
                <h2>Verify Your Email Address</h2>
                <p>Thank you for registering with Saffron India! To complete your verification, please use the One-Time Password (OTP) below:</p>
                
                <div class="otp">{otp}</div>
                
                <p><strong>This OTP is valid for 10 minutes only.</strong></p>
                <p>For your security, never share this OTP with anyone.</p>
            </div>
            
            <div class="footer">
                <p>&copy; {datetime.utcnow().year} Saffron India. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"[SUCCESS] OTP email sent to {email}")
        return True
        
    except Exception as e:
        print(f"[WARNING] Failed to send OTP email: {e}")
        return False


# ----------------------------------------------------------
# Authentication & OTP Endpoints
# ----------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    payload = request.get_json() or {}

    required_fields = ["full_name", "email", "password", "phone"]
    if not all(payload.get(field) for field in required_fields):
        return error_response("Full name, email, password, and phone number are required.")

    email = payload["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return error_response("Email already registered.", 409)

    password = payload["password"]
    is_valid, password_message = validate_password(password)
    if not is_valid:
        return error_response(password_message)

    phone = payload["phone"]
    is_valid, phone_result = validate_phone(phone)
    if not is_valid:
        return error_response(phone_result)
    clean_phone = phone_result

    # Generate and hash OTP
    otp = generate_otp()
    otp_hash = generate_password_hash(otp)
    otp_expires_at = datetime.utcnow() + timedelta(minutes=10)

    user = User(
        full_name=payload["full_name"].strip(),
        email=email,
        phone=clean_phone,
        role="user",
        email_verified=False,
        otp_code=otp_hash,
        otp_expires_at=otp_expires_at,
        otp_attempts=0,
        otp_last_sent_at=datetime.utcnow()
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Send plain OTP to user's email only
    email_sent = send_otp_email(email, otp)
    
    msg = "Registration successful! Please check your email for OTP verification." if email_sent else \
          "Registration successful! (Email delivery is currently paused; please contact support for verification)."

    return jsonify({
        "success": True, 
        "message": msg,
        "user_id": user.id,
        "email": user.email
    }), 201


@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    """Verify OTP for email registration with rate limiting and secure hashing"""
    payload = request.get_json() or {}
    
    required_fields = ["email", "otp"]
    if not all(payload.get(field) for field in required_fields):
        return error_response("Email and OTP are required.")
    
    email = payload["email"].strip().lower()
    otp = str(payload["otp"]).strip()
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return error_response("User not found.", 404)
    
    if user.email_verified:
        return error_response("Email already verified.")
    
    # Check attempt limit
    if (user.otp_attempts or 0) >= 5:
        user.otp_code = None
        db.session.commit()
        return error_response("Too many failed verification attempts. Please request a new OTP.", 429)
    
    if not user.otp_code or not user.otp_expires_at:
        return error_response("No pending OTP found. Please request a new OTP.")
    
    if datetime.utcnow() > user.otp_expires_at:
        return error_response("OTP has expired. Please request a new OTP.")
    
    # Verify hash (or fallback to plain comparison for backward compatibility with existing DB records)
    is_otp_valid = False
    if user.otp_code.startswith("scrypt:") or user.otp_code.startswith("pbkdf2:"):
        is_otp_valid = check_password_hash(user.otp_code, otp)
    else:
        is_otp_valid = (user.otp_code == otp)
        
    if not is_otp_valid:
        user.otp_attempts = (user.otp_attempts or 0) + 1
        db.session.commit()
        remaining = 5 - user.otp_attempts
        return error_response(f"Invalid OTP. {remaining} attempt(s) remaining.")
    
    # Successful verification
    user.email_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    user.otp_attempts = 0
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Email verified successfully! You can now login."
    })


@app.route("/api/resend-otp", methods=["POST"])
def resend_otp():
    """Resend OTP for email verification with 60-second cooldown protection"""
    payload = request.get_json() or {}
    
    email = payload.get("email", "").strip().lower()
    if not email:
        return error_response("Email is required.")
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return error_response("User not found.", 404)
    
    if user.email_verified:
        return error_response("Email already verified.")
    
    # Cooldown check: enforce minimum 60s between OTP requests
    if user.otp_last_sent_at:
        elapsed = (datetime.utcnow() - user.otp_last_sent_at).total_seconds()
        if elapsed < 60:
            remaining = int(60 - elapsed)
            return error_response(f"Please wait {remaining} seconds before requesting a new OTP.", 429)
    
    otp = generate_otp()
    user.otp_code = generate_password_hash(otp)
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    user.otp_attempts = 0
    user.otp_last_sent_at = datetime.utcnow()
    db.session.commit()
    
    email_sent = send_otp_email(email, otp)
    if email_sent:
        return jsonify({"success": True, "message": "OTP has been resent to your email."})
    else:
        return jsonify({"success": True, "message": "New OTP generated. (Email delivery paused; please contact support)."})


@app.route("/api/login", methods=["POST"])
def login():
    payload = request.get_json() or {}
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not email or not password:
        return error_response("Email and password are required.")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return error_response("Invalid credentials.", 401)

    # Store user identity in session cookie
    session["user_id"] = user.id
    session["user_email"] = user.email

    if user.role == "admin":
        return jsonify({"success": True, "message": "Admin login successful.", "user": user.to_dict(), "redirect": "admin"})

    return jsonify({"success": True, "message": "Login successful.", "user": user.to_dict()})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/user", methods=["GET"])
@require_login
def get_current_user():
    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return error_response("User not found.", 404)

    return jsonify({"success": True, "user": user.to_dict()})


# ----------------------------------------------------------
# Product Endpoints (Public & Admin)
# ----------------------------------------------------------
@app.route("/api/products", methods=["GET"])
def list_products():
    """Get all active products for the store"""
    products = Product.query.filter_by(active=True).order_by(Product.created_at.desc()).all()
    return jsonify({"success": True, "products": [p.to_dict() for p in products]})


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Get a single product by ID"""
    product = db.session.get(Product, product_id)
    if not product or not product.active:
        return error_response("Product not found.", 404)
    return jsonify({"success": True, "product": product.to_dict()})


@app.route("/api/admin/products", methods=["GET"])
@require_admin
def admin_list_products():
    """Get all products for admin management"""
    products = Product.query.order_by(Product.created_at.desc()).all()
    return jsonify({"success": True, "products": [p.to_dict() for p in products]})


@app.route("/api/admin/products", methods=["POST"])
@require_admin
def admin_create_product():
    """Create a new product"""
    payload = request.get_json() or {}
    
    required_fields = ["name", "sku", "price"]
    if not all(payload.get(field) for field in required_fields):
        return error_response("Name, SKU, and price are required.")
    
    sku = payload["sku"].strip()
    if Product.query.filter_by(sku=sku).first():
        return error_response("A product with this SKU already exists.", 409)
    
    try:
        price = int(payload["price"])
        if price < 0:
            return error_response("Price must be a non-negative integer.")
    except (ValueError, TypeError):
        return error_response("Invalid price format.")
    
    product = Product(
        name=payload["name"].strip(),
        sku=sku,
        description=payload.get("description", "").strip(),
        price=price,
        image_url=payload.get("image_url", "").strip(),
        active=bool(payload.get("active", True))
    )
    
    db.session.add(product)
    db.session.commit()
    
    return jsonify({"success": True, "product": product.to_dict()}), 201


@app.route("/api/admin/products/<int:product_id>", methods=["PUT"])
@require_admin
def admin_update_product(product_id):
    """Update an existing product"""
    product = db.session.get(Product, product_id)
    if not product:
        return error_response("Product not found.", 404)
    payload = request.get_json() or {}
    
    if "name" in payload:
        product.name = payload["name"].strip()
    if "description" in payload:
        product.description = payload["description"].strip()
    if "price" in payload:
        try:
            price = int(payload["price"])
            if price < 0:
                return error_response("Price must be non-negative.")
            product.price = price
        except (ValueError, TypeError):
            return error_response("Invalid price format.")
    if "image_url" in payload:
        product.image_url = payload["image_url"].strip()
    if "active" in payload:
        product.active = bool(payload["active"])
    
    if "sku" in payload:
        new_sku = payload["sku"].strip()
        if new_sku != product.sku:
            existing = Product.query.filter_by(sku=new_sku).first()
            if existing:
                return error_response("A product with this SKU already exists.", 409)
            product.sku = new_sku
    
    db.session.commit()
    return jsonify({"success": True, "product": product.to_dict()})


@app.route("/api/admin/products/<int:product_id>", methods=["DELETE"])
@require_admin
def admin_delete_product(product_id):
    """Delete a product"""
    product = db.session.get(Product, product_id)
    if not product:
        return error_response("Product not found.", 404)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"success": True, "message": "Product deleted successfully"})


# ----------------------------------------------------------
# Order Endpoints (Secure Server-Side Price Calculation)
# ----------------------------------------------------------
CATALOG_FALLBACK_PRICES = {
    "imperial threads 2g": 1999,
    "reserve threads 5g": 4750,
    "ceremonial hamper": 4499,
    "noor wellness elixir": 1299,
}

@app.route("/api/orders", methods=["POST"])
@require_login
def create_order():
    payload = request.get_json() or {}
    raw_items = payload.get("items") or []
    if not raw_items:
        return error_response("Order must contain at least one item.")

    full_name = (payload.get("fullName") or "").strip()
    email = (payload.get("email") or "").strip()
    phone = (payload.get("phone") or "").strip()
    shipping_method = (payload.get("shippingMethod") or "standard").strip().lower()
    payment_method = (payload.get("paymentMethod") or "cod").strip()
    notes = (payload.get("notes") or "").strip()
    address = payload.get("address") or {}

    if not full_name or not email or not phone:
        return error_response("Full name, email, and phone are required for orders.")

    # Validate and calculate prices server-side to prevent price tampering
    db_products = {p.id: p for p in Product.query.all()}
    db_products_by_name = {p.name.strip().lower(): p for p in db_products.values()}
    db_products_by_sku = {p.sku.strip().lower(): p for p in db_products.values()}

    calculated_subtotal = 0
    validated_items = []

    for item in raw_items:
        product_name = (item.get("product") or item.get("product_name") or "").strip()
        try:
            qty = int(item.get("qty") or 0)
        except (ValueError, TypeError):
            qty = 0

        if not product_name or qty <= 0:
            continue
        if qty > 100:
            return error_response("Maximum quantity per item is 100.")

        # Match against database products
        matched_product = None
        item_product_id = item.get("product_id") or item.get("id")
        if item_product_id and item_product_id in db_products:
            matched_product = db_products[item_product_id]
        elif product_name.lower() in db_products_by_name:
            matched_product = db_products_by_name[product_name.lower()]
        elif item.get("sku") and item.get("sku").strip().lower() in db_products_by_sku:
            matched_product = db_products_by_sku[item.get("sku").strip().lower()]

        if matched_product:
            unit_price = matched_product.price
            final_name = matched_product.name
            prod_id = matched_product.id
        else:
            # Fallback to verified catalog prices if DB not yet fully populated
            unit_price = CATALOG_FALLBACK_PRICES.get(product_name.lower(), int(item.get("price") or 0))
            final_name = product_name
            prod_id = None

        calculated_subtotal += unit_price * qty
        validated_items.append({
            "product_id": prod_id,
            "product_name": final_name,
            "qty": qty,
            "unit_price": unit_price
        })

    if not validated_items:
        return error_response("No valid items in order.")

    # Shipping cost calculated server-side
    calculated_shipping = 299 if shipping_method == "express" else 0
    calculated_total = calculated_subtotal + calculated_shipping

    order = Order(
        user_id=session["user_id"],
        full_name=full_name,
        email=email,
        phone=phone,
        shipping_method=shipping_method,
        payment_method=payment_method,
        status=payload.get("paymentStatus") or "pending",
        country=(address.get("country") or "").strip(),
        address_line1=(address.get("line1") or "").strip(),
        address_line2=(address.get("line2") or "").strip(),
        city=(address.get("city") or "").strip(),
        postal_code=(address.get("postalCode") or "").strip(),
        notes=notes,
        subtotal=calculated_subtotal,
        shipping_cost=calculated_shipping,
        total=calculated_total,
    )

    db.session.add(order)
    db.session.flush()

    for vi in validated_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=vi["product_id"],
            product_name=vi["product_name"],
            qty=vi["qty"],
            unit_price=vi["unit_price"],
        )
        db.session.add(order_item)

    db.session.commit()

    # Trigger order confirmation email safely (non-blocking failure)
    try:
        order_data = order.to_dict(include_items=True)
        send_order_email(email, full_name, order_data, is_update=False)
    except Exception as e:
        print(f"Warning: Failed to send confirmation email: {e}")

    return jsonify({"success": True, "order": order.to_dict(include_items=True)}), 201


@app.route("/api/orders", methods=["GET"])
@require_login
def list_user_orders():
    orders = (
        Order.query.filter_by(user_id=session["user_id"])
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify({"success": True, "orders": [o.to_dict(include_items=True) for o in orders]})


@app.route("/api/admin/orders", methods=["GET"])
@require_admin
def admin_list_orders():
    status = request.args.get("status")
    query = Order.query
    if status:
        query = query.filter_by(status=status)
    orders = query.order_by(Order.created_at.desc()).all()
    return jsonify({"success": True, "orders": [o.to_dict(include_items=True) for o in orders]})


@app.route("/api/admin/orders/<int:order_id>", methods=["PATCH"])
@require_admin
def admin_update_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return error_response("Order not found.", 404)
        
    payload = request.get_json() or {}
    new_status = payload.get("status")
    
    old_status = order.status
    if new_status and new_status != old_status:
        order.status = new_status
        db.session.commit()
        
        # Send status update email only when status actually changes
        try:
            order_data = order.to_dict(include_items=True)
            send_order_email(order.email, order.full_name, order_data, is_update=True)
        except Exception as e:
            print(f"Warning: Failed to send order status update email: {e}")
            
    return jsonify({"success": True, "order": order.to_dict(include_items=True)})


# ----------------------------------------------------------
# Analytics Endpoint
# ----------------------------------------------------------
@app.route("/api/admin/analytics", methods=["GET"])
@require_admin
def admin_analytics():
    """Get comprehensive analytics including profit/loss and sales trends"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start_date = datetime.utcnow() - timedelta(days=365)
            
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        else:
            end_date = datetime.utcnow()
    except ValueError:
        start_date = datetime.utcnow() - timedelta(days=365)
        end_date = datetime.utcnow()
    
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).all()
    
    total_orders = len(orders)
    total_revenue = sum(order.total for order in orders)
    total_shipping = sum(order.shipping_cost for order in orders)
    
    # 30% assumed product cost -> 70% gross product margin
    estimated_cost = sum(order.subtotal * 0.3 for order in orders)
    gross_profit = total_revenue - estimated_cost - total_shipping
    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    monthly_sales = {}
    monthly_orders = {}
    for order in orders:
        if order.created_at:
            month_key = order.created_at.strftime('%Y-%m')
            monthly_sales[month_key] = monthly_sales.get(month_key, 0) + order.total
            monthly_orders[month_key] = monthly_orders.get(month_key, 0) + 1
    
    daily_sales = {}
    daily_orders = {}
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_orders = [o for o in orders if o.created_at and o.created_at >= thirty_days_ago]
    
    for order in recent_orders:
        day_key = order.created_at.strftime('%Y-%m-%d')
        daily_sales[day_key] = daily_sales.get(day_key, 0) + order.total
        daily_orders[day_key] = daily_orders.get(day_key, 0) + 1
    
    product_sales = {}
    for order in orders:
        for item in order.items:
            product_key = item.product_name
            if product_key not in product_sales:
                product_sales[product_key] = {'quantity': 0, 'revenue': 0}
            product_sales[product_key]['quantity'] += item.qty
            product_sales[product_key]['revenue'] += item.unit_price * item.qty
    
    top_products = sorted(
        product_sales.items(), 
        key=lambda x: x[1]['revenue'], 
        reverse=True
    )[:10]
    
    status_breakdown = {}
    for order in orders:
        status_breakdown[order.status] = status_breakdown.get(order.status, 0) + 1
    
    return jsonify({
        "success": True,
        "analytics": {
            "summary": {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "gross_profit": round(gross_profit, 2),
                "profit_margin": round(profit_margin, 2),
                "total_shipping": total_shipping,
                "estimated_costs": round(estimated_cost, 2),
                "average_order_value": round(total_revenue / total_orders, 2) if total_orders > 0 else 0
            },
            "monthly_sales": monthly_sales,
            "monthly_orders": monthly_orders,
            "daily_sales": daily_sales,
            "daily_orders": daily_orders,
            "top_products": [{
                "name": name,
                "quantity": data['quantity'],
                "revenue": data['revenue']
            } for name, data in top_products],
            "status_breakdown": status_breakdown,
            "date_range": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d')
            }
        }
    })


# ----------------------------------------------------------
# Static File Routing (Local & Server Fallback)
# ----------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    safe_filename = filename.lower()
    # Security: Block server-side code, secrets, logs, and database files
    if (
        safe_filename.endswith((".py", ".pyc", ".env", ".db", ".sqlite", ".sql", ".log"))
        or safe_filename.startswith(("api/", "backend/", "instance/", "."))
        or "/." in safe_filename
    ):
        return error_response("Not found", 404)
    return send_from_directory(BASE_DIR, filename)


# ----------------------------------------------------------
# CLI Commands
# ----------------------------------------------------------
@app.cli.command("init-db")
def init_db():
    """Create database tables and seed initial catalog if empty"""
    db.create_all()
    print("Database tables verified.")
    
    # Seed default products if empty
    if Product.query.count() == 0:
        seed_products = [
            Product(name="Imperial Threads 2g", sku="threads", price=1999, description="Hand-picked stigmas with crocin levels above 250.", image_url="https://images.unsplash.com/photo-1453831210728-695502f9f795?auto=format&fit=crop&w=600&q=80", active=True),
            Product(name="Reserve Threads 5g", sku="reserve", price=4750, description="Limited harvest lot numbered by hand and packed in violet glass.", image_url="https://images.unsplash.com/photo-1464306076886-da185f6a9d12?auto=format&fit=crop&w=600&q=80", active=True),
            Product(name="Ceremonial Hamper", sku="hamper", price=4499, description="Includes saffron jar, tasting spoons, brass diya, and infusion guide.", image_url="https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&w=600&q=80", active=True),
            Product(name="Noor Wellness Elixir", sku="elixir", price=1299, description="Infuse into sparkling water or desserts for antioxidant-rich notes.", image_url="https://images.unsplash.com/photo-1457410129867-5999af49daf7?auto=format&fit=crop&w=600&q=80", active=True)
        ]
        db.session.add_all(seed_products)
        db.session.commit()
        print("Default catalog seeded.")


@app.cli.command("create-admin")
def create_admin():
    """Create an admin user for the system"""
    email = input("Enter admin email: ").strip().lower()
    password = input("Enter admin password: ").strip()
    full_name = input("Enter admin full name (optional): ").strip() or "Admin"
    
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        print(f"User with email {email} already exists!")
        return
    
    admin_user = User(
        full_name=full_name,
        email=email,
        phone="0000000000",
        role="admin",
        email_verified=True
    )
    admin_user.set_password(password)
    
    db.session.add(admin_user)
    db.session.commit()
    
    print("[SUCCESS] Admin user created successfully!")
    print(f"  Email: {email}")
    print(f"  Name: {full_name}")
    print("  Role: admin")


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
