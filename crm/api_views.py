from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Project, Booking, ChannelPartner, Commission
from .serializers import ProjectSerializer, BookingSerializer, ChannelPartnerSerializer
from django.db import models

class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for projects
    """
    queryset = Project.objects.filter(status='active')
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Project.objects.filter(status='active')
        location = self.request.query_params.get('location', None)
        developer = self.request.query_params.get('developer', None)
        
        if location:
            queryset = queryset.filter(location__icontains=location)
        if developer:
            queryset = queryset.filter(developer__icontains=developer)
            
        return queryset

class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for bookings
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.user_type in ['admin_l1', 'admin_l2', 'admin_l3']:
            return Booking.objects.all()
        elif user.user_type in ['cp', 'vp']:
            try:
                return Booking.objects.filter(cp__user=user)
            except AttributeError:
                return Booking.objects.none()
        elif user.user_type in ['rm', 'team_head', 'team_leader']:
            return Booking.objects.filter(rm=user)
        else:
            return Booking.objects.none()

class ChannelPartnerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for channel partners
    """
    queryset = ChannelPartner.objects.all()
    serializer_class = ChannelPartnerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.user_type in ['admin_l1', 'admin_l2', 'admin_l3']:
            return ChannelPartner.objects.all()
        elif user.user_type == 'cp':
            return ChannelPartner.objects.filter(user=user)
        else:
            return ChannelPartner.objects.none()

class DashboardStatsAPIView(APIView):
    """
    API endpoint for dashboard statistics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.user_type in ['admin_l1', 'admin_l2', 'admin_l3']:
            # Admin stats
            stats = {
                'total_bookings': Booking.objects.count(),
                'total_sales': Booking.objects.filter(
                    status__in=['approved', 'completed']
                ).aggregate(total=Sum('total_amount'))['total'] or 0,
                'pending_approvals': Booking.objects.filter(status='requested').count(),
                'total_cps': ChannelPartner.objects.filter(is_active=True).count(),
                'total_projects': Project.objects.filter(status='active').count(),
                'monthly_bookings': self.get_monthly_bookings(),
                'top_performers': self.get_top_performers()
            }
        elif user.user_type in ['cp', 'vp']:
            # CP stats
            try:
                cp = user.channelpartner
                bookings = Booking.objects.filter(cp=cp)
                stats = {
                    'total_bookings': bookings.count(),
                    'pending_bookings': bookings.filter(status='requested').count(),
                    'approved_bookings': bookings.filter(status='approved').count(),
                    'total_commission': bookings.aggregate(
                        total=models.Sum('commission_amount')
                    )['total'] or 0,
                    'monthly_performance': self.get_cp_monthly_performance(cp)
                }
            except ChannelPartner.DoesNotExist:
                stats = {'error': 'Channel Partner profile not found'}
        else:
            stats = {'error': 'Access denied'}
            
        return Response(stats)
    
    def get_monthly_bookings(self):
        """Get monthly booking statistics for the last 6 months"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=180)
        
        monthly_data = []
        current_date = start_date
        
        while current_date <= end_date:
            month_start = current_date.replace(day=1)
            if current_date.month == 12:
                month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
            
            bookings_count = Booking.objects.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            ).count()
            
            monthly_data.append({
                'month': current_date.strftime('%b %Y'),
                'bookings': bookings_count
            })
            
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return monthly_data
    
    def get_top_performers(self):
        """Get top performing CPs"""
        return ChannelPartner.objects.annotate(
            total_bookings=Count('booking'),
            total_amount=Sum('booking__total_amount')
        ).filter(total_bookings__gt=0).order_by('-total_amount')[:5].values(
            'cp_code', 'company_name', 'total_bookings', 'total_amount'
        )
    
    def get_cp_monthly_performance(self, cp):
        """Get CP monthly performance for the last 6 months"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=180)
        
        monthly_data = []
        current_date = start_date
        
        while current_date <= end_date:
            month_start = current_date.replace(day=1)
            if current_date.month == 12:
                month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
            
            bookings = Booking.objects.filter(
                cp=cp,
                created_at__gte=month_start,
                created_at__lte=month_end
            )
            
            monthly_data.append({
                'month': current_date.strftime('%b %Y'),
                'bookings': bookings.count(),
                'amount': bookings.aggregate(total=Sum('total_amount'))['total'] or 0
            })
            
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return monthly_data

class CommissionReportAPIView(APIView):
    """
    API endpoint for commission reports
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.user_type not in ['admin_l1', 'admin_l2', 'admin_l3']:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get commission data
        commissions = Commission.objects.select_related('booking', 'cp').all()
        
        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            commissions = commissions.filter(created_at__gte=start_date)
        if end_date:
            commissions = commissions.filter(created_at__lte=end_date)
        
        # Aggregate data
        report_data = {
            'total_commission': commissions.aggregate(total=Sum('amount'))['total'] or 0,
            'commission_by_type': list(commissions.values('transaction_type').annotate(
                total=Sum('amount'),
                count=Count('id')
            )),
            'commission_by_cp': list(commissions.values(
                'cp__cp_code', 'cp__company_name'
            ).annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')[:10])
        }
        
        return Response(report_data)
