import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'united_network_crm.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from crm.models import User, Project, ChannelPartner
from django.db import transaction

def reset_sample_data():
    with transaction.atomic():
        print('Clearing existing data...')
        
        # Delete all projects
        Project.objects.all().delete()
        
        # Delete all users except 8882443789
        User.objects.exclude(phone_number='8882443789').delete()
        ChannelPartner.objects.exclude(user__phone_number='8882443789').delete()
        
        # Update 8882443789 to CP if not already
        try:
            cp_user = User.objects.get(phone_number='8882443789')
            cp_user.user_type = 'cp'
            cp_user.save()
            
            # Ensure CP profile exists
            if not hasattr(cp_user, 'channelpartner'):
                ChannelPartner.objects.create(
                    user=cp_user,
                    company_name='Demo Company',
                    pan_number='DEMO12345',
                    bank_name='Demo Bank',
                    account_number='1234567890',
                    ifsc_code='DEMO0001',
                    address='Demo Address'
                )
        except User.DoesNotExist:
            # Create CP user if doesn't exist
            cp_user = User.objects.create_user(
                username='8882443789',
                phone_number='8882443789',
                first_name='Demo',
                last_name='CP',
                email='demo@cp.com',
                user_type='cp',
                is_verified=True
            )
            ChannelPartner.objects.create(
                user=cp_user,
                company_name='Demo Company',
                pan_number='DEMO12345',
                bank_name='Demo Bank',
                account_number='1234567890',
                ifsc_code='DEMO0001',
                address='Demo Address'
            )
        
        # Create Admin user
        admin_user = User.objects.create_user(
            username='9999999999',
            phone_number='9999999999',
            first_name='Admin',
            last_name='User',
            email='admin@bop.com',
            user_type='admin_l1',
            is_verified=True,
            is_staff=True,
            is_superuser=True
        )
        admin_user.set_password('12345')
        admin_user.save()
        
        # Create RM user
        rm_user = User.objects.create_user(
            username='9999999998',
            phone_number='9999999998',
            first_name='RM',
            last_name='User',
            email='rm@bop.com',
            user_type='rm',
            is_verified=True
        )
        rm_user.set_password('12345')
        rm_user.save()
        
        # Create TL user
        tl_user = User.objects.create_user(
            username='9999999997',
            phone_number='9999999997',
            first_name='Team',
            last_name='Leader',
            email='tl@bop.com',
            user_type='tl',
            is_verified=True
        )
        tl_user.set_password('12345')
        tl_user.save()
        
        # Create Bhutani Project
        bhutani_project = Project.objects.create(
            name='Bhutani City Center',
            developer='Bhutani Group',
            location='Noida Sector 32',
            property_type='studio',
            description='Premium studio apartments in Noida Sector 32. Fully managed hotel-like suites for investors. Fixed rental income + 21-day annual stay benefit. Located in Bhutani City Center – a lifestyle hub. High ROI real estate in Noida. Passive rental income from a managed property. Ownership in a branded hospitality asset.',
            min_price=10000000,  # 1 Cr
            max_price=15000000,  # 1.5 Cr
            status='active'
        )
        
        # Create Gaur Project
        gaur_project = Project.objects.create(
            name='Gaur Aspire Leisure Park',
            developer='Gaur Group',
            location='Techzone-4 Greater Noida West',
            property_type='apartment',
            description='7 ACRES Plot Size in Techzone-4 Greater Noida West. 6 Tower and One Iconic Tower with 3BHK, 4BHK, 5BHK Luxury Apartments. Sizes- 3BHK+Ser.Room 2293 Sq.Ft. 4BHK+Ser.Room 2783 Sq.Ft. 4BHK+Ser.Room 3769 Sq.Ft. 5BHK+Ser.Room 7262 Sq.Ft. King-Size Residences with unmatched luxury. 2 Wardrobes in all bedrooms. 3-Side Open Views Of The City Skyline. Privacy With No Units Facing Each Other.',
            min_price=8000000,   # 80 Lakh
            max_price=25000000,  # 2.5 Cr
            status='active'
        )
        
        print('✅ Successfully created sample data:')
        print('- CP User: 8882443789 (Direct Login)')
        print('- Admin: 9999999999 (Password: 12345)')
        print('- RM: 9999999998 (Password: 12345)')
        print('- TL: 9999999997 (Password: 12345)')
        print(f'- Projects: {bhutani_project.name}, {gaur_project.name}')

if __name__ == '__main__':
    reset_sample_data()