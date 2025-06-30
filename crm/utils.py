import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def send_whatsapp_message(phone_number, message):
    """
    Send WhatsApp message using API
    This is a placeholder function - implement with your WhatsApp API
    """
    try:
        # Placeholder implementation
        # Replace with actual WhatsApp API integration
        logger.info(f"WhatsApp message sent to {phone_number}: {message[:50]}...")
        return True, "Message sent successfully"
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message to {phone_number}: {e}")
        return False, str(e)

def send_booking_status_update(booking, old_status, new_status):
    """
    Send booking status update notification
    """
    try:
        message = f"""📋 *Booking Status Update*

🆔 Booking ID: *{booking.booking_id}*
🏢 Project: {booking.project.name}
📊 Status: {old_status.title()} → {new_status.title()}
💰 Amount: ₹{booking.total_amount:,.0f}

- United Network Team"""
        
        return send_whatsapp_message(booking.cp.user.phone_number, message)
    except Exception as e:
        logger.error(f"Failed to send booking status update: {e}")
        return False, str(e)

def send_project_collateral_whatsapp(phone_number, project, collateral_title, file_url):
    """
    Send project collateral via WhatsApp
    """
    try:
        message = f"""📋 *{collateral_title}*

🏢 Project: {project.name}
📍 Location: {project.location}
🏗️ Developer: {project.developer}

📎 Download: {file_url}

- United Network Team"""
        
        return send_whatsapp_message(phone_number, message)
    except Exception as e:
        logger.error(f"Failed to send project collateral: {e}")
        return False, str(e)

def send_mlm_notification(sponsor_user, new_vp):
    """
    Send MLM notification to sponsor when new VP is created
    """
    try:
        message = f"""🎉 *New VP Added to Your Network!*

✅ VP Code: *{new_vp.cp_code}*
👤 Name: {new_vp.user.get_full_name()}
🏢 Company: {new_vp.company_name}

💰 You can now earn MLM commissions from their bookings!

- United Network Team"""
        
        return send_whatsapp_message(sponsor_user.phone_number, message)
    except Exception as e:
        logger.error(f"Failed to send MLM notification: {e}")
        return False, str(e)

def send_email_notification(to_email, subject, template_name, context):
    """
    Send email notification using template
    """
    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True, "Email sent successfully"
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False, str(e)

def calculate_commission_amount(total_amount, commission_percentage):
    """
    Calculate commission amount
    """
    return (total_amount * commission_percentage) / 100

def format_currency(amount):
    """
    Format currency for display
    """
    return f"₹{amount:,.0f}"

def get_user_permissions(user):
    """
    Get user permissions based on user type
    """
    permissions = {
        'can_view_all_bookings': False,
        'can_approve_bookings': False,
        'can_view_customer_details': False,
        'can_create_bookings': True,
        'can_view_commission': True,
        'can_create_vps': False,
        'can_access_admin': False,
    }
    
    if user.user_type in ['admin_l1', 'admin_l2', 'admin_l3']:
        permissions.update({
            'can_view_all_bookings': True,
            'can_approve_bookings': True,
            'can_view_customer_details': True,
            'can_access_admin': True,
        })
    elif user.user_type in ['rm', 'team_head', 'team_leader', 'branch']:
        permissions.update({
            'can_view_all_bookings': True,
            'can_view_customer_details': True,
        })
    elif user.user_type in ['cp', 'vp']:
        if hasattr(user, 'channelpartner') and user.channelpartner.can_create_vps:
            permissions['can_create_vps'] = True
    
    return permissions

def validate_phone_number(phone_number):
    """
    Validate phone number format
    """
    import re
    pattern = r'^(\+91|91)?[6-9]\d{9}$'
    return bool(re.match(pattern, phone_number))

def generate_booking_receipt(booking):
    """
    Generate booking receipt data
    """
    return {
        'booking_id': booking.booking_id,
        'project_name': booking.project.name,
        'customer_name': booking.customer_name,
        'total_amount': booking.total_amount,
        'booking_amount': booking.booking_amount,
        'commission_amount': booking.commission_amount,
        'booking_date': booking.created_at,
        'status': booking.get_status_display(),
    }
