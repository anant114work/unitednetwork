from .models import Notification

def global_context(request):
    """Global context processor for all templates"""
    context = {}
    
    if request.user.is_authenticated:
        # Get unread notifications count
        context['unread_notifications_count'] = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
        
        # Get recent notifications for dropdown
        context['recent_notifications'] = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
    
    return context
