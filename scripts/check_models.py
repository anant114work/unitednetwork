#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'united_network_crm.settings')
django.setup()

def check_models():
    """Check if models are properly defined and importable"""
    print("🔍 Checking CRM Models...")
    print("=" * 50)
    
    try:
        # Import the models
        from crm.models import User, Project, ChannelPartner, Booking
        print("✅ User model found")
        print("✅ Project model found") 
        print("✅ ChannelPartner model found")
        print("✅ Booking model found")
        
        # Check User model specifically
        print(f"\n📋 User Model Details:")
        print(f"   - Model name: {User.__name__}")
        print(f"   - App label: {User._meta.app_label}")
        print(f"   - DB table: {User._meta.db_table}")
        print(f"   - Fields: {[f.name for f in User._meta.fields[:5]]}...")
        
        # Check if it's properly configured as AUTH_USER_MODEL
        from django.conf import settings
        print(f"\n⚙️  AUTH_USER_MODEL: {settings.AUTH_USER_MODEL}")
        
        if settings.AUTH_USER_MODEL == 'crm.User':
            print("✅ Custom User model properly configured")
        else:
            print("❌ AUTH_USER_MODEL not set to crm.User")
            
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def check_migrations():
    """Check migration status"""
    print("\n🔄 Checking Migrations...")
    print("=" * 50)
    
    from django.core.management import execute_from_command_line
    
    # Check if migrations exist
    migrations_dir = os.path.join('crm', 'migrations')
    if os.path.exists(migrations_dir):
        migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.py') and f != '__init__.py']
        if migration_files:
            print(f"✅ Found {len(migration_files)} migration files:")
            for f in migration_files:
                print(f"   - {f}")
        else:
            print("❌ No migration files found")
            return False
    else:
        print("❌ Migrations directory doesn't exist")
        return False
    
    return True

if __name__ == '__main__':
    print("🚀 Django CRM Model Checker")
    print("=" * 50)
    
    models_ok = check_models()
    migrations_ok = check_migrations()
    
    if models_ok and migrations_ok:
        print("\n✅ All checks passed! Models are properly configured.")
    else:
        print("\n❌ Issues found. Please fix the above errors.")
        
        if not models_ok:
            print("\n🔧 To fix model issues:")
            print("   1. Make sure crm/models.py exists and has proper imports")
            print("   2. Check that User class extends AbstractUser")
            print("   3. Verify AUTH_USER_MODEL = 'crm.User' in settings.py")
            
        if not migrations_ok:
            print("\n🔧 To fix migration issues:")
            print("   1. Run: python manage.py makemigrations crm")
            print("   2. Run: python manage.py migrate")
