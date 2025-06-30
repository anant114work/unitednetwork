from django.urls import path
from . import views

urlpatterns = [
    # Public URLs
    path('', views.home, name='home'),
    path('projects/', views.projects_list, name='projects_list'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.cp_registration, name='cp_registration'),
    
    # Dashboard URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Booking URLs
    path('bookings/', views.bookings_list, name='bookings_list'),
    path('booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('booking/create/', views.create_booking, name='create_booking'),
    path('booking/<int:booking_id>/approve/', views.approve_booking, name='approve_booking'),
    path('booking/<int:booking_id>/reject/', views.reject_booking, name='reject_booking'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    
    # MLM URLs
    path('create-vp/', views.create_vp, name='create_vp'),
    
    # Performance URLs
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # Profile and Settings URLs
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    
    # Notification URLs
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/count/', views.notification_count, name='notification_count'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    
    # Document URLs
    path('project/<int:project_id>/brochure/', views.download_brochure_whatsapp, name='download_brochure_whatsapp'),
    path('project/<int:project_id>/collateral/<int:collateral_id>/', views.send_collateral_whatsapp, name='send_collateral_whatsapp'),
    
    # AJAX URLs
    path('api/project/<int:project_id>/commission-slabs/', views.get_commission_slabs, name='get_commission_slabs'),
    path('api/calculate-commission/', views.calculate_commission, name='calculate_commission'),
    path('api/notification/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    
    # User Management URLs (Admin only)
    path('manage/users/', views.user_management, name='user_management'),
    path('manage/users/create/', views.create_user, name='create_user'),
    path('manage/users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    
    # Admin Management URLs
    path('manage/admins/', views.admin_management, name='admin_management'),
    path('manage/create-admin/', views.create_admin, name='create_admin'),
    path('manage/create-rm/', views.create_rm, name='create_rm'),
    
    # Project Management URLs (Admin, RM, Team Head)
    path('manage/projects/', views.project_management, name='project_management'),
    path('manage/projects/create/', views.create_project, name='create_project'),
    path('manage/projects/edit/<int:project_id>/', views.edit_project, name='edit_project'),
    
    # Debug URLs (Admin only)
    path('debug/users/', views.check_users, name='check_users'),
    path('debug/stats/', views.system_stats, name='system_stats'),
    path('test-navbar/', views.test_navbar, name='test_navbar'),
    path('debug-navbar/', views.test_navbar, name='debug_navbar'),
    path('simple-test/', views.simple_test, name='simple_test'),
]
