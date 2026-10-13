# FreshCart - API & Route Reference

Base URL: `http://127.0.0.1:8000`

---

## 1. Storefront & Catalog

- `GET /` — Homepage with hero banner, promotional grocery deals, and category shortcuts.
- `GET /products` — Product catalog with category and price query filters (`?category_id=1&q=apple`).
- `GET /product/{product_id}` — Detailed single product view with nutritional specs and stock status.

---

## 2. Authentication & User Portals

- `GET /login` — Unified authentication portal for customers, sellers, and administrators.
- `POST /login` — Authenticates credentials and initializes signed session cookies.
- `GET /register` — New customer registration view.
- `POST /register` — Processes customer sign-up with password hashing.
- `GET /logout` — Terminates active session.
- `GET /user/dashboard` — Customer dashboard showing active orders and account details.
- `GET /user/profile` — Profile settings and address updates.

---

## 3. Shopping Cart & Checkout

- `GET /cart` — View current shopping cart items, line item totals, and delivery charges.
- `POST /cart/add/{product_id}` — Adds product to user cart or increments item quantity.
- `POST /cart/update/{product_id}` — Modifies line item quantity.
- `POST /cart/remove/{product_id}` — Removes an item from the cart.
- `GET /checkout` — Order summary and delivery address confirmation.
- `POST /checkout` — Submits order, creates order item records, and clears cart.
- `GET /orders` — User order history with tracking statuses (`Processing`, `Shipped`, `Delivered`).

---

## 4. Seller & Vendor Management

- `GET /seller/register` — Vendor onboarding registration view.
- `POST /seller/register` — Registers new grocery merchant store.
- `GET /seller/dashboard` — Merchant inventory portal with product listing and sales counts.
- `POST /seller/product/add` — Adds a new grocery inventory item.
- `POST /seller/product/edit/{product_id}` — Updates product details, prices, and stock counts.

---

## 5. Administrative Oversight

- `GET /admin/dashboard` — Administrator dashboard with total sales metrics, platform revenue, and user registries.
- `GET /api/health` — System status and active database engine connectivity check.
