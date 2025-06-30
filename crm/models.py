from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid
import random
import string
from datetime import datetime

class User(AbstractUser):
    USER_TYPES = [
        ('super_admin', 'Super Admin'),
        ('admin_l1', 'Admin Level 1'),
        ('admin_l2', 'Admin Level 2'), 
        ('admin_l3', 'Admin Level 3'),
        ('cp', 'Channel Partner'),
        ('vp', 'Vice Partner'),
        ('rm', 'Relationship Manager'),
        ('team_head', 'Team Head'),
        ('team_leader', 'Team Leader'),
        ('branch', 'Branch Manager'),
        ('commission_admin', 'Commission Admin'),  # New user type for commission handling
    ]
    
    phone_number = models.CharField(max_length=15, unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='cp')
    is_verified = models.BooleanField(default=False)
    sponsor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sponsored_users')
    level = models.IntegerField(default=1)
    parent_user = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='team_members')
    
    # Additional fields for views compatibility
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    whatsapp_notifications = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    login_count = models.IntegerField(default=0)
    
    # Team Head specific fields
    can_act_as_cp = models.BooleanField(default=False)  # For direct bookings
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username', 'email']

    def __str__(self):
        return f"{self.get_full_name()} ({self.phone_number}) - {self.get_user_type_display()}"
    
    def get_display_name(self):
        return self.get_full_name() or self.username

class SystemSettings(models.Model):
    """Global system settings and configurations"""
    mlm_activated = models.BooleanField(default=False)
    mlm_activation_threshold = models.IntegerField(default=1000)
    total_cp_count = models.IntegerField(default=0)
    commission_visibility_internal = models.BooleanField(default=False)  # Hide commission from internal team
    default_commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"System Settings (MLM: {'Active' if self.mlm_activated else 'Inactive'})"

class ChannelPartner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cp_code = models.CharField(max_length=20, unique=True, blank=True)
    company_name = models.CharField(max_length=200)
    pan_number = models.CharField(max_length=10, validators=[
        RegexValidator(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', 'Enter a valid PAN number.')
    ])
    
    # Additional fields for forms compatibility
    rera_number = models.CharField(max_length=50, blank=True)
    gst_number = models.CharField(max_length=15, blank=True)
    
    # Banking Information
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=11)
    
    # Address Information
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    
    # Status and Verification
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    can_create_vps = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.cp_code:
            self.cp_code = self.generate_cp_code()
        super().save(*args, **kwargs)

    def generate_cp_code(self):
        prefix = "VP" if self.user.user_type == 'vp' else "CP"
        while True:
            code = prefix + ''.join(random.choices(string.digits, k=6))
            if not ChannelPartner.objects.filter(cp_code=code).exists():
                return code

    def __str__(self):
        return f"{self.cp_code} - {self.user.get_full_name()} ({self.company_name})"

    def get_total_bookings(self):
        """Get total bookings count"""
        return self.bookings.count()

    def get_total_vps(self):
        """Get total VPs count"""
        return ChannelPartner.objects.filter(user__sponsor=self.user, user__user_type='vp').count()
    
    def get_total_sales_value(self):
        """Get total sales value"""
        return self.bookings.aggregate(total=models.Sum('total_amount'))['total'] or 0

class Project(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('sold_out', 'Sold Out'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]
    
    PROPERTY_TYPES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('mixed', 'Mixed Development'),
        ('plots', 'Plots/Land'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, blank=True)
    developer = models.CharField(max_length=200)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES, default='residential')
    location = models.CharField(max_length=200)
    description = models.TextField()
    
    # Pricing
    price_range = models.CharField(max_length=100)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Status and Visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False)
    
    # Media
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    brochure = models.FileField(upload_to='brochures/', blank=True, null=True)
    amenities = models.TextField(blank=True, help_text="Comma-separated list of amenities")
    
    # Performance tracking
    view_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_project_code()
        super().save(*args, **kwargs)

    def generate_project_code(self):
        prefix = "PRJ"
        while True:
            code = prefix + ''.join(random.choices(string.digits, k=6))
            if not Project.objects.filter(code=code).exists():
                return code

    def __str__(self):
        return f"{self.name} - {self.developer} ({self.location})"

