#!/usr/bin/env python3
"""
Add OTP columns to existing database
"""

import os
import sys
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_config():
    """Get database configuration from environment or use defaults"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'saffron_india')
    }

def add_otp_columns():
    """Add OTP verification columns to users table"""
    
    db_config = get_db_config()
    
    try:
        print("Connecting to database...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        print("Checking existing columns...")
        cursor.execute("DESCRIBE users")
        columns = [column[0] for column in cursor.fetchall()]
        print(f"Existing columns: {', '.join(columns)}")
        
        # Add email_verified column if not exists
        if 'email_verified' not in columns:
            print("Adding email_verified column...")
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE")
            print("✓ email_verified column added")
        else:
            print("✓ email_verified column already exists")
        
        # Add otp_code column if not exists
        if 'otp_code' not in columns:
            print("Adding otp_code column...")
            cursor.execute("ALTER TABLE users ADD COLUMN otp_code VARCHAR(6)")
            print("✓ otp_code column added")
        else:
            print("✓ otp_code column already exists")
        
        # Add otp_expires_at column if not exists
        if 'otp_expires_at' not in columns:
            print("Adding otp_expires_at column...")
            cursor.execute("ALTER TABLE users ADD COLUMN otp_expires_at DATETIME")
            print("✓ otp_expires_at column added")
        else:
            print("✓ otp_expires_at column already exists")
        
        conn.commit()
        
        # Verify columns were added
        cursor.execute("DESCRIBE users")
        updated_columns = [column[0] for column in cursor.fetchall()]
        print(f"Updated columns: {', '.join(updated_columns)}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database OTP columns updated successfully!")
        return True
        
    except mysql.connector.Error as err:
        print(f"❌ Database error: {err}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    try:
        print("🔧 Adding OTP verification columns to database...")
        
        if add_otp_columns():
            print("\n🎉 Database migration completed successfully!")
            print("\nThe user registration with OTP verification is now ready.")
        else:
            print("\n❌ Database migration failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
