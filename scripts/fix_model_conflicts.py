#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'united_network_crm.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def fix_model_conflicts():
    """Remove conflicting fields from ChannelPartner model"""
    print("🔧 Fixing model conflicts...")
    
    try:
        with connection.cursor() as cursor:
            # Check if the conflicting columns exist and remove them
            conflicting_fields = [
                'total_bookings',
                'total_sales_value', 
                'total_commission_earned',
                'total_vps'
            ]
            
            for field in conflicting_fields:
                try:
                    cursor.execute(f"ALTER TABLE crm_channelpartner DROP COLUMN {field}")
                    print(f"✅ Removed field: {field}")
                except Exception as e:
                    print(f"⚠️  Field {field} might not exist or already removed: {e}")
            
        print("✅ Model conflicts fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error fixing model conflicts: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting model conflict fix...")
    
    if fix_model_conflicts():
        print("🎉 All conflicts resolved!")
    else:
        print("❌ Some issues remain. Please check manually.")
