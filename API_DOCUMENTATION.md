# API Documentation (REST / JSON)

Base URL: `/api`

All endpoints use **JSON in / JSON out** and standard HTTP status codes.

## Common response format

Success responses are endpoint-specific.

Error responses (most failures) are returned as:
```json
{ "error": "Human-readable error message" }
```

## Authentication (JWT)

1. Login to get a JWT:
   - `POST /api/auth/login`
2. For protected endpoints, send:
   - `Authorization: Bearer <token>`

The `POST /api/auth/logout` endpoint exists, but since JWT is stateless, logout is effectively handled by discarding the token on the client.

## Roles

- `admin`
  - Full access to: customers, restaurants, menus, transactions, and users
- `restaurant`
  - Access is restricted to their own `restaurant_id`

The restaurant role can create purchases for their restaurant and accept/reject their own pending orders.

---

## Health / API root

### `GET /api/`

Response (`200`):
```json
{ "status": "ok", "message": "API is running" }
```

---

## Auth

### `POST /api/auth/login`

Body:
```json
{ "username": "string", "password": "string" }
```

Responses:
- `200`
```json
{
  "user": {
    "id": 1,
    "username": "admin_user",
    "role": "admin",
    "restaurant_id": null
  },
  "token": "<jwt>"
}
```
- `400` missing fields
- `401` invalid username/password

### `POST /api/auth/logout`

Headers: `Authorization: Bearer <token>`

Response (`200`):
```json
{ "message": "Logged out" }
```

---

## Customers (admin only)

### `GET /api/customers`

Query parameters (optional):
- `search` (matches `name` or `phone` via substring)
- `page` (default `1`)
- `per_page` (default `20`, max `50`)

Response (`200`):
```json
{
  "customers": [
    { "id": 1, "name": "Alice", "phone": "123", "balance": 50.0 }
  ],
  "page": 1,
  "per_page": 20,
  "total": 3
}
```

### `POST /api/customers`

Body:
```json
{ "name": "string", "phone": "string|null" }
```

Response (`201`):
```json
{ "id": 1, "name": "Alice", "phone": "123", "balance": 0.0 }
```

### `GET /api/customers/<customer_id>`

Response (`200`):
```json
{ "id": 1, "name": "Alice", "phone": "123", "balance": 50.0 }
```

Errors:
- `404` if not found
- `401` unauthenticated
- `403` not admin

### `PATCH /api/customers/<customer_id>`

Body (any subset):
```json
{ "name": "string", "phone": "string|null" }
```

Response (`200`): updated customer object

Errors:
- `404` if not found
- `400` if `name` becomes empty

### `DELETE /api/customers/<customer_id>`

Response (`200`):
```json
{ "message": "Customer deleted" }
```

### `POST /api/customers/<customer_id>/balance`

Body:
```json
{ "amount": 10.5, "action": "add" | "withdraw" }
```

Rules:
- withdrawing will fail if it would make the balance negative

Responses:
- `200`: returns updated customer:
```json
{ "id": 1, "name": "Alice", "phone": "123", "balance": 60.0 }
```
- `400`: invalid input / insufficient balance
- `404`: customer not found

---

## Restaurants

### `GET /api/restaurants`

Auth:
- `admin`: returns all restaurants
- `restaurant`: returns only their own restaurant (as a single-element list)

Response (`200`):
```json
{ "restaurants": [ { "id": 1, "name": "Booth A" } ] }
```

### `POST /api/restaurants` (admin only)

Body:
```json
{ "name": "string" }
```

Response (`201`):
```json
{ "id": 1, "name": "Booth A" }
```

### `GET /api/restaurants/<restaurant_id>`

Auth:
- `admin`: any restaurant
- `restaurant`: only their own

Response (`200`):
```json
{ "id": 1, "name": "Booth A" }
```

### `PATCH /api/restaurants/<restaurant_id>`

Body:
```json
{ "name": "string" }
```

Response (`200`): updated restaurant object

Errors:
- `404`: restaurant not found
- `400`: name empty / invalid
- `403`: not allowed

### `DELETE /api/restaurants/<restaurant_id>` (admin only)

Response (`200`):
```json
{ "message": "Restaurant deleted" }
```

---

## Menu (MenuItem; no options)

### `GET /api/restaurants/<restaurant_id>/menu`

Auth:
- `admin`: any restaurant
- `restaurant`: only their own

