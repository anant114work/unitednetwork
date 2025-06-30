#!/usr/bin/env python
"""
Setup script to create initial data for United Network CRM
"""
import os
import sys
import django
from decimal import Decimal

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'united_network_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from crm.models import (
    User, Project, ChannelPartner, CommissionSlab, Booking, 
    SystemSettings, ProjectCollateral
)

def create_admin_users():
    """Create admin users"""
    print("Creating admin users...")
    
    # Level 1 Admin (Super Admin)
    admin_l1, created = User.objects.get_or_create(
        username='+919999999999',
        defaults={
            'phone_number': '+919999999999',
            'email': 'admin@unitednetwork.com',
            'first_name': 'Super',
            'last_name': 'Admin',
            'user_type': 'admin_l1',
            'is_staff': True,
            'is_superuser': True,
            'is_verified': True
        }
    )
    if created:
        admin_l1.set_password('admin123')
        admin_l1.save()
        print(f"✅ Created Level 1 Admin: {admin_l1.phone_number}")
    
    # Level 2 Admin
    admin_l2, created = User.objects.get_or_create(
        username='+919999999998',
        defaults={
            'phone_number': '+919999999998',
            'email': 'admin2@unitednetwork.com',
            'first_name': 'Admin',
            'last_name': 'Level2',
            'user_type': 'admin_l2',
            'is_staff': True,
            'is_verified': True
        }
    )
    if created:
        admin_l2.set_password('admin123')
        admin_l2.save()
        print(f"✅ Created Level 2 Admin: {admin_l2.phone_number}")

def create_sample_projects():
    """Create sample projects"""
    print("Creating sample projects...")
    
    projects_data = [
        {
            'name': 'Skyline Towers',
            'code': 'SKY001',
            'developer': 'Skyline Developers',
            'location': 'Gurgaon',
            'description': 'Luxury residential towers with modern amenities',
            'price_range': '₹80L - ₹2.5Cr',
            'status': 'active'
        },
        {
            'name': 'Green Valley Homes',
            'code': 'GVH002',
            'developer': 'Green Valley Group',
            'location': 'Noida',
            'description': 'Eco-friendly homes with green spaces',
            'price_range': '₹60L - ₹1.8Cr',
            'status': 'active'
        },
        {
            'name': 'Metro Heights',
            'code': 'MH003',
            'developer': 'Metro Builders',
            'location': 'Delhi',
            'description': 'Premium apartments near metro station',
            'price_range': '₹1.2Cr - ₹3.5Cr',
            'status': 'active'
        },
        {
            'name': 'Riverside Residency',
            'code': 'RR004',
            'developer': 'Riverside Developers',
            'location': 'Pune',
            'description': 'Waterfront living with scenic views',
            'price_range': '₹70L - ₹2.2Cr',
            'status': 'active'
        },
        {
            'name': 'Tech Park Apartments',
            'code': 'TPA005',
            'developer': 'Tech Builders',
            'location': 'Bangalore',
            'description': 'Modern apartments near IT parks',
            'price_range': '₹65L - ₹1.9Cr',
            'status': 'active'
        }
    ]
    
    for project_data in projects_data:
        project, created = Project.objects.get_or_create(
            code=project_data['code'],
            defaults=project_data
        )
        if created:
            print(f"✅ Created project: {project.name}")

def create_commission_slabs():
    """Create default commission slabs"""
    print("Creating commission slabs...")
    
    projects = Project.objects.all()
    
    for project in projects:
        # Default commission slabs
        slabs_data = [
            {'min_amount': 0, 'max_amount': 5000000, 'commission_percentage': 2.0},
            {'min_amount': 5000001, 'max_amount': 10000000, 'commission_percentage': 2.5},
            {'min_amount': 10000001, 'max_amount': 20000000, 'commission_percentage': 3.0},
            {'min_amount': 20000001, 'max_amount': 50000000, 'commission_percentage': 3.5},
            {'min_amount': 50000001, 'max_amount': 999999999, 'commission_percentage': 4.0},
        ]
        
        for slab_data in slabs_data:
            slab, created = CommissionSlab.objects.get_or_create(
                project=project,
                cp=None,  # Default slab
                min_amount=slab_data['min_amount'],
                max_amount=slab_data['max_amount'],
                defaults={
                    'commission_percentage': slab_data['commission_percentage'],
                    'is_default': True
                }
            )
            if created:
                print(f"✅ Created commission slab for {project.name}: {slab.commission_percentage}%")

