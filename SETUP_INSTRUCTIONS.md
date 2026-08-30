# Setup Instructions for Saffron India Backend

## Prerequisites
- Python 3.10 or higher installed
- MySQL 8.x installed and running

## Step 1: Create MySQL Database

Open MySQL command line or MySQL Workbench and run:

```sql
CREATE DATABASE saffron_india CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'saffron_user'@'localhost' IDENTIFIED BY 'your_password_here';
GRANT ALL PRIVILEGES ON saffron_india.* TO 'saffron_user'@'localhost';
FLUSH PRIVILEGES;
```

**Note:** Replace `'your_password_here'` with a strong password of your choice.

## Step 2: Set Up Python Environment

### Option A: Use the Setup Script (Easiest)

**In PowerShell:**
```powershell
cd backend
.\setup.ps1
```

**In Command Prompt:**
```cmd
cd backend
setup.bat
```

### Option B: Manual Setup

**In PowerShell:**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**If you get an execution policy error in PowerShell, run this first:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**In Command Prompt:**
```cmd
cd backend
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

**Important:** Run each command separately, not all at once!

## Step 3: Configure Database Connection

Create a file named `.env` in the `backend` folder with your MySQL credentials:

```
DATABASE_URL=mysql+mysqlconnector://saffron_user:your_password_here@localhost/saffron_india
```

**Replace:**
- `saffron_user` with your MySQL username
- `your_password_here` with your MySQL password
- `localhost` if your MySQL is on a different host
- `saffron_india` with your database name (if different)

## Step 4: Initialize Database Tables

While still in the `backend` folder with the virtual environment activated:

```powershell
flask --app app.py init-db
```

You should see: "Database tables created."

## Step 5: Start the Backend Server

Keep the virtual environment activated and run:

```powershell
python app.py
```

Or:

```powershell
flask --app app.py run
```

The server will start on `http://127.0.0.1:5000`

## Step 6: Test the Setup

1. Keep the backend server running
2. Open `register.html` in your browser
3. Try creating an account
4. Then try logging in with those credentials on `login.html`

## Troubleshooting

- **"The system cannot find the path specified"**: 
  - Make sure you're in the `backend` folder: `cd backend`
  - Run commands one at a time, not all together
  - If using PowerShell, try: `.\venv\Scripts\Activate.ps1` instead of `.\venv\Scripts\activate`
  - Or use the setup script: `.\setup.ps1` or `setup.bat`

- **PowerShell execution policy error**: 
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

- **MySQL connection error**: Make sure MySQL is running and your credentials in `.env` are correct

- **Module not found**: Make sure you activated the virtual environment (`.\venv\Scripts\Activate.ps1` in PowerShell or `venv\Scripts\activate.bat` in CMD)

- **Port already in use**: Change the port in `app.py` or stop the other service using port 5000

