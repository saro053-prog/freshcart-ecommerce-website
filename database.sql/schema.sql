CREATE DATABASE IF NOT EXISTS online_supermarket;
USE online_supermarket;

CREATE TABLE IF NOT EXISTS user_account (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    dob DATE,
    mobile VARCHAR(30),
    address TEXT,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS seller (
    seller_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    shop_name VARCHAR(150) NOT NULL,
    gst_no VARCHAR(50),
    shop_address TEXT,
    mobile VARCHAR(30),
    email VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS product (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    brand_name VARCHAR(150),
    description TEXT,
    photo VARCHAR(255),
    price DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL DEFAULT 50,
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    category_id INT,
    seller_id INT,
    FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE SET NULL,
    FOREIGN KEY (seller_id) REFERENCES seller(seller_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS cart (
    cart_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    qty INT NOT NULL DEFAULT 1,
    UNIQUE KEY unique_cart_item (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES user_account(user_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    shipping_address TEXT NOT NULL,
    phone VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_account(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    seller_id INT,
    qty INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(product_id),
    FOREIGN KEY (seller_id) REFERENCES seller(seller_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    seller_id INT,
    comment TEXT,
    rating TINYINT NOT NULL,
    created_on DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_account(user_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE CASCADE,
    FOREIGN KEY (seller_id) REFERENCES seller(seller_id) ON DELETE SET NULL
);

INSERT INTO category (category_name)
SELECT 'Fresh Fruits & Vegetables' WHERE NOT EXISTS (SELECT 1 FROM category WHERE category_name = 'Fresh Fruits & Vegetables');

INSERT INTO category (category_name)
SELECT 'Dairy, Bakery & Eggs' WHERE NOT EXISTS (SELECT 1 FROM category WHERE category_name = 'Dairy, Bakery & Eggs');

INSERT INTO category (category_name)
SELECT 'Pantry & Cooking Essentials' WHERE NOT EXISTS (SELECT 1 FROM category WHERE category_name = 'Pantry & Cooking Essentials');

INSERT INTO category (category_name)
SELECT 'Snacks, Beverages & Instant Food' WHERE NOT EXISTS (SELECT 1 FROM category WHERE category_name = 'Snacks, Beverages & Instant Food');

INSERT INTO category (category_name)
SELECT 'Household & Personal Care' WHERE NOT EXISTS (SELECT 1 FROM category WHERE category_name = 'Household & Personal Care');

INSERT INTO admin (username, password)
SELECT 'admin', 'admin123' WHERE NOT EXISTS (SELECT 1 FROM admin WHERE username = 'admin');
