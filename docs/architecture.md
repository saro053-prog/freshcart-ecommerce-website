# FreshCart - System Architecture & Engineering Specifications

## 1. High-Level Architecture

FreshCart is built as a high-performance web application utilizing **FastAPI**, an asynchronous Python ASGI web framework, combined with server-rendered Jinja2 templates and a relational persistence layer.

```mermaid
graph TD
    Client["Client Browser (Responsive HTML5, CSS3, Vanilla ES6+)"] -->|HTTP / Form Data / JSON| Uvicorn["Uvicorn ASGI Server"]
    Uvicorn --> FastAPI["FastAPI Application (Routing & Controllers)"]
    FastAPI --> SessionMiddleware["Starlette Session Middleware (Encrypted Cookies)"]
    FastAPI --> Security["Werkzeug Security (PBKDF2 Password Hashing)"]
    FastAPI --> Jinja2["Jinja2 Server-Side Template Renderer"]
    FastAPI --> DBRouter["Database Router & Connection Layer"]
    DBRouter --> MySQL[("MySQL 8.0 Database (Production)")]
    DBRouter -.->|Fallback| SQLite[("SQLite Engine (Development / Zero-Downtime)")]
```

---

## 2. Relational Data Model (ER Diagram)

```mermaid
erDiagram
    USER_ACCOUNT ||--o{ CART : "owns"
    USER_ACCOUNT ||--o{ ORDERS : "places"
    USER_ACCOUNT ||--o{ FEEDBACK : "submits"
    SELLER ||--o{ PRODUCT : "supplies"
    CATEGORY ||--o{ PRODUCT : "groups"
    PRODUCT ||--o{ CART : "item_in"
    ORDERS ||--o{ ORDER_ITEMS : "contains"
    PRODUCT ||--o{ ORDER_ITEMS : "referenced_by"

    USER_ACCOUNT {
        int user_id PK
        string name
        string email UK
        string password_hash
        string phone
        string address
    }

    SELLER {
        int seller_id PK
        string store_name
        string email UK
        string password_hash
        string phone
        string status
    }

    CATEGORY {
        int category_id PK
        string category_name UK
        string description
    }

    PRODUCT {
        int product_id PK
        int category_id FK
        int seller_id FK
        string product_name
        decimal price
        int stock_quantity
        string image_path
    }

    CART {
        int cart_id PK
        int user_id FK
        int product_id FK
        int quantity
    }

    ORDERS {
        int order_id PK
        int user_id FK
        decimal total_amount
        string order_status
        datetime order_date
        string shipping_address
    }

    ORDER_ITEMS {
        int order_item_id PK
        int order_id FK
        int product_id FK
        int quantity
        decimal unit_price
    }
```

---

## 3. Security & Data Integrity

1. **Password Encryption**: All customer, seller, and administrator passwords are encrypted via `werkzeug.security.generate_password_hash` using PBKDF2 with SHA-256 HMAC and random salts.
2. **Session Security**: Session cookies are signed with an HMAC secret key and configured with `HttpOnly` and `SameSite=Lax` flags to prevent cross-site scripting (XSS) session theft.
3. **Dual-Database Resiliency**: The database layer connects to MySQL via `pymysql` with automated connection timeouts. If MySQL is unreachable, it automatically provisions and switches to SQLite (`app.db`), guaranteeing zero runtime crashes.
