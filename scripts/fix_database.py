#!/usr/bin/env python
"""
Fix database issues and recreate tables
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
    """Fix database issues"""
    print("🔧 Fixing database issues...")
    print("=" * 40)
    
    try:
        # Delete corrupted database
        db_path = 'db.sqlite3'
        if os.path.exists(db_path):
            os.remove(db_path)
            print("✅ Removed corrupted database")
        
        # Create migrations
        print("📝 Creating migrations...")
        execute_from_command_line(['manage.py', 'makemigrations'])
        
        # Apply migrations
        print("🔄 Applying migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("✅ Database fixed successfully!")
        print("Now run: python scripts/setup_database.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