def create_sample_cps():
    """Create sample Channel Partners"""
    print("Creating sample Channel Partners...")
    
    cps_data = [
        {
            'phone_number': '+919876543210',
            'email': 'cp1@example.com',
            'first_name': 'Rajesh',
            'last_name': 'Kumar',
            'company_name': 'Kumar Properties',
            'rera_number': 'RERA001',
            'pan_number': 'ABCDE1234F',
            'bank_name': 'HDFC Bank',
            'account_number': '12345678901',
            'ifsc_code': 'HDFC0001234',
            'address': '123 Business District, Delhi'
        },
        {
            'phone_number': '+919876543211',
            'email': 'cp2@example.com',
            'first_name': 'Priya',
            'last_name': 'Sharma',
            'company_name': 'Sharma Realty',
            'rera_number': 'RERA002',
            'pan_number': 'FGHIJ5678K',
            'bank_name': 'ICICI Bank',
            'account_number': '98765432101',
            'ifsc_code': 'ICIC0001234',
            'address': '456 Commercial Complex, Mumbai'
        },
        {
            'phone_number': '+919876543212',
            'email': 'cp3@example.com',
            'first_name': 'Amit',
            'last_name': 'Patel',
            'company_name': 'Patel Estates',
            'rera_number': 'RERA003',
            'pan_number': 'KLMNO9012P',
            'bank_name': 'SBI',
            'account_number': '11223344556',
            'ifsc_code': 'SBIN0001234',
            'address': '789 Trade Center, Ahmedabad'
        }
    ]
    
    for cp_data in cps_data:
        user, created = User.objects.get_or_create(
            username=cp_data['phone_number'],
            defaults={
                'phone_number': cp_data['phone_number'],
                'email': cp_data['email'],
                'first_name': cp_data['first_name'],
                'last_name': cp_data['last_name'],
                'user_type': 'cp',
                'is_verified': True
            }
        )
        
        if created:
            user.set_password('cp123')
            user.save()
            
            cp = ChannelPartner.objects.create(
                user=user,
                company_name=cp_data['company_name'],
                rera_number=cp_data['rera_number'],
                pan_number=cp_data['pan_number'],
                bank_name=cp_data['bank_name'],
                account_number=cp_data['account_number'],
                ifsc_code=cp_data['ifsc_code'],
                address=cp_data['address']
            )
            print(f"✅ Created CP: {cp.cp_code} - {cp.company_name}")

def create_team_members():
    """Create sample team members"""
    print("Creating team members...")
    
    team_data = [
        {
            'phone_number': '+919876543220',
            'email': 'rm1@unitednetwork.com',
            'first_name': 'Suresh',
            'last_name': 'Gupta',
            'user_type': 'rm'
        },
        {
            'phone_number': '+919876543221',
            'email': 'teamhead1@unitednetwork.com',
            'first_name': 'Meera',
            'last_name': 'Singh',
            'user_type': 'team_head'
        },
        {
            'phone_number': '+919876543222',
            'email': 'teamleader1@unitednetwork.com',
            'first_name': 'Vikash',
            'last_name': 'Yadav',
            'user_type': 'team_leader'
        }
    ]
    
    for member_data in team_data:
        user, created = User.objects.get_or_create(
            username=member_data['phone_number'],
            defaults={
                'phone_number': member_data['phone_number'],
                'email': member_data['email'],
                'first_name': member_data['first_name'],
                'last_name': member_data['last_name'],
                'user_type': member_data['user_type'],
                'is_verified': True
            }
        )
        
        if created:
            user.set_password('team123')
            user.save()
            print(f"✅ Created {member_data['user_type']}: {user.get_full_name()}")

