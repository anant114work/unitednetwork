from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, ChannelPartner, Booking, Project

class CPRegistrationForm(forms.Form):
    # Personal Information
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+91XXXXXXXXXX'
        })
    )
    
    # Company Information
    company_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter company name'
        })
    )
    rera_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter RERA number'
        })
    )
    pan_number = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter PAN number'
        })
    )
    gst_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter GST number (optional)'
        })
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter complete address'
        })
    )
    
    # Banking Information
    bank_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter bank name'
        })
    )
    account_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter account number'
        })
    )
    ifsc_code = forms.CharField(
        max_length=11,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter IFSC code'
        })
    )

class LoginForm(forms.Form):
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number',
            'required': True
        })
    )

class UserCreateForm(forms.ModelForm):
    """Form for creating users by admin"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'user_type']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91XXXXXXXXXX'}),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter user types based on requesting user's permissions
        if user and user.user_type == 'super_admin':
            # Super admin can create all types including other admins
            self.fields['user_type'].choices = User.USER_TYPES
        elif user and user.user_type in ['admin_l1', 'admin_l2', 'admin_l3']:
            # Regular admins can create RM, TL and other non-admin types
            self.fields['user_type'].choices = [
                ('admin_l2', 'Admin Level 2'),
                ('admin_l3', 'Admin Level 3'),
                ('rm', 'Relationship Manager'),
                ('team_head', 'Team Head'),
                ('team_leader', 'Team Leader'),
                ('branch', 'Branch Manager'),
                ('commission_admin', 'Commission Admin'),
            ]
        else:
            # Default limited choices
            self.fields['user_type'].choices = [
                ('rm', 'Relationship Manager'),
            ]
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data

class AdminCreateForm(forms.ModelForm):
    """Specialized form for creating admin users"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'user_type']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91XXXXXXXXXX'}),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show admin types
        if user and user.user_type == 'super_admin':
            self.fields['user_type'].choices = [
                ('admin_l1', 'Admin Level 1'),
                ('admin_l2', 'Admin Level 2'),
                ('admin_l3', 'Admin Level 3'),
            ]
        elif user and user.user_type in ['admin_l1']:
            self.fields['user_type'].choices = [
                ('admin_l2', 'Admin Level 2'),
                ('admin_l3', 'Admin Level 3'),
            ]
        else:
            self.fields['user_type'].choices = [
                ('admin_l3', 'Admin Level 3'),
            ]
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data

class ProjectForm(forms.ModelForm):
    """Form for creating and editing projects"""
    
    class Meta:
        model = Project
        fields = [
            'name', 'developer', 'property_type', 'location', 'description',
            'price_range', 'min_price', 'max_price', 'status', 'is_featured',
            'image', 'brochure', 'amenities'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project Name'}),
            'developer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Developer Name'}),
            'property_type': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Project Description'}),
            'price_range': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., ₹50L - ₹2Cr'}),
            'min_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Minimum Price'}),
            'max_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Maximum Price'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'brochure': forms.FileInput(attrs={'class': 'form-control'}),
            'amenities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Comma-separated amenities'}),
        }

class RMCreateForm(forms.ModelForm):
    """Specialized form for creating RM and TL users"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    parent_user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select parent user (Team Head/Team Leader)"
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'user_type', 'parent_user']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91XXXXXXXXXX'}),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show RM and TL types
        self.fields['user_type'].choices = [
            ('rm', 'Relationship Manager'),
            ('team_leader', 'Team Leader'),
        ]
        
        # Set parent user options
        if user:
            self.fields['parent_user'].queryset = User.objects.filter(
                user_type__in=['team_head', 'team_leader', 'branch']
            ).order_by('first_name', 'last_name')
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'project', 'cp', 'customer_name', 'customer_phone', 'customer_email',
            'customer_address', 'unit_type', 'unit_number', 'booking_amount',
            'total_amount', 'payment_proof', 'booking_form'
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'cp': forms.Select(attrs={'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91XXXXXXXXXX'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'customer@email.com'}),
            'customer_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'unit_type': forms.Select(attrs={'class': 'form-control'}),
            'unit_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unit Number (if known)'}),
            'booking_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_proof': forms.FileInput(attrs={'class': 'form-control'}),
            'booking_form': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter projects based on user type
        if user:
            if user.user_type in ['cp', 'vp']:
                # CP can only see active projects
                self.fields['project'].queryset = Project.objects.filter(status='active').order_by('name')
                
                # Auto-set CP if user is CP and hide the field
                if hasattr(user, 'channelpartner'):
                    self.fields['cp'].queryset = ChannelPartner.objects.filter(id=user.channelpartner.id)
                    self.fields['cp'].initial = user.channelpartner
                    self.fields['cp'].widget = forms.HiddenInput()
                else:
                    self.fields['cp'].queryset = ChannelPartner.objects.none()
            else:
                # Internal users can see all projects and CPs
                self.fields['project'].queryset = Project.objects.all().order_by('name')
                self.fields['cp'].queryset = ChannelPartner.objects.filter(is_active=True).order_by('cp_code')
        else:
            # Default queryset
            self.fields['project'].queryset = Project.objects.filter(status='active').order_by('name')
            self.fields['cp'].queryset = ChannelPartner.objects.filter(is_active=True).order_by('cp_code')
