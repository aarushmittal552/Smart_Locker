-- Smart RFID Locker Database Schema
-- Run this in MySQL to create the database and tables

-- Create database
CREATE DATABASE IF NOT EXISTS smart_security;
USE smart_security;

-- ============ USERS TABLE ============
-- Stores admin and user login credentials
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============ RFID CARDS TABLE ============
-- Maps RFID card UIDs to users and lockers
CREATE TABLE IF NOT EXISTS rfid_cards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uid VARCHAR(20) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL,
    locker_id VARCHAR(20) NOT NULL DEFAULT 'LOCKER_1',
    card_type ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

-- ============ LOCKERS TABLE ============
-- Stores locker information and current status
CREATE TABLE IF NOT EXISTS lockers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    locker_id VARCHAR(20) NOT NULL UNIQUE,
    location VARCHAR(100),
    status ENUM('LOCKED', 'UNLOCKED') DEFAULT 'LOCKED',
    current_pin VARCHAR(10) DEFAULT '1234',
    last_accessed TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============ LOGS TABLE ============
-- Stores all system events and access logs
CREATE TABLE IF NOT EXISTS logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message TEXT NOT NULL,
    log_type ENUM('access', 'intruder', 'admin', 'system', 'pin_change') DEFAULT 'system',
    locker_id VARCHAR(20),
    username VARCHAR(50),
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============ INTRUDER EVENTS TABLE ============
-- Stores intruder detection events with photo references
CREATE TABLE IF NOT EXISTS intruder_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uid VARCHAR(20),
    locker_id VARCHAR(20),
    photo_path VARCHAR(255),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============ INSERT DEFAULT DATA ============

-- Default admin user (password: admin123)
INSERT INTO users (username, password, role, email) VALUES 
('admin', 'admin123', 'admin', 'admin@smartlocker.com'),
('aarush', 'admin123', 'admin', 'aarush@smartlocker.com');

-- Default test user (password: user123)
INSERT INTO users (username, password, role, email) VALUES 
('user1', 'user123', 'user', 'user1@smartlocker.com'),
('testuser', 'test123', 'user', 'test@smartlocker.com');

-- Default locker
INSERT INTO lockers (locker_id, location, status, current_pin) VALUES 
('LOCKER_1', 'Main Building - Floor 1', 'LOCKED', '1234');

-- Sample RFID cards (replace UIDs with your actual card UIDs)
-- Get your card UID by scanning it and checking Serial Monitor
INSERT INTO rfid_cards (uid, username, locker_id, card_type) VALUES 
('A1B2C3D4', 'user1', 'LOCKER_1', 'user'),
('FFFFFFFF', 'admin', 'LOCKER_1', 'admin');

-- Initial system log
INSERT INTO logs (message, log_type) VALUES 
('System initialized', 'system');

-- ============ USEFUL QUERIES ============

-- View all users
-- SELECT * FROM users;

-- View all RFID cards with owner info
-- SELECT r.uid, r.username, r.locker_id, r.card_type, u.role 
-- FROM rfid_cards r JOIN users u ON r.username = u.username;

-- View recent logs
-- SELECT * FROM logs ORDER BY time DESC LIMIT 20;

-- View intruder events
-- SELECT * FROM intruder_events ORDER BY detected_at DESC;
