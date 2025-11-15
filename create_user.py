#!/usr/bin/env python3
"""
Script to create an initial admin user for the Instagram automation dashboard.
"""

from database import Database
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
mongo_conn_str = os.getenv('MONGO_CONNECTION_STRING')
mongo_db_name = os.getenv('MONGO_DATABASE_NAME')

if not mongo_conn_str or not mongo_db_name:
    print("Error: MONGO_CONNECTION_STRING and MONGO_DATABASE_NAME must be set in .env")
    exit(1)

db = Database(mongo_conn_str, mongo_db_name)

# Create admin user
username = input("Enter username for admin user (default: admin): ").strip() or "admin"
password = input("Enter password for admin user (default: password): ").strip() or "password"

db.create_user(username, password, 'admin')
print(f"Admin user '{username}' created successfully!")