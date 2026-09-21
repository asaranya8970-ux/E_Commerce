# ShopSphere — E-Commerce Web Application

A complete beginner-friendly full-stack e-commerce application built with **Flask + MySQL + HTML/CSS/JavaScript**.

## Features covered
- Product catalog and search
- Add to cart and checkout
- User registration/login/logout
- Role-based access: USER and ADMIN
- Admin product add/delete management
- Backend REST APIs for products and orders
- MySQL database integration
- Order tracking: Placed → Processing → Shipped → Delivered
- Admin order status updates
- Stock validation and stock reduction after checkout
- Responsive UI

## Run locally on Windows + XAMPP
1. Install/start **MySQL** from XAMPP.
2. Open PowerShell in this project folder.
3. Create a virtual environment:
   `python -m venv venv`
4. Activate it:
   `venv\Scripts\Activate.ps1`
5. Install packages:
   `pip install -r requirements.txt`
6. Optional: copy `.env.example` to `.env` and set your MySQL password. If XAMPP root has no password, the defaults already work.
7. Start the app:
   `python app.py`
8. Open http://127.0.0.1:5000

The first run automatically creates `ecommerce_db`, tables, demo products and the admin account.

### Admin demo
- Email: `admin@shop.com`
- Password: `admin123`

Change the admin password before deploying publicly.

## API summary
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/products`
- `POST /api/products` (ADMIN)
- `PUT /api/products/:id` (ADMIN)
- `DELETE /api/products/:id` (ADMIN)
- `POST /api/orders` (USER)
- `GET /api/orders` (USER)
- `GET /api/admin/orders` (ADMIN)
- `PUT /api/admin/orders/:id` (ADMIN)
- `GET /api/admin/stats` (ADMIN)

## Updated UI
The latest version starts with a dedicated **white, minimal login page with dark accents**. Users can sign in, create an account, or use the demo admin account before entering the shopping dashboard.

Demo admin:
- Email: `admin@shop.com`
- Password: `admin123`
