-- SQL Queries to View Registered Users in MySQL Workbench
-- Copy and paste these queries into MySQL Workbench

-- 1. View all users (including password hash - for admin use only)
SELECT * FROM users;

-- 2. View users with readable information (excluding password hash)
SELECT 
    id,
    full_name,
    email,
    phone,
    created_at
FROM users
ORDER BY created_at DESC;

-- 3. Count total registered users
SELECT COUNT(*) AS total_users FROM users;

-- 4. View users registered today
SELECT 
    id,
    full_name,
    email,
    phone,
    created_at
FROM users
WHERE DATE(created_at) = CURDATE()
ORDER BY created_at DESC;

-- 5. View users with their registration date formatted nicely
SELECT 
    id,
    full_name,
    email,
    phone,
    DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS registration_date
FROM users
ORDER BY created_at DESC;

-- 6. Search for a specific user by email
-- Replace 'user@example.com' with the email you want to search
SELECT 
    id,
    full_name,
    email,
    phone,
    created_at
FROM users
WHERE email = 'user@example.com';

-- 7. View users registered in the last 7 days
SELECT 
    id,
    full_name,
    email,
    phone,
    created_at
FROM users
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY created_at DESC;

