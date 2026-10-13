# FreshCart - Online Supermarket Website

A modern, high-performance full-stack e-commerce grocery storefront built with FastAPI, Jinja2 server-rendered templates, and responsive design, engineered for seamless grocery shopping, catalog exploration, shopping cart workflows, seller product management, and administrative control.

---

## Overview

**FreshCart** (Online Super Market) is a digital grocery marketplace designed to streamline daily essentials shopping. It bridges the gap between everyday consumers and local grocery vendors, offering real-time product discovery, category-based browsing, dynamic shopping carts, user order history, seller product portals, and administrative oversight. The platform utilizes a dual-engine database architecture (MySQL with an automatic fallback to SQLite) ensuring high availability, reliable local execution, and effortless deployment.

---

## Features

- **Modern Responsive Storefront**: Clean, accessible, and mobile-friendly UI crafted with modern CSS custom properties, responsive flex/grid layouts, and interactive micro-animations.
- **Dynamic Product Catalog**: Filter products across categories (Fruits, Vegetables, Dairy, Bakery, Beverages, Snacks) with search and price filtering.
- **Shopping Cart & Checkout Workflow**: Persistent user cart with real-time total calculation, delivery fee handling, and streamlined simulated checkout.
- **Role-Based Access Control**:
  - **Customers**: Browse catalog, manage cart, place orders, view order history, update user profiles, and submit feedback.
  - **Sellers / Vendors**: Dedicated seller registration and portal for managing inventory, editing products, and monitoring order dispatches.
  - **Administrators**: Centralized admin dashboard for reviewing total sales, platform revenue, user lists, and category management.
- **Resilient Dual-Database Architecture**: Built-in support for MySQL with automatic fallback to local SQLite (`app.db`), guaranteeing zero-downtime execution out-of-the-box.
- **Security & Session Safety**: Secure password hashing using `werkzeug.security` (PBKDF2/SHA-256), encrypted session cookies via Starlette Session Middleware, and safe file upload handling.

---

## Technologies Used

- **Frontend**:
  - HTML5
  - CSS3 (Custom design system, flexbox, grid, responsive design)
  - JavaScript (Vanilla ES6+ for cart interactions, navbar toggling, dynamic UI)
  - Google Fonts (DM Sans, Space Grotesk)
- **Backend**:
  - Python 3
  - FastAPI (High-performance asynchronous Python web framework)
  - Starlette (Session middleware, static file serving)
  - Jinja2 (Templating engine)
  - Uvicorn (ASGI web server)
- **Database & Storage**:
  - MySQL (Production relational database)
  - SQLite (Automated fallback & development database)
  - PyMySQL (Pure Python MySQL client)
- **Security & Utilities**:
  - Werkzeug (Secure password hashing & secure filename handling)
  - python-dotenv (Environment configuration management)

---

## Project Structure

```
freshcart-ecommerce-website/
├── database.sql/
│   └── schema.sql            # MySQL relational schema DDL and table definitions
├── static/
│   ├── css/
│   │   ├── storefront.css    # Primary design system and responsive styles
│   │   └── style.css         # Utility styles
│   ├── js/
│   │   ├── navbar.js         # Mobile navigation drawer controller
│   │   └── storefront.js     # Cart operations, quantity updates, dynamic UI
│   └── images/               # Product photography, promotional banners, fonts
├── templates/
│   ├── admin_dashboard.html      # Administrator management control center
│   ├── cart.html                 # Active shopping cart and price calculation
│   ├── checkout.html             # Order checkout and shipping information
│   ├── feedback.html             # Customer reviews and feedback portal
│   ├── index.html                # Storefront homepage with hero and featured items
│   ├── login.html                # Customer, seller, and admin authentication
│   ├── orders.html               # Customer order history and status tracking
│   ├── product_details.html      # Detailed single product view
│   ├── products.html             # Full catalog with search and filters
│   ├── profile.html              # Customer profile management
│   ├── register.html             # New customer registration
│   ├── seller_dashboard.html     # Vendor inventory management portal
│   ├── seller-register.html      # Vendor onboarding registration
│   ├── seller_product_edit.html  # Product editor for sellers
│   └── user_dashboard.html       # Customer account overview
├── app.py                    # Main FastAPI application backend and routing
├── requirements.txt          # Python package dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules for virtualenvs, caches, and secrets
└── README.md                 # Project documentation
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10+ installed
- (Optional) MySQL Server 8.0+ running locally (or SQLite fallback will run automatically)

### 2. Clone the Repository
```bash
git clone https://github.com/saro053-prog/freshcart-ecommerce-website.git
cd freshcart-ecommerce-website
```

### 3. Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy the `.env.example` file to create your `.env` configuration:
```bash
cp .env.example .env
```
Edit `.env` to configure your database settings or leave as default for automatic SQLite mode.

### 6. Run the Application
```bash
python app.py
```
Or directly with Uvicorn:
```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

---

## Usage

1. Open your browser and navigate to:
   - Storefront Homepage: [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - All Products Catalog: [http://127.0.0.1:8000/products](http://127.0.0.1:8000/products)
   - Login & Portals: [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
2. Browse available grocery items, add products to your cart, and proceed to checkout.
3. Access Seller and Admin views to manage stock and review orders.

---

## Screenshots

| Storefront Hero & Promotions | Product Catalog & Categories |
|:---:|:---:|
| ![FreshCart Hero](static/images/hero-grocery.jpg) | ![FreshCart Deals](static/images/deal-groceries.jpg) |

---

## Future Improvements

- [ ] Integration with online payment gateways (Stripe / Razorpay).
- [ ] Email / SMS order confirmation notifications.
- [ ] Live delivery agent tracking via GPS integration.
- [ ] Customer product ratings and verified review system.
- [ ] Coupon code and seasonal discount engine.

---

## Author

**V. Saravanapandi**  
- GitHub: [@saro053-prog](https://github.com/saro053-prog)
- Email: [saro77057@gmail.com](mailto:saro77057@gmail.com)
