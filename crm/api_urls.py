from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'projects', api_views.ProjectViewSet)
router.register(r'bookings', api_views.BookingViewSet)
router.register(r'channel-partners', api_views.ChannelPartnerViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('rest_framework.urls')),
    path('dashboard-stats/', api_views.DashboardStatsAPIView.as_view(), name='dashboard_stats'),
    path('commission-report/', api_views.CommissionReportAPIView.as_view(), name='commission_report'),
]
