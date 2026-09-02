-- ==========================================================
-- Saffron India - Supabase PostgreSQL Database Schema
-- Run this script in the Supabase SQL Editor:
-- Project Dashboard -> SQL Editor -> New Query -> Run
-- ==========================================================

-- Enable UUID extension if needed in future
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------
-- 1. USERS TABLE
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    phone VARCHAR(50),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    email_verified BOOLEAN DEFAULT FALSE,
    otp_code VARCHAR(255),
    otp_expires_at TIMESTAMP WITH TIME ZONE,
    otp_attempts INTEGER DEFAULT 0,
    otp_last_sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ----------------------------------------------------------
-- 2. PRODUCTS TABLE
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,  -- stored in Indian Rupees (INR)
    image_url VARCHAR(500),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(active);

-- ----------------------------------------------------------
-- 3. ORDERS TABLE
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    shipping_method VARCHAR(50) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    country VARCHAR(80),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(80),
    postal_code VARCHAR(20),
    notes TEXT,
    subtotal INTEGER NOT NULL,
    shipping_cost INTEGER NOT NULL,
    total INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

-- ----------------------------------------------------------
-- 4. ORDER ITEMS TABLE
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product_name VARCHAR(200) NOT NULL,
    qty INTEGER NOT NULL,
    unit_price INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- ----------------------------------------------------------
-- 5. INITIAL PRODUCT CATALOG SEED DATA
-- ----------------------------------------------------------
INSERT INTO products (name, sku, description, price, image_url, active)
VALUES
    (
        'Imperial Threads 2g',
        'threads',
        'Hand-picked stigmas with crocin levels above 250 for intense color and aroma. Premium Grade I saffron hand-picked from our Pampore estate at 5,000 ft altitude.',
        1999,
        'https://images.unsplash.com/photo-1453831210728-695502f9f795?auto=format&fit=crop&w=600&q=80',
        TRUE
    ),
    (
        'Reserve Threads 5g',
        'reserve',
        'Limited harvest lot numbered by hand and packed in violet glass. An exclusive limited-edition harvest from our finest Pampore fields.',
        4750,
        'https://images.unsplash.com/photo-1464306076886-da185f6a9d12?auto=format&fit=crop&w=600&q=80',
        TRUE
    ),
    (
        'Ceremonial Hamper',
        'hamper',
        'Includes saffron jar, tasting spoons, brass diya, and infusion guide in a handcrafted cedar box.',
        4499,
        'https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&w=600&q=80',
        TRUE
    ),
    (
        'Noor Wellness Elixir',
        'elixir',
        'Infuse into sparkling water or desserts for antioxidant-rich notes. Crafted with premium saffron, organic rose petals, cardamom, and raw Himalayan honey.',
        1299,
        'https://images.unsplash.com/photo-1457410129867-5999af49daf7?auto=format&fit=crop&w=600&q=80',
        TRUE
    )
ON CONFLICT (sku) DO NOTHING;