def create_sample_bookings():
    """Create sample bookings"""
    print("Creating sample bookings...")
    
    cps = ChannelPartner.objects.all()
    projects = Project.objects.all()
    rm = User.objects.filter(user_type='rm').first()
    
    if not rm:
        print("❌ No RM found. Creating sample RM...")
        rm = User.objects.create_user(
            username='+919876543230',
            phone_number='+919876543230',
            email='rm@unitednetwork.com',
            first_name='Sample',
            last_name='RM',
            user_type='rm',
            is_verified=True
        )
        rm.set_password('rm123')
        rm.save()
    
    bookings_data = [
        {
            'customer_name': 'Rohit Sharma',
            'customer_phone': '+919999888877',
            'customer_email': 'rohit@example.com',
            'customer_address': '123 Customer Street, Delhi',
            'unit_type': '3bhk',
            'booking_amount': 500000,
            'total_amount': 8500000,
            'status': 'approved'
        },
        {
            'customer_name': 'Anita Desai',
            'customer_phone': '+919999888876',
            'customer_email': 'anita@example.com',
            'customer_address': '456 Buyer Lane, Mumbai',
            'unit_type': '2bhk',
            'booking_amount': 300000,
            'total_amount': 6200000,
            'status': 'requested'
        },
        {
            'customer_name': 'Kiran Patel',
            'customer_phone': '+919999888875',
            'customer_email': 'kiran@example.com',
            'customer_address': '789 Client Road, Pune',
            'unit_type': '4bhk',
            'booking_amount': 800000,
            'total_amount': 12500000,
            'status': 'completed'
        }
    ]
    
    for i, booking_data in enumerate(bookings_data):
        cp = cps[i % len(cps)]
        project = projects[i % len(projects)]
        
        booking = Booking.objects.create(
            project=project,
            cp=cp,
            rm=rm,
            customer_name=booking_data['customer_name'],
            customer_phone=booking_data['customer_phone'],
            customer_email=booking_data['customer_email'],
            customer_address=booking_data['customer_address'],
            unit_type=booking_data['unit_type'],
            booking_amount=booking_data['booking_amount'],
            total_amount=booking_data['total_amount'],
            status=booking_data['status'],
            commission_percentage=Decimal('2.5'),
            commission_amount=booking_data['total_amount'] * Decimal('0.025')
        )
        print(f"✅ Created booking: {booking.booking_id}")

def create_system_settings():
    """Create system settings"""
    print("Creating system settings...")
    
    settings, created = SystemSettings.objects.get_or_create(
        id=1,
        defaults={
            'total_cp_count': ChannelPartner.objects.filter(user__user_type='cp').count(),
            'mlm_activated': False,
            'mlm_activation_threshold': 1000,
            'commission_visibility_internal': False
        }
    )
    
    if created:
        print("✅ Created system settings")
    else:
        # Update CP count
        settings.total_cp_count = ChannelPartner.objects.filter(user__user_type='cp').count()
        settings.save()
        print("✅ Updated system settings")

def create_project_collaterals():
    """Create sample project collaterals"""
    print("Creating project collaterals...")
    
    projects = Project.objects.all()
    
    collateral_types = [
        ('brochure', 'Project Brochure'),
        ('floor_plan', 'Floor Plans'),
        ('price_list', 'Price List'),
        ('amenities', 'Amenities Guide'),
        ('location_map', 'Location Map')
    ]
    
    for project in projects:
        for collateral_type, title in collateral_types:
            collateral, created = ProjectCollateral.objects.get_or_create(
                project=project,
                title=f"{project.name} - {title}",
                collateral_type=collateral_type,
                defaults={
                    'description': f'{title} for {project.name}',
                    'is_public': collateral_type in ['brochure', 'location_map']
                }
            )
            if created:
                print(f"✅ Created collateral: {collateral.title}")

def main():
    """Main setup function"""
    print("🚀 Setting up United Network CRM Database...")
    print("=" * 50)
    
    try:
        create_admin_users()
        create_sample_projects()
        create_commission_slabs()
        create_sample_cps()
        create_team_members()
        create_sample_bookings()
        create_system_settings()
        create_project_collaterals()
        
        print("=" * 50)
        print("✅ Database setup completed successfully!")
        print("\n📋 Login Credentials:")
        print("=" * 30)
        print("🔑 Admin Login:")
        print("   Phone: +919999999999")
        print("   Password: admin123")
        print("\n🔑 CP Login:")
        print("   Phone: +919876543210")
        print("   Password: cp123")
        print("\n🔑 RM Login:")
        print("   Phone: +919876543220")
        print("   Password: team123")
        print("\n🌐 Access the application at: http://localhost:8000")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
