#!/usr/bin/env python
"""
Force create migrations for CRM app
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'united_network_crm.settings')
django.setup()

from django.core.management import execute_from_command_line

def main():
    """Force create migrations and migrate"""
    print("🔧 Forcing CRM migrations...")
    
    try:
        # Force create migrations for CRM app
        print("Creating migrations for CRM app...")
        execute_from_command_line(['manage.py', 'makemigrations', 'crm', '--empty'])
        execute_from_command_line(['manage.py', 'makemigrations', 'crm'])
        
        # Apply migrations
        print("Applying migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("✅ Migrations completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
