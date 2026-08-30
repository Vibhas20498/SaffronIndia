# Saffron India Backend

Python/Flask API for handling authentication and persisting users in a MySQL database.

## Prerequisites

- Python 3.10+
- MySQL 8.x

## Setup

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

Create a database and user in MySQL:

```sql
CREATE DATABASE saffron_india CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'saffron_user'@'%' IDENTIFIED BY 'strongpassword';
GRANT ALL PRIVILEGES ON saffron_india.* TO 'saffron_user'@'%';
FLUSH PRIVILEGES;
```

Copy `.env.example` to `.env` (or set the environment variable another way) and update it with your credentials:

```
DATABASE_URL=mysql+mysqlconnector://saffron_user:strongpassword@localhost/saffron_india
```

Initialize the tables:

```bash
cd backend
flask --app app.py init-db
```

## Running the API

```bash
flask --app app.py run
# or simply
python app.py
```

## Endpoints

| Method | Path            | Description                     |
| ------ | --------------- | ------------------------------- |
| POST   | `/api/register` | Create a user account           |
| POST   | `/api/login`    | Verify credentials and log user |

Both endpoints expect/return JSON. Responses include `success`, `message`, and a `user` payload (without passwords).