Response (`200`):
```json
{
  "menu_items": [
    { "id": 1, "restaurant_id": 1, "name": "Tea", "price": 5.0, "sold_out": false }
  ]
}
```

### `POST /api/restaurants/<restaurant_id>/menu`

Body:
```json
{ "name": "string", "price": 5.0, "sold_out": false }
```

Rules:
- `price` must be a positive number

Response (`201`): created menu item object (same shape as list items)

### `GET /api/restaurants/<restaurant_id>/menu/<menu_id>`

Response (`200`): menu item object

### `PATCH /api/restaurants/<restaurant_id>/menu/<menu_id>`

Body (any subset):
```json
{ "name": "string", "price": 6.0, "sold_out": true }
```

Response (`200`): updated menu item object

### `DELETE /api/restaurants/<restaurant_id>/menu/<menu_id>`

Response (`200`):
```json
{ "message": "Menu item deleted" }
```

---

## Transactions / Orders

Transaction `type` values:
- `purchase`
- `balance_add`
- `balance_withdraw`

Transaction `status` values:
- `pending`
- `accepted`
- `rejected`

### `GET /api/transactions`

Query parameters (optional):
- `customer_id` (int)
- `restaurant_id` (int)
- `status` (`pending` | `accepted` | `rejected`)
- `date_from` (ISO datetime string)
- `date_to` (ISO datetime string)
- `page` (default `1`)
- `per_page` (default `20`, max `50`)

Auth scoping:
- `restaurant` users are automatically restricted to their own `restaurant_id`

Response (`200`):
```json
{
  "transactions": [
    {
      "id": 1,
      "customer_id": 1,
      "restaurant_id": 1,
      "amount": 10.0,
      "type": "purchase",
      "status": "pending",
      "description": "Purchase order",
      "timestamp": "2026-03-17T12:34:56.000000"
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 3
}
```

### `POST /api/transactions` (create purchase)

Body:
```json
{
  "customer_id": 1,
  "restaurant_id": 1,
  "items": [
    { "menu_item_id": 1, "quantity": 2 }
  ]
}
```

Rules:
- restaurant role can only create purchases for their own `restaurant_id`
- each referenced menu item must belong to the specified restaurant
- sold-out menu items are rejected
- customer must have enough balance (`balance` will never go negative)

On success:
- deducts the computed total from the customer's balance
- creates one `Transaction`:
  - `type = "purchase"`
  - `status = "pending"`

Response (`201`):
```json
{
  "id": 1,
  "customer_id": 1,
  "restaurant_id": 1,
  "amount": 10.0,
  "type": "purchase",
  "status": "pending",
  "description": "Purchase order",
  "timestamp": "..."
}
```

Errors:
- `400`: invalid payload, insufficient balance, sold-out menu item, etc.
- `403`: restaurant scope violation
- `404`: customer or restaurant not found

### `GET /api/transactions/<transaction_id>`

Auth:
- `admin`: any transaction
- `restaurant`: only transactions whose `restaurant_id` matches their own

Response (`200`): transaction object

### `PATCH /api/transactions/<transaction_id>` (restaurant accept/reject)

Body:
```json
{ "status": "accepted" | "rejected" }
```

Rules:
- only restaurant role can call this
- only for `type = "purchase"`
- only when current `status = "pending"`
- restaurant must own the transaction’s `restaurant_id`

Response (`200`): updated transaction object

### `DELETE /api/transactions/<transaction_id>` (admin)

Auth: `admin` only

Rules:
- only `type = "purchase"`
- adds the purchase amount back to the customer balance
- deletes the transaction record

Response (`200`):
```json
{ "message": "Transaction deleted and balance reverted" }
```

---

## Users (admin only)

User `role` values:
- `admin`
- `restaurant`

Restaurant users always store `restaurant_id`.

### `GET /api/users`

Response (`200`):
```json
{
  "users": [
    { "id": 1, "username": "admin2", "role": "admin", "restaurant_id": null }
  ]
}
```

### `POST /api/users`

Body:
```json
{
  "username": "string",
  "password": "string",
  "role": "admin" | "restaurant",
  "restaurant_id": 1
}
```

Rules:
- username must be unique
- for `role = "restaurant"`, `restaurant_id` is required and must exist

Response (`201`): created user object

### `DELETE /api/users/<user_id>`

Response (`200`):
```json
{ "message": "User deleted" }
```

