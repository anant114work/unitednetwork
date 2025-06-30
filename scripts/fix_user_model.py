#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'united_network_crm.settings')
django.setup()

def fix_migrations():
    """Fix migration issues with custom User model"""
    print("🔧 Fixing User Model Migrations...")
    print("=" * 50)
    
    # Delete existing database
    db_path = 'db.sqlite3'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✅ Deleted old database")
    
    # Delete existing migrations
    migrations_dir = os.path.join('crm', 'migrations')
    if os.path.exists(migrations_dir):
        for file in os.listdir(migrations_dir):
            if file.endswith('.py') and file != '__init__.py':
                os.remove(os.path.join(migrations_dir, file))
                print(f"✅ Deleted migration: {file}")
    
    # Create migrations directory if it doesn't exist
    os.makedirs(migrations_dir, exist_ok=True)
    
    # Create __init__.py if it doesn't exist
    init_file = os.path.join(migrations_dir, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write('')
        print("✅ Created migrations/__init__.py")
    
    # Run makemigrations
    from django.core.management import execute_from_command_line
    
    print("\n🔄 Creating new migrations...")
    try:
        execute_from_command_line(['manage.py', 'makemigrations', 'crm'])
        print("✅ Migrations created successfully")
    except Exception as e:
        print(f"❌ Error creating migrations: {e}")
        return False
    
    print("\n🔄 Applying migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrations applied successfully")
    except Exception as e:
        print(f"❌ Error applying migrations: {e}")
        return False
    
    return True

if __name__ == '__main__':
    if fix_migrations():
        print("\n🎉 User model fixed successfully!")
        print("You can now run: python scripts/setup_database.py")
    else:
        print("\n❌ Failed to fix user model. Check the errors above.")
