from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter"""
    if value:
        return [item.strip() for item in str(value).split(delimiter)]
    return []

@register.filter
def strip(value):
    """Strip whitespace from string"""
    if value:
        return str(value).strip()
    return value

@register.filter
def currency(value):
    """Format currency"""
    try:
        return f"₹{float(value):,.0f}"
    except (ValueError, TypeError):
        return value

@register.filter
def percentage(value):
    """Format percentage"""
    try:
        return f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return value

@register.filter
def badge_class(status):
    """Return Bootstrap badge class for status"""
    status_classes = {
        'active': 'bg-success',
        'pending': 'bg-warning',
        'approved': 'bg-success',
        'rejected': 'bg-danger',
        'requested': 'bg-info',
        'completed': 'bg-primary',
        'cancelled': 'bg-secondary',
        'draft': 'bg-secondary',
        'under_review': 'bg-warning',
    }
    return status_classes.get(status.lower(), 'bg-secondary')

@register.filter
def user_avatar(user):
    """Generate user avatar initials"""
    if user.first_name and user.last_name:
        return f"{user.first_name[0]}{user.last_name[0]}".upper()
    elif user.first_name:
        return user.first_name[0].upper()
    elif user.username:
        return user.username[0].upper()
    return "U"

@register.filter
def user_type_color(user_type):
    """Return Bootstrap color class for user type"""
    color_map = {
        'super_admin': 'danger',
        'admin_l1': 'warning',
        'admin_l2': 'warning', 
        'admin_l3': 'info',
        'cp': 'success',
        'vp': 'primary',
        'rm': 'secondary',
        'team_head': 'dark',
        'team_leader': 'info',
        'branch': 'warning',
        'commission_admin': 'purple',
    }
    return color_map.get(user_type, 'secondary')