class CommissionSlab(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    cp = models.ForeignKey(ChannelPartner, on_delete=models.CASCADE, null=True, blank=True)
    
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    # MLM commission structure
    level_1_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    level_2_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Admin control fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_slabs')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_slabs')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        cp_name = self.cp.cp_code if self.cp else "Default"
        return f"{self.project.name} - {cp_name} - {self.commission_percentage}%"

class Booking(models.Model):
    BOOKING_STATUS = [
        ('draft', 'Draft'),
        ('requested', 'Booking Requested'),
        ('under_review', 'Under Review'),
        ('approved', 'Booking Approved'),
        ('processed', 'Processed'),  # New status
        ('bba_issued', 'BBA Issued'),  # New status
        ('registered', 'Registered'),  # New status
        ('rejected', 'Booking Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    UNIT_TYPES = [
        ('1bhk', '1 BHK'),
        ('2bhk', '2 BHK'),
        ('3bhk', '3 BHK'),
        ('4bhk', '4 BHK'),
        ('villa', 'Villa'),
        ('plot', 'Plot'),
        ('shop', 'Shop'),
        ('office', 'Office'),
    ]
    
    booking_id = models.CharField(max_length=20, unique=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bookings')
    cp = models.ForeignKey(ChannelPartner, on_delete=models.CASCADE, related_name='bookings')
    rm = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_bookings')
    
    # Customer Details
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=15)
    customer_email = models.EmailField(blank=True)
    customer_address = models.TextField(blank=True)
    
    # Unit Details
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPES)
    unit_number = models.CharField(max_length=50, blank=True)
    
    # Financial Details
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    booking_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # MLM commission tracking
    level_1_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    level_2_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Documents
    payment_proof = models.FileField(upload_to='booking_documents/', null=True, blank=True)
    booking_form = models.FileField(upload_to='booking_documents/', null=True, blank=True)
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='requested')
    booking_date = models.DateField(auto_now_add=True)  # Changed to DateField to avoid timezone issues
    
    # Approval
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_bookings')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Flags
    is_direct_sale = models.BooleanField(default=False)  # For Team Head direct bookings
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = self.generate_booking_id()
        
        # Calculate commission due
        self.commission_due = self.commission_amount - self.commission_paid
        
        super().save(*args, **kwargs)

    def generate_booking_id(self):
        prefix = "BK"
        date_str = timezone.now().strftime('%Y%m%d')
        while True:
            code = f"{prefix}{date_str}{random.randint(1000, 9999)}"
            if not Booking.objects.filter(booking_id=code).exists():
                return code

    def __str__(self):
        return f"{self.booking_id} - {self.customer_name} - {self.project.name}"
    
    def calculate_commission(self):
        """Calculate commission based on commission slabs"""
        # Get commission slab for this CP and project
        slab = CommissionSlab.objects.filter(
            project=self.project,
            cp=self.cp,
            min_amount__lte=self.total_amount,
            max_amount__gte=self.total_amount,
            is_active=True
        ).first()
        
        if not slab:
            # Try default slab for project
            slab = CommissionSlab.objects.filter(
                project=self.project,
                cp=None,
                min_amount__lte=self.total_amount,
                max_amount__gte=self.total_amount,
                is_default=True,
                is_active=True
            ).first()
        
        if slab:
            self.commission_percentage = slab.commission_percentage
            self.commission_amount = (self.total_amount * slab.commission_percentage) / 100
            
            # Calculate MLM commissions if applicable
            settings = SystemSettings.objects.first()
            if settings and settings.mlm_activated:
                if self.cp.user.sponsor and slab.level_1_percentage > 0:
                    self.level_1_commission = (self.total_amount * slab.level_1_percentage) / 100
                
                if (self.cp.user.sponsor and self.cp.user.sponsor.sponsor and 
                    slab.level_2_percentage > 0):
                    self.level_2_commission = (self.total_amount * slab.level_2_percentage) / 100
        else:
            # Use system default
            settings = SystemSettings.objects.first()
            if settings:
                self.commission_percentage = settings.default_commission_percentage
                self.commission_amount = (self.total_amount * settings.default_commission_percentage) / 100
        
        # Calculate commission due
        self.commission_due = self.commission_amount - self.commission_paid
        self.save()

