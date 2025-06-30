from rest_framework import serializers
from .models import Project, Booking, ChannelPartner, Commission

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'code', 'developer', 'property_type', 'location',
            'description', 'price_range', 'min_price', 'max_price',
            'status', 'is_featured', 'amenities', 'image', 'created_at'
        ]

class ChannelPartnerSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = ChannelPartner
        fields = [
            'id', 'cp_code', 'user_name', 'company_name', 'city', 'state',
            'total_bookings', 'total_sales_value', 'is_active', 'created_at'
        ]

class BookingSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    cp_code = serializers.CharField(source='cp.cp_code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_id', 'project_name', 'cp_code', 'unit_type',
            'total_amount', 'commission_amount', 'status', 'status_display',
            'booking_date', 'created_at'
        ]
        
    def to_representation(self, instance):
        """Hide customer details from non-admin users"""
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if request and request.user.user_type not in ['admin_l1', 'admin_l2', 'admin_l3']:
            # Remove customer details for non-admin users
            sensitive_fields = ['customer_name', 'customer_phone', 'customer_email']
            for field in sensitive_fields:
                if field in data:
                    data[field] = "***HIDDEN***"
        
        return data
