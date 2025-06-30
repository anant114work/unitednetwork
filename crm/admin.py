from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (User, Project, ChannelPartner, Booking, CommissionSlab, 
                    Commission, WhatsAppLog, SystemSettings, ProjectCollateral)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone_number', 'user_type', 'is_verified', 'date_joined')
    list_filter = ('user_type', 'is_verified', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('user_type', 'phone_number', 'is_verified', 'parent_user', 'level', 'sponsor')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {
            'fields': ('user_type', 'phone_number', 'is_verified', 'parent_user', 'level', 'sponsor')
        }),
    )

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('total_cp_count', 'mlm_activated', 'mlm_activation_threshold', 'commission_visibility_internal')
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not SystemSettings.objects.exists()

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'developer', 'location', 'status', 'created_at')
    list_filter = ('status', 'developer', 'property_type', 'created_at')
    search_fields = ('name', 'code', 'developer', 'location')
    ordering = ('-created_at',)
    readonly_fields = ('code', 'created_at', 'updated_at')

@admin.register(ChannelPartner)
class ChannelPartnerAdmin(admin.ModelAdmin):
    list_display = ('cp_code', 'company_name', 'user', 'is_active', 'can_create_vps', 'get_total_vps', 'created_at')
    list_filter = ('is_active', 'can_create_vps', 'created_at')
    search_fields = ('cp_code', 'company_name', 'user__username', 'user__phone_number')
    ordering = ('-created_at',)
    readonly_fields = ('cp_code', 'created_at')

    def get_total_vps(self, obj):
        return obj.get_total_vps()
    get_total_vps.short_description = 'Total VPs'

@admin.register(CommissionSlab)
class CommissionSlabAdmin(admin.ModelAdmin):
    list_display = ('project', 'cp', 'min_amount', 'max_amount', 'commission_percentage', 'is_default')
    list_filter = ('is_default', 'project', 'created_at')
    search_fields = ('project__name', 'cp__cp_code')
    ordering = ('project', 'min_amount')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'project', 'cp', 'customer_name', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'project', 'created_at', 'is_direct_sale')
    search_fields = ('booking_id', 'customer_name', 'customer_phone', 'cp__cp_code', 'project__name')
    ordering = ('-created_at',)
    readonly_fields = ('booking_id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_id', 'project', 'cp', 'rm', 'status')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'customer_phone', 'customer_email', 'customer_address')
        }),
        ('Booking Details', {
            'fields': ('unit_type', 'unit_number', 'booking_amount', 'total_amount')
        }),
        ('Commission', {
            'fields': ('commission_percentage', 'commission_amount', 'commission_paid', 'commission_due', 'level_1_commission', 'level_2_commission')
        }),
        ('Files', {
            'fields': ('payment_proof', 'booking_form')
        }),
        ('Approval', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('booking', 'cp', 'transaction_type', 'amount', 'level', 'created_at')
    list_filter = ('transaction_type', 'level', 'created_at')
    search_fields = ('booking__booking_id', 'cp__cp_code', 'description')
    ordering = ('-created_at',)

@admin.register(WhatsAppLog)
class WhatsAppLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_type', 'phone_number', 'status', 'created_at')
    list_filter = ('message_type', 'status', 'created_at')
    search_fields = ('user__username', 'phone_number', 'message_content')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

@admin.register(ProjectCollateral)
class ProjectCollateralAdmin(admin.ModelAdmin):
    list_display = ('project', 'title', 'collateral_type', 'is_public', 'created_at')
    list_filter = ('collateral_type', 'is_public', 'created_at')
    search_fields = ('project__name', 'title', 'description')
    ordering = ('-created_at',)
