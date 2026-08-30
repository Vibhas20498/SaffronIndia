from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import re
import random
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

# Get the parent directory (project root) for serving HTML files
BASE_DIR = Path(__file__).parent.parent

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path='')


# Email configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)

# Debug email configuration
print(f"Email Configuration:")
print(f"EMAIL_HOST: {EMAIL_HOST}")
print(f"EMAIL_PORT: {EMAIL_PORT}")
print(f"EMAIL_USER: {EMAIL_USER}")
print(f"EMAIL_PASSWORD: {'SET' if EMAIL_PASSWORD else 'NOT SET'}")
print(f"EMAIL_FROM: {EMAIL_FROM}")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "mysql+mysqlconnector://root:password@localhost/saffron_india"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JSON_SORT_KEYS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

db = SQLAlchemy(app)
# CORS configuration - allow credentials with specific origins
CORS(app, 
     resources={r"/api/*": {"origins": ["http://localhost:5000", "http://127.0.0.1:5000", "http://192.168.0.101:5000"], "supports_credentials": True}}, 
     supports_credentials=True,
     allow_headers=["Content-Type"],
     methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    email_verified = db.Column(db.Boolean, default=False)
    otp_code = db.Column(db.String(6))
    otp_expires_at = db.Column(db.DateTime)
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
            "created_at": self.created_at.isoformat(),
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
            "created_at": self.created_at.isoformat(),
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
            "created_at": self.created_at.isoformat(),
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
        user = User.query.get(user_id)
        if not user or user.role != "admin":
            return error_response("Not authorized.", 403)
        return f(*args, **kwargs)

    return decorated

def send_order_email(user_email, user_name, order_data, is_update=False):
    """Send order confirmation or status update email"""
    print(f"\n=== SENDING EMAIL ===")
    print(f"To: {user_email}")
    print(f"Name: {user_name}")
    print(f"Order ID: {order_data['id']}")
    print(f"Is Update: {is_update}")
    print(f"Email Configured: {bool(EMAIL_USER and EMAIL_PASSWORD)}")
    
    try:
        # Check if email configuration is set
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("ERROR: Email configuration not set in .env file")
            return False
            
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = user_email
        
        if is_update:
            msg['Subject'] = f"Order Status Update - Saffron India - Order #{order_data['id']:06d}"
            email_type = "Status Update"
        else:
            msg['Subject'] = f"Order Confirmation - Saffron India - Order #{order_data['id']:06d}"
            email_type = "Order Confirmation"

        print(f"Subject: {msg['Subject']}")

        # Create email body with proper data insertion
        # Handle different date formats
        try:
            order_date = datetime.strptime(order_data['created_at'], '%a, %d %b %Y %H:%M:%S GMT').strftime('%B %d, %Y')
        except ValueError:
            try:
                order_date = datetime.strptime(order_data['created_at'], '%Y-%m-%dT%H:%M:%S').strftime('%B %d, %Y')
            except ValueError:
                order_date = order_data['created_at'][:10]  # Fallback to YYYY-MM-DD format
        
        order_id_str = str(order_data['id']).zfill(6)

        # Determine status color
        status_colors = {
            'delivered': '#28a745',
            'shipped': '#007bff',
            'processing': '#ffc107',
            'pending': '#6c757d'
        }
        status_color = status_colors.get(order_data['status'], '#6c757d')

        # Build items table
        items_rows = ""
        for item in order_data['items']:
            # Use unit_price from database (the actual field name)
            item_price = item.get('unit_price', item.get('price', 0))
            item_total = item_price * item['qty']
            items_rows += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 12px;">{item['product_name']}</td>
                <td style="padding: 12px; text-align: center;">{item['qty']}</td>
                <td style="padding: 12px; text-align: right;">₹{item_price}</td>
                <td style="padding: 12px; text-align: right; font-weight: bold;">₹{item_total}</td>
            </tr>"""

        # Build address lines
        address_lines = f"""
        <p style="margin: 5px 0;">{order_data['full_name']}</p>
        <p style="margin: 5px 0;">{order_data['address_line1']}</p>"""

        if order_data.get('address_line2'):
            address_lines += f"<p style='margin: 5px 0;'>{order_data['address_line2']}</p>"

        address_lines += f"""
        <p style="margin: 5px 0;">{order_data['city']}, {order_data['postal_code']}</p>
        <p style="margin: 5px 0;">{order_data['country']}</p>"""

        # Email body template
        email_template = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
            <div style="background-color: #1a0c29; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: #d4af37; margin: 0; font-size: 28px;">Saffron India</h1>
                <p style="color: #f7f3e9; margin: 10px 0 0 0; font-size: 16px;">{email_type}</p>
            </div>

            <div style="background-color: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                {f"""
                <h2 style="color: #1a0c29; margin-bottom: 20px;">Your Order Status Has Been Updated!</h2>
                <p style="color: #333; line-height: 1.6; margin-bottom: 20px;">Dear {user_name},</p>
                <p style="color: #333; line-height: 1.6; margin-bottom: 20px;">Good news! Your order status has been updated. Here are the latest details:</p>
                """ if is_update else f"""
                <h2 style="color: #1a0c29; margin-bottom: 20px;">Thank You for Your Order!</h2>
                <p style="color: #333; line-height: 1.6; margin-bottom: 20px;">Dear {user_name},</p>
                <p style="color: #333; line-height: 1.6; margin-bottom: 20px;">We're pleased to confirm your order has been received and is being processed. Below are your order details:</p>
                """}

                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #d4af37;">
                    <h3 style="color: #1a0c29; margin-top: 0; margin-bottom: 15px;">Order Information</h3>
                    <p style="margin: 5px 0;"><strong>Order Number:</strong> #{order_id_str}</p>
                    <p style="margin: 5px 0;"><strong>Order Date:</strong> {order_date}</p>
                    <p style="margin: 5px 0;"><strong>Payment Method:</strong> {order_data['payment_method'].title()}</p>
                    <p style="margin: 5px 0;"><strong>Shipping Method:</strong> {order_data['shipping_method'].title()}</p>
                    <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{order_data['status'].title()}</span></p>
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
                    {f"""
                    <p style="margin: 0 0 10px 0; color: #666;">You can track your order status by visiting our website.</p>
                    <p style="margin: 0; color: #666;">We'll notify you of any further updates.</p>
                    """ if is_update else f"""
                    <p style="margin: 0 0 10px 0; color: #666;">You will receive email notifications for all status updates.</p>
                    <p style="margin: 0; color: #666;">Please keep this email for your records.</p>
                    """}
                </div>

                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                    <p style="color: #666; margin: 0;">Thank you for choosing Saffron India!</p>
                    <p style="color: #666; margin: 5px 0 0 0;">For any questions, please contact our customer support.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Use the email template directly (already formatted with Python string formatting)
        email_body = email_template
        
        # Attach HTML body
        msg.attach(MIMEText(email_body, 'html'))
        
        # Send email
        print(f"Connecting to SMTP server: {EMAIL_HOST}:{EMAIL_PORT}")
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        print("Connected to SMTP server")
        
        server.starttls()
        print("STARTTLS completed")
        
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        print("SMTP login successful")
        
        server.send_message(msg)
        print("Email sent successfully")
        
        server.quit()
        print("SMTP connection closed")
        
        email_type_str = "status update" if is_update else "confirmation"
        print(f"✅ Order {email_type_str} email sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send order email: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False


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
    
    # Remove any non-digit characters
    clean_phone = re.sub(r'[^\d]', '', phone)
    
    if len(clean_phone) != 10:
        return False, "Phone number must be exactly 10 digits"
    
    if not clean_phone.isdigit():
        return False, "Phone number must contain only digits"
    
    return True, clean_phone


def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))


def send_otp_email(email, otp):
    """Send OTP email for verification"""
    try:
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("ERROR: Email configuration not set")
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
                .header {{ background: #d4af37; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .otp {{ font-size: 32px; font-weight: bold; color: #d4af37; text-align: center; padding: 20px; background: white; border: 2px dashed #d4af37; border-radius: 8px; margin: 20px 0; letter-spacing: 5px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Saffron India</h1>
                <p>Email Verification</p>
            </div>
            
            <div class="content">
                <h2>Verify Your Email Address</h2>
                <p>Thank you for registering with Saffron India! To complete your registration, please use the following One-Time Password (OTP):</p>
                
                <div class="otp">{otp}</div>
                
                <p><strong>This OTP is valid for 10 minutes only.</strong></p>
                <p>If you didn't request this verification, please ignore this email.</p>
            </div>
            
            <div class="footer">
                <p>&copy; 2024 Saffron India. All rights reserved.</p>
                <p>Crafted with intention in Kashmir & Mumbai.</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ OTP email sent to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send OTP email: {e}")
        return False

@app.route("/api/register", methods=["POST"])
def register():
    payload = request.get_json() or {}

    required_fields = ["full_name", "email", "password", "phone"]
    if not all(payload.get(field) for field in required_fields):
        return error_response("Full name, email, password, and phone number are required.")

    email = payload["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return error_response("Email already registered.", 409)

    # Validate password
    password = payload["password"]
    is_valid, password_message = validate_password(password)
    if not is_valid:
        return error_response(password_message)

    # Validate phone number
    phone = payload["phone"]
    is_valid, phone_result = validate_phone(phone)
    if not is_valid:
        return error_response(phone_result)
    clean_phone = phone_result

    # Generate OTP
    otp = generate_otp()
    otp_expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Create user with OTP (unverified)
    user = User(
        full_name=payload["full_name"].strip(),
        email=email,
        phone=clean_phone,
        role="user",
        email_verified=False,
        otp_code=otp,
        otp_expires_at=otp_expires_at
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Send OTP email
    if send_otp_email(email, otp):
        return jsonify({
            "success": True, 
            "message": "Registration successful! Please check your email for OTP verification.",
            "user_id": user.id,
            "email": user.email
        }), 201
    else:
        # If email fails, still create user but inform them
        return jsonify({
            "success": True, 
            "message": "Registration successful! Email service unavailable. Please contact support to verify your account.",
            "user_id": user.id,
            "email": user.email
        }), 201


@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    """Verify OTP for email registration"""
    payload = request.get_json() or {}
    
    required_fields = ["email", "otp"]
    if not all(payload.get(field) for field in required_fields):
        return error_response("Email and OTP are required.")
    
    email = payload["email"].strip().lower()
    otp = payload["otp"].strip()
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return error_response("User not found.")
    
    if user.email_verified:
        return error_response("Email already verified.")
    
    # Check if OTP matches and is not expired
    if not user.otp_code or user.otp_code != otp:
        return error_response("Invalid OTP.")
    
    if datetime.utcnow() > user.otp_expires_at:
        return error_response("OTP has expired. Please request a new OTP.")
    
    # Mark email as verified and clear OTP
    user.email_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Email verified successfully! You can now login."
    })


@app.route("/api/resend-otp", methods=["POST"])
def resend_otp():
    """Resend OTP for email verification"""
    payload = request.get_json() or {}
    
    email = payload.get("email", "").strip().lower()
    if not email:
        return error_response("Email is required.")
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return error_response("User not found.")
    
    if user.email_verified:
        return error_response("Email already verified.")
    
    # Generate new OTP
    otp = generate_otp()
    otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    user.otp_code = otp
    user.otp_expires_at = otp_expires_at
    db.session.commit()
    
    # Send OTP email
    if send_otp_email(email, otp):
        return jsonify({
            "success": True,
            "message": "OTP has been resent to your email."
        })
    else:
        return error_response("Failed to send OTP. Please try again later.")


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

    # Store user ID in session
    session["user_id"] = user.id
    session["user_email"] = user.email

    # Check if user is admin and return appropriate redirect
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
    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return error_response("User not found.", 404)

    return jsonify({"success": True, "user": user.to_dict()})


@app.route("/api/orders", methods=["POST"])
@require_login
def create_order():
    payload = request.get_json() or {}
    items = payload.get("items") or []
    if not items:
        return error_response("Order must contain at least one item.")

    full_name = (payload.get("fullName") or "").strip()
    email = (payload.get("email") or "").strip()
    phone = (payload.get("phone") or "").strip()
    shipping_method = payload.get("shippingMethod") or "standard"
    payment_method = payload.get("paymentMethod") or "cod"
    notes = payload.get("notes") or ""
    address = payload.get("address") or {}

    if not full_name or not email or not phone:
        return error_response("Full name, email, and phone are required for orders.")

    subtotal = int(payload.get("subtotal") or 0)
    shipping_cost = int(payload.get("shippingCost") or 0)
    total = int(payload.get("total") or (subtotal + shipping_cost))

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
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        total=total,
    )

    db.session.add(order)
    db.session.flush()

    for item in items:
        product_name = (item.get("product") or "").strip()
        qty = int(item.get("qty") or 0)
        unit_price = int(item.get("price") or 0)
        if not product_name or qty <= 0 or unit_price < 0:
            continue
        order_item = OrderItem(
            order_id=order.id,
            product_name=product_name,
            qty=qty,
            unit_price=unit_price,
        )
        db.session.add(order_item)

    db.session.commit()

    # Send order confirmation email
    try:
        order_data = order.to_dict(include_items=True)
        email_sent = send_order_email(email, full_name, order_data, is_update=False)
        if email_sent:
            print(f"Order confirmation email sent successfully to {email}")
        else:
            print(f"Failed to send order confirmation email to {email}")
    except Exception as e:
        print(f"Error sending order email: {str(e)}")

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


# Product Management Endpoints
@app.route("/api/admin/products", methods=["GET"])
@require_admin
def admin_list_products():
    """Get all products for admin management"""
    products = Product.query.order_by(Product.created_at.desc()).all()
    return jsonify({"success": True, "products": [product.to_dict() for product in products]})

@app.route("/api/admin/products", methods=["POST"])
@require_admin
def admin_create_product():
    """Create a new product"""
    payload = request.get_json() or {}
    
    required_fields = ["name", "sku", "price"]
    if not all(payload.get(field) for field in required_fields):
        return error_response("Name, SKU, and price are required.")
    
    # Check if SKU already exists
    if Product.query.filter_by(sku=payload["sku"].strip()).first():
        return error_response("A product with this SKU already exists.", 409)
    
    product = Product(
        name=payload["name"].strip(),
        sku=payload["sku"].strip(),
        description=payload.get("description", "").strip(),
        price=int(payload["price"]),
        image_url=payload.get("image_url", "").strip(),
        active=payload.get("active", True)
    )
    
    db.session.add(product)
    db.session.commit()
    
    return jsonify({"success": True, "product": product.to_dict()}), 201

@app.route("/api/admin/products/<int:product_id>", methods=["PUT"])
@require_admin
def admin_update_product(product_id):
    """Update an existing product"""
    product = Product.query.get_or_404(product_id)
    payload = request.get_json() or {}
    
    # Update fields if provided
    if "name" in payload:
        product.name = payload["name"].strip()
    if "description" in payload:
        product.description = payload["description"].strip()
    if "price" in payload:
        product.price = int(payload["price"])
    if "image_url" in payload:
        product.image_url = payload["image_url"].strip()
    if "active" in payload:
        product.active = payload["active"]
    
    # Handle SKU change (check for duplicates)
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
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"success": True, "message": "Product deleted successfully"})


# Public Product Endpoints (for main website)
@app.route("/api/products", methods=["GET"])
def list_products():
    """Get all active products for the main website"""
    products = Product.query.filter_by(active=True).order_by(Product.created_at.desc()).all()
    return jsonify({"success": True, "products": [product.to_dict() for product in products]})

@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Get a single product by ID"""
    product = Product.query.get_or_404(product_id)
    if not product.active:
        return error_response("Product not found.", 404)
    return jsonify({"success": True, "product": product.to_dict()})

@app.route("/api/admin/analytics", methods=["GET"])
@require_admin
def admin_analytics():
    """Get comprehensive analytics including profit/loss and sales trends"""
    # Get date range from query params (default to last 12 months)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.utcnow() - timedelta(days=365)
        
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    else:
        end_date = datetime.utcnow()
    
    # Get orders within date range
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).all()
    
    # Calculate basic metrics
    total_orders = len(orders)
    total_revenue = sum(order.total for order in orders)
    total_shipping = sum(order.shipping_cost for order in orders)
    
    # Calculate profit (assuming 70% margin on products)
    # This is a simplified calculation - in real scenario you'd track cost prices
    estimated_cost = sum(order.subtotal * 0.3 for order in orders)  # 30% assumed cost
    gross_profit = total_revenue - estimated_cost - total_shipping
    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Monthly sales data
    monthly_sales = {}
    monthly_orders = {}
    
    for order in orders:
        month_key = order.created_at.strftime('%Y-%m')
        if month_key not in monthly_sales:
            monthly_sales[month_key] = 0
            monthly_orders[month_key] = 0
        monthly_sales[month_key] += order.total
        monthly_orders[month_key] += 1
    
    # Daily sales data (last 30 days)
    daily_sales = {}
    daily_orders = {}
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_orders = [o for o in orders if o.created_at >= thirty_days_ago]
    
    for order in recent_orders:
        day_key = order.created_at.strftime('%Y-%m-%d')
        if day_key not in daily_sales:
            daily_sales[day_key] = 0
            daily_orders[day_key] = 0
        daily_sales[day_key] += order.total
        daily_orders[day_key] += 1
    
    # Top selling products
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
    
    # Order status breakdown
    status_breakdown = {}
    for order in orders:
        status = order.status
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
    
    return jsonify({
        "success": True,
        "analytics": {
            "summary": {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "gross_profit": gross_profit,
                "profit_margin": round(profit_margin, 2),
                "total_shipping": total_shipping,
                "estimated_costs": estimated_cost,
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


@app.route("/api/admin/orders/<int:order_id>", methods=["PATCH"])
@require_admin
def admin_update_order(order_id):
    order = Order.query.get_or_404(order_id)
    payload = request.get_json() or {}
    status = payload.get("status")
    if status:
        order.status = status
    db.session.commit()
    return jsonify({"success": True, "order": order.to_dict(include_items=True)})


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    # Serve HTML files
    if filename.endswith(".html"):
        return send_from_directory(BASE_DIR, filename)
    # Serve CSS, JS, and other static files
    elif any(filename.endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"]):
        return send_from_directory(BASE_DIR, filename)
    else:
        return send_from_directory(BASE_DIR, filename)


@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database tables created.")


@app.cli.command("create-admin")
def create_admin():
    """Create an admin user for the system"""
    email = input("Enter admin email: ").strip().lower()
    password = input("Enter admin password: ").strip()
    full_name = input("Enter admin full name (optional): ").strip() or "Admin"
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        print(f"User with email {email} already exists!")
        return
    
    # Create admin user
    admin_user = User(
        full_name=full_name,
        email=email,
        phone="",
        role="admin",
        email_verified=True
    )
    admin_user.set_password(password)
    
    db.session.add(admin_user)
    db.session.commit()
    
    print(f"✓ Admin user created successfully!")
    print(f"  Email: {email}")
    print(f"  Name: {full_name}")
    print(f"  Role: admin")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