class Commission(models.Model):
    TRANSACTION_TYPES = [
        ('booking_commission', 'Booking Commission'),
        ('mlm_level_1', 'MLM Level 1 Commission'),
        ('mlm_level_2', 'MLM Level 2 Commission'),
        ('bonus', 'Bonus'),
        ('adjustment', 'Adjustment'),
        ('debit', 'Debit'),  # New transaction type
        ('payment', 'Payment'),  # New transaction type
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    cp = models.ForeignKey(ChannelPartner, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    level = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    
    # Commission admin tracking
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_commissions')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.booking_id} - {self.cp.cp_code} - {self.transaction_type} - ₹{self.amount}"

class WhatsAppLog(models.Model):
    MESSAGE_TYPES = [
        ('welcome', 'Welcome Message'),
        ('login_notification', 'Login Notification'),
        ('booking_status', 'Booking Status Update'),
        ('commission_update', 'Commission Update'),
        ('project_collateral', 'Project Collateral'),
        ('mlm_notification', 'MLM Notification'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    message_content = models.TextField()
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.message_type} - {self.status}"

class ProjectCollateral(models.Model):
    COLLATERAL_TYPES = [
        ('brochure', 'Brochure'),
        ('floor_plan', 'Floor Plan'),
        ('price_list', 'Price List'),
        ('gallery', 'Photo Gallery'),
        ('video', 'Video'),
        ('other', 'Other'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='collaterals')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    collateral_type = models.CharField(max_length=20, choices=COLLATERAL_TYPES)
    file = models.FileField(upload_to='collaterals/')
    is_public = models.BooleanField(default=False)
    
    # Access Control
    access_level = models.CharField(max_length=20, choices=[
        ('public', 'Public'),
        ('registered', 'Registered Users'),
        ('cp_only', 'Channel Partners Only'),
        ('internal', 'Internal Team Only'),
    ], default='registered')
    
    # Tracking
    download_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.name} - {self.title}"

class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('booking_created', 'Booking Created'),
        ('booking_updated', 'Booking Updated'),
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected'),
        ('cp_registered', 'CP Registered'),
        ('vp_created', 'VP Created'),
        ('project_viewed', 'Project Viewed'),
        ('document_downloaded', 'Document Downloaded'),
        ('commission_modified', 'Commission Modified'),  # New action type
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    description = models.TextField()
    
    # Related Objects
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    cp = models.ForeignKey(ChannelPartner, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Technical Details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.created_at}"

class Notification(models.Model):
    """In-app notifications"""
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('booking', 'Booking Related'),
        ('commission', 'Commission Related'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    
    # Related Objects
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Action
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class LeadSource(models.Model):
    """Lead source tracking"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CustomerFeedback(models.Model):
    """Customer feedback and reviews"""
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    cp = models.ForeignKey(ChannelPartner, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    
    # Ratings
    overall_rating = models.IntegerField(choices=RATING_CHOICES)
    service_rating = models.IntegerField(choices=RATING_CHOICES)
    communication_rating = models.IntegerField(choices=RATING_CHOICES)
    
    # Feedback
    feedback_text = models.TextField()
    suggestions = models.TextField(blank=True)
    
    # Recommendation
    would_recommend = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.customer_name} - {self.overall_rating} stars"
