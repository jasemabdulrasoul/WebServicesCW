# COMP3011 Web Services and Web Data Coursework 1

This project is a basic payment/ordering system that is used for social events. This app will make managing booths in events easier by creating a role based
model to serve customers easily. The project uses Python Flask and RESTful API.

---

**About this app**

- RESTful API: all requests and responses are JSON.
- Two roles: **admin** (manages customers, restaurants, menu, orders, and users) and **restaurant** (manages only their own restaurant’s menu and orders).
- Customers have a balance; orders are paid from that balance. Restaurants can accept or reject orders.

**Getting started**

1. Install dependencies and set up the app (see project docs if needed).
2. Run the CLI script to create the first admin user.
3. Use the API at `/api` (e.g. login, then call the endpoints you need).

### Running

1. Install dependencies: `pip install -r requirements.txt`
2. Create your env file (optional for defaults): copy `.env.example` to `.env`
3. Create the first admin: `python create_admin.py --username admin --password "your_password"`
4. Start the server: `python app.py`

### Web pages (frontend)

- Home: `/`
- Customers: `/customers`
- Purchase (place an order): `/purchase`
- Transactions (view and update order status): `/transactions`
- Booths (admin): `/admin/booths`
- Users (admin): `/admin/users`

After you log in on the Home page, your login token is stored in your browser, and the pages will use it to call the `/api` endpoints.

### API authentication (JWT)

- Login: `POST /api/auth/login`
- For all protected API requests, include: `Authorization: Bearer <token>`

### API documentation

Full endpoint documentation: `API_DOCUMENTATION.md`