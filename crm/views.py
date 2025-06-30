from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
import json
import logging
from datetime import datetime, timedelta

from .models import (
    User, Project, ChannelPartner, Booking, CommissionSlab, 
    Commission, SystemSettings, ProjectCollateral, WhatsAppLog,
    ActivityLog, Notification, LeadSource, CustomerFeedback
)
from .forms import CPRegistrationForm, BookingForm, LoginForm, UserCreateForm, ProjectForm, AdminCreateForm, RMCreateForm
from .sms_service import sms_service
from .utils import (
    send_whatsapp_message, send_booking_status_update,
    send_project_collateral_whatsapp, send_mlm_notification
)

logger = logging.getLogger(__name__)

# Utility Functions
def log_activity(user, action_type, description, **kwargs):
    """Log user activity"""
    try:
        ActivityLog.objects.create(
            user=user,
            action_type=action_type,
            description=description,
            booking=kwargs.get('booking'),
            project=kwargs.get('project'),
            cp=kwargs.get('cp'),
            ip_address=kwargs.get('ip_address'),
            user_agent=kwargs.get('user_agent', '')
        )
    except Exception as e:
        logger.error(f"Error logging activity: {e}")

def create_notification(user, title, message, notification_type='info', **kwargs):
    """Create in-app notification"""
    try:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            booking=kwargs.get('booking'),
            project=kwargs.get('project'),
            action_url=kwargs.get('action_url', ''),
            action_text=kwargs.get('action_text', '')
        )
    except Exception as e:
        logger.error(f"Error creating notification: {e}")

def is_admin(user):
    """Check if user is admin"""
    return user.user_type in ['super_admin', 'admin_l1', 'admin_l2', 'admin_l3']

def is_internal_user(user):
    """Check if user is internal team member"""
    return user.user_type in ['super_admin', 'admin_l1', 'admin_l2', 'admin_l3', 'rm', 'team_head', 'team_leader', 'branch']

# Public Views
def home(request):
    """Public homepage with project showcase and search"""
    # Get search parameters
    search = request.GET.get('search', '')
    location = request.GET.get('location', '')
    developer = request.GET.get('developer', '')
    property_type = request.GET.get('property_type', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    
    # Filter projects
    projects = Project.objects.filter(status='active')
    
    if search:
        projects = projects.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(location__icontains=search) |
            Q(developer__icontains=search)
        )
    
    if location:
        projects = projects.filter(location__icontains=location)
    
    if developer:
        projects = projects.filter(developer__icontains=developer)
    
    if property_type:
        projects = projects.filter(property_type=property_type)
    
    if min_price:
        try:
            projects = projects.filter(min_price__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            projects = projects.filter(max_price__lte=float(max_price))
        except ValueError:
            pass
    
    # Order by featured first, then by creation date
    projects = projects.order_by('-is_featured', '-created_at')
    
    # Limit to featured projects for homepage
    featured_projects = projects.filter(is_featured=True)[:6]
    if not featured_projects.exists():
        featured_projects = projects[:6]
    
    # Get unique values for filters
    all_projects = Project.objects.filter(status='active')
    locations = all_projects.values_list('location', flat=True).distinct().order_by('location')
    developers = all_projects.values_list('developer', flat=True).distinct().order_by('developer')
    property_types = Project.PROPERTY_TYPES
    
    # Get system settings for MLM status
    settings, created = SystemSettings.objects.get_or_create(id=1)
    
    # Get statistics
    stats = {
        'total_projects': all_projects.count(),
        'total_cps': ChannelPartner.objects.filter(is_active=True).count(),
        'total_bookings': Booking.objects.filter(status__in=['approved', 'completed']).count(),
        'total_sales_value': Booking.objects.filter(
            status__in=['approved', 'completed']
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
    }
    
    context = {
        'projects': featured_projects,
        'locations': locations,
        'developers': developers,
        'property_types': property_types,
        'mlm_activated': settings.mlm_activated,
        'stats': stats,
        'search_params': {
            'search': search,
            'location': location,
            'developer': developer,
            'property_type': property_type,
            'min_price': min_price,
            'max_price': max_price,
        }
    }
    
    return render(request, 'crm/home.html', context)

def project_detail(request, project_id):
    """Project detail page with role-based access"""
    project = get_object_or_404(Project, id=project_id)
    
    # Increment view count
    project.view_count += 1
    project.save()
    
    # Log activity if user is authenticated
    if request.user.is_authenticated:
        log_activity(
            request.user, 
            'project_viewed', 
            f'Viewed project: {project.name}',
            project=project,
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    context = {'project': project}
    
    if request.user.is_authenticated:
        # Show commission slabs for logged-in users
        if hasattr(request.user, 'channelpartner'):
            # Get CP-specific slabs first
            slabs = CommissionSlab.objects.filter(
                project=project,
                cp=request.user.channelpartner,
                is_active=True
            ).order_by('min_amount')
            
            if not slabs.exists():
                # Fall back to default slabs
                slabs = CommissionSlab.objects.filter(
                    project=project,
                    cp=None,
                    is_default=True,
                    is_active=True
                ).order_by('min_amount')
            
            context['commission_slabs'] = slabs
            
        elif is_internal_user(request.user):
            # Internal users can see all slabs
            context['commission_slabs'] = CommissionSlab.objects.filter(
                project=project,
                is_active=True
            ).order_by('cp__cp_code', 'min_amount')
        
        # Show collaterals based on access level - only those with files
        if is_admin(request.user):
            collaterals = ProjectCollateral.objects.filter(project=project).exclude(file='')
        elif is_internal_user(request.user):
            collaterals = ProjectCollateral.objects.filter(
                project=project,
                access_level__in=['public', 'registered', 'cp_only', 'internal']
            ).exclude(file='')
        elif hasattr(request.user, 'channelpartner'):
            collaterals = ProjectCollateral.objects.filter(
                project=project,
                access_level__in=['public', 'registered', 'cp_only']
            ).exclude(file='')
        else:
            collaterals = ProjectCollateral.objects.filter(
                project=project,
                access_level__in=['public', 'registered']
            ).exclude(file='')
        
        context['collaterals'] = collaterals.order_by('collateral_type', 'title')
        context['show_full_details'] = True
        
        # Get recent bookings for this project (admin only)
        if is_admin(request.user):
            context['recent_bookings'] = Booking.objects.filter(
                project=project
            ).order_by('-created_at')[:5]
    else:
        # Limited info for non-logged users
        context['collaterals'] = ProjectCollateral.objects.filter(
            project=project, 
            access_level='public'
        ).exclude(file='').order_by('collateral_type', 'title')
        context['show_full_details'] = False
    
    # Get similar projects
    similar_projects = Project.objects.filter(
        status='active',
        location=project.location
    ).exclude(id=project.id)[:4]
    context['similar_projects'] = similar_projects
    
    return render(request, 'crm/project_detail.html', context)

def projects_list(request):
    """List all projects with advanced search and filtering"""
    # Get search parameters
    search = request.GET.get('search', '')
    location = request.GET.get('location', '')
    developer = request.GET.get('developer', '')
    property_type = request.GET.get('property_type', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    status = request.GET.get('status', 'active')
    sort_by = request.GET.get('sort_by', '-created_at')
    
    # Base queryset
    projects = Project.objects.all()
    
    # Apply filters
    if status:
        projects = projects.filter(status=status)
    
    if search:
        projects = projects.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(location__icontains=search) |
            Q(developer__icontains=search)
        )
    
    if location:
        projects = projects.filter(location__icontains=location)
    
    if developer:
        projects = projects.filter(developer__icontains=developer)
    
    if property_type:
        projects = projects.filter(property_type=property_type)
    
    if min_price:
        try:
            projects = projects.filter(min_price__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            projects = projects.filter(max_price__lte=float(max_price))
        except ValueError:
            pass
    
    # Apply sorting
    valid_sort_fields = [
        'name', '-name', 'location', '-location', 'developer', '-developer',
        'min_price', '-min_price', 'created_at', '-created_at', 'view_count', '-view_count'
    ]
    if sort_by in valid_sort_fields:
        projects = projects.order_by(sort_by)
    else:
        projects = projects.order_by('-is_featured', '-created_at')
    
    # Pagination
    paginator = Paginator(projects, 12)  # Show 12 projects per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    all_projects = Project.objects.all()
    locations = all_projects.values_list('location', flat=True).distinct().order_by('location')
    developers = all_projects.values_list('developer', flat=True).distinct().order_by('developer')
    
    context = {
        'page_obj': page_obj,
        'projects': page_obj,  # For template compatibility
        'locations': locations,
        'developers': developers,
        'property_types': Project.PROPERTY_TYPES,
        'status_choices': Project.STATUS_CHOICES,
        'search_params': {
            'search': search,
            'location': location,
            'developer': developer,
            'property_type': property_type,
            'min_price': min_price,
            'max_price': max_price,
            'status': status,
            'sort_by': sort_by,
        }
    }
    
    return render(request, 'crm/projects_list.html', context)

# Authentication Views
def login_view(request):
    """OTP-based login system"""
    if request.method == 'POST':
        if 'send_otp' in request.POST:
            # Step 1: Send OTP
            phone_number = request.POST.get('phone_number')
            if phone_number:
                # Direct login for default number
                if phone_number == '8882443789':
                    try:
                        user = User.objects.get(phone_number=phone_number)
                        if not user.is_active:
                            messages.error(request, '❌ Your account has been deactivated.')
                            return render(request, 'crm/login.html')
                        
                        user.last_login_ip = request.META.get('REMOTE_ADDR')
                        user.login_count += 1
                        user.save()
                        
                        login(request, user)
                        log_activity(user, 'login', 'Direct login (default number)', ip_address=request.META.get('REMOTE_ADDR'))
                        messages.success(request, f'✅ Welcome back, {user.get_display_name()}!')
                        return redirect(request.GET.get('next', 'dashboard'))
                    except User.DoesNotExist:
                        messages.error(request, '❌ Phone number not registered!')
                        return render(request, 'crm/login.html')
                
                try:
                    user = User.objects.get(phone_number=phone_number)
                    if not user.is_active:
                        messages.error(request, '❌ Your account has been deactivated.')
                        return render(request, 'crm/login.html')
                    
                    success, otp = sms_service.send_otp(phone_number, "login")
                    if success:
                        messages.success(request, f'✅ OTP sent to {phone_number}')
                        return render(request, 'crm/login.html', {'show_otp': True, 'phone_number': phone_number})
                    else:
                        messages.error(request, '❌ Failed to send OTP. Please try again.')
                except User.DoesNotExist:
                    messages.error(request, '❌ Phone number not registered!')
        
        elif 'verify_otp' in request.POST:
            # Step 2: Verify OTP and login
            phone_number = request.POST.get('phone_number')
            entered_otp = request.POST.get('otp')
            
            if sms_service.verify_otp(phone_number, entered_otp):
                try:
                    user = User.objects.get(phone_number=phone_number)
                    user.last_login_ip = request.META.get('REMOTE_ADDR')
                    user.login_count += 1
                    user.save()
                    
                    login(request, user)
                    
                    log_activity(user, 'login', 'User logged in with OTP', ip_address=request.META.get('REMOTE_ADDR'))
                    
                    messages.success(request, f'✅ Welcome back, {user.get_display_name()}!')
                    return redirect(request.GET.get('next', 'dashboard'))
                except User.DoesNotExist:
                    messages.error(request, '❌ User not found.')
            else:
                messages.error(request, '❌ Invalid or expired OTP.')
                return render(request, 'crm/login.html', {'show_otp': True, 'phone_number': phone_number})
    
    return render(request, 'crm/login.html')

def logout_view(request):
    """Enhanced logout with activity logging"""
    if request.user.is_authenticated:
        # Log activity
        log_activity(
            request.user, 
            'logout', 
            'User logged out',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        user_name = request.user.get_display_name()
        logout(request)
        messages.success(request, f'👋 Goodbye {user_name}! You have been logged out successfully.')
    
    return redirect('home')

def cp_registration(request):
    """OTP-based Channel Partner Registration"""
    if request.method == 'POST':
        if 'send_otp' in request.POST:
            # Step 1: Send OTP for registration
            phone_number = request.POST.get('phone_number')
            if phone_number:
                if User.objects.filter(phone_number=phone_number).exists():
                    messages.error(request, f'❌ Phone number {phone_number} is already registered.')
                    return render(request, 'crm/cp_registration.html')
                
                success, otp = sms_service.send_otp(phone_number, "registration")
                if success:
                    messages.success(request, f'✅ OTP sent to {phone_number}')
                    # Store form data in session
                    request.session['registration_data'] = request.POST.dict()
                    return render(request, 'crm/cp_registration.html', {'show_otp': True, 'phone_number': phone_number})
                else:
                    messages.error(request, '❌ Failed to send OTP. Please try again.')
        
        elif 'verify_otp' in request.POST:
            # Step 2: Verify OTP and complete registration
            phone_number = request.POST.get('phone_number')
            entered_otp = request.POST.get('otp')
            
            if sms_service.verify_otp(phone_number, entered_otp):
                # Get stored registration data
                reg_data = request.session.get('registration_data', {})
                
                try:
                    with transaction.atomic():
                        # Create user
                        user = User.objects.create_user(
                            username=phone_number,
                            phone_number=phone_number,
                            email=reg_data.get('email', ''),
                            first_name=reg_data.get('first_name', ''),
                            last_name=reg_data.get('last_name', ''),
                            user_type='cp',
                            is_verified=True
                        )
                        
                        # Create CP profile
                        cp = ChannelPartner.objects.create(
                            user=user,
                            company_name=reg_data.get('company_name', 'N/A'),
                            pan_number=reg_data.get('pan_number', 'N/A'),
                            bank_name=reg_data.get('bank_name', 'N/A'),
                            account_number=reg_data.get('account_number', 'N/A'),
                            ifsc_code=reg_data.get('ifsc_code', 'N/A'),
                            address=reg_data.get('address', 'N/A')
                        )
                        
                        # Clear session data
                        del request.session['registration_data']
                        
                        log_activity(user, 'cp_registered', f'New CP registered: {cp.cp_code}', cp=cp)
                        
                        messages.success(request, f'🎉 Registration successful! Your CP Code is: {cp.cp_code}')
                        return redirect('login')
                        
                except Exception as e:
                    logger.error(f"Registration error: {e}")
                    messages.error(request, '❌ Registration failed. Please try again.')
            else:
                messages.error(request, '❌ Invalid or expired OTP.')
                return render(request, 'crm/cp_registration.html', {'show_otp': True, 'phone_number': phone_number})
    
    return render(request, 'crm/cp_registration.html')

# Dashboard Views
@login_required
def dashboard(request):
    """Enhanced role-based dashboard with commission visibility restrictions"""
    user = request.user
    context = {'user': user}
    
    # Get system settings
    settings, created = SystemSettings.objects.get_or_create(id=1)
    context['system_settings'] = settings
    
    # Get user notifications
    notifications = Notification.objects.filter(
        user=user, 
        is_read=False
    ).order_by('-created_at')[:5]
    context['notifications'] = notifications
    
    # Determine commission visibility
    show_commission = True
    if user.user_type in ['rm', 'team_head', 'team_leader', 'branch'] and settings.commission_visibility_internal:
        show_commission = False
    
    context['show_commission'] = show_commission
    
    if user.user_type in ['admin_l1', 'admin_l2', 'admin_l3']:
        # Admin dashboard - comprehensive system overview
        today = timezone.now().date()
        this_month = today.replace(day=1)
        last_month = (this_month - timedelta(days=1)).replace(day=1)
        
        # Basic statistics
        total_bookings = Booking.objects.count()
        total_sales = Booking.objects.filter(
            status__in=['approved', 'completed', 'registered', 'processed', 'bba_issued']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        total_commission = Booking.objects.aggregate(
            total=Sum('commission_amount')
        )['total'] or 0
        
        # Monthly comparisons
        this_month_bookings = Booking.objects.filter(created_at__gte=this_month).count()
        last_month_bookings = Booking.objects.filter(
            created_at__gte=last_month,
            created_at__lt=this_month
        ).count()
        
        this_month_sales = Booking.objects.filter(
            created_at__gte=this_month,
            status__in=['approved', 'completed', 'registered', 'processed', 'bba_issued']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        last_month_sales = Booking.objects.filter(
            created_at__gte=last_month,
            created_at__lt=this_month,
            status__in=['approved', 'completed', 'registered', 'processed', 'bba_issued']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate growth percentages
        booking_growth = 0
        if last_month_bookings > 0:
            booking_growth = ((this_month_bookings - last_month_bookings) / last_month_bookings) * 100
        
        sales_growth = 0
        if last_month_sales > 0:
            sales_growth = ((this_month_sales - last_month_sales) / last_month_sales) * 100
        
        # Top performing CPs - Use raw SQL to avoid property conflicts
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT cp.id, cp.cp_code, u.first_name, u.last_name,
                       COUNT(b.id) as booking_count,
                       COALESCE(SUM(b.total_amount), 0) as total_sales,
                       COALESCE(SUM(b.commission_amount), 0) as total_commission
                FROM crm_channelpartner cp
                JOIN crm_user u ON cp.user_id = u.id
                LEFT JOIN crm_booking b ON cp.id = b.cp_id
                WHERE cp.is_active = 1
                GROUP BY cp.id, cp.cp_code, u.first_name, u.last_name
                HAVING booking_count > 0
                ORDER BY total_sales DESC
                LIMIT 5
            """)
            
            top_cps_data = []
            for row in cursor.fetchall():
                top_cps_data.append({
                    'cp_code': row[1],
                    'full_name': f"{row[2]} {row[3]}".strip(),
                    'booking_count': row[4],
                    'total_sales': row[5],
                    'total_commission': row[6] if show_commission else 0
                })
        
        # Recent activities
        recent_activities = ActivityLog.objects.select_related('user').order_by('-created_at')[:10]
        
        context.update({
            'total_bookings': total_bookings,
            'total_sales': total_sales,
            'total_commission': total_commission if show_commission else 0,
            'pending_approvals': Booking.objects.filter(status='requested').count(),
            'total_cps': ChannelPartner.objects.filter(is_active=True).count(),
            'total_projects': Project.objects.filter(status='active').count(),
            'recent_bookings': Booking.objects.select_related('project', 'cp__user').order_by('-created_at')[:5],
            'top_cps_data': top_cps_data,
            'recent_activities': recent_activities,
            'this_month_bookings': this_month_bookings,
            'last_month_bookings': last_month_bookings,
            'booking_growth': booking_growth,
            'this_month_sales': this_month_sales,
            'last_month_sales': last_month_sales,
            'sales_growth': sales_growth,
        })
        return render(request, 'crm/admin_dashboard.html', context)
    
    elif user.user_type in ['cp', 'vp']:
        # CP/VP dashboard - personal performance and MLM data
        try:
            cp = user.channelpartner
            bookings = Booking.objects.filter(cp=cp)
            
            # Performance metrics (always show for CPs)
            total_commission = bookings.aggregate(
                total=Sum('commission_amount')
            )['total'] or 0
            
            commission_paid = bookings.aggregate(
                total=Sum('commission_paid')
            )['total'] or 0
            
            commission_due = total_commission - commission_paid
            
            # Monthly performance
            today = timezone.now().date()
            this_month = today.replace(day=1)
            
            this_month_bookings = bookings.filter(created_at__gte=this_month)
            this_month_sales = this_month_bookings.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            
            # MLM data for CPs
            mlm_data = {}
            if settings.mlm_activated and user.user_type == 'cp':
                vp_list = User.objects.filter(sponsor=user, user_type='vp')
                vp_bookings = Booking.objects.filter(cp__user__in=vp_list)
                vp_commission = vp_bookings.aggregate(
                    total=Sum('level_1_commission')
                )['total'] or 0
            
                mlm_data = {
                    'can_create_vps': cp.can_create_vps,
                    'total_vps': cp.get_total_vps(),
                    'vp_list': vp_list,
                    'vp_bookings_count': vp_bookings.count(),
                    'vp_commission_earned': vp_commission,
                }
        
            # Recent projects
            recent_projects = Project.objects.filter(status='active').order_by('-created_at')[:5]
        
            # Hide customer details from recent bookings
            recent_bookings = bookings.select_related('project').order_by('-created_at')[:5]
        
            context.update({
                'cp': cp,
                'total_bookings': bookings.count(),
                'pending_bookings': bookings.filter(status='requested').count(),
                'approved_bookings': bookings.filter(status='approved').count(),
                'completed_bookings': bookings.filter(status='completed').count(),
                'total_commission': total_commission,
                'commission_paid': commission_paid,
                'commission_due': commission_due,
                'recent_bookings': recent_bookings,
                'this_month_bookings': this_month_bookings.count(),
                'this_month_sales': this_month_sales,
                'show_customer_details': False,  # Hide customer details from CPs
                'mlm_data': mlm_data,
                'recent_projects': recent_projects,
            })
        except ChannelPartner.DoesNotExist:
            messages.error(request, '❌ Channel Partner profile not found!')
            return redirect('home')
    
        return render(request, 'crm/cp_dashboard.html', context)
    
    elif user.user_type in ['rm', 'team_head', 'team_leader', 'branch']:
        # Internal team dashboard - team performance and management
        if user.user_type == 'branch':
            bookings = Booking.objects.all()
            team_members = User.objects.filter(
                user_type__in=['rm', 'team_head', 'team_leader']
            )
        elif user.user_type == 'team_head':
            bookings = Booking.objects.filter(
                Q(rm=user) | Q(rm__parent_user=user)
            )
            team_members = User.objects.filter(parent_user=user)
            
            # Team Head can act as CP for direct sales
            context['can_act_as_cp'] = user.can_act_as_cp
        else:
            bookings = Booking.objects.filter(rm=user)
            team_members = User.objects.filter(parent_user=user)
        
        # Team performance metrics
        team_bookings = bookings.count()
        team_sales = bookings.filter(
            status__in=['approved', 'completed', 'registered', 'processed', 'bba_issued']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Monthly performance
        today = timezone.now().date()
        this_month = today.replace(day=1)
        this_month_bookings = bookings.filter(created_at__gte=this_month).count()
        
        # Commission data (only if visibility is enabled)
        team_commission = 0
        if show_commission:
            team_commission = bookings.aggregate(
                total=Sum('commission_amount')
            )['total'] or 0
        
        context.update({
            'total_bookings': team_bookings,
            'total_sales': team_sales,
            'total_commission': team_commission,
            'pending_bookings': bookings.filter(status='requested').count(),
            'team_members': team_members,
            'recent_bookings': bookings.order_by('-created_at')[:5],
            'this_month_bookings': this_month_bookings,
        })
        return render(request, 'crm/team_dashboard.html', context)
    
    elif user.user_type == 'commission_admin':
        # Commission Admin dashboard - commission management only
        total_commission = Commission.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        pending_commission = Commission.objects.filter(
            status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        paid_commission = Commission.objects.filter(
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        recent_transactions = Commission.objects.select_related(
            'booking', 'cp'
        ).order_by('-created_at')[:10]
        
        context.update({
            'total_commission': total_commission,
            'pending_commission': pending_commission,
            'paid_commission': paid_commission,
            'recent_transactions': recent_transactions,
            'show_commission': True,  # Commission admin always sees commission
        })
        return render(request, 'crm/commission_dashboard.html', context)
    
    else:
        messages.error(request, '❌ Invalid user type!')
        return redirect('home')

# Profile and Settings Views
@login_required
def profile_view(request):
    """User profile view"""
    user = request.user
    
    if request.method == 'POST':
        # Handle profile updates
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        messages.success(request, '✅ Profile updated successfully!')
        return redirect('profile')
    
    context = {'user': user}
    
    if hasattr(user, 'channelpartner'):
        context['cp'] = user.channelpartner
    
    return render(request, 'crm/profile.html', context)

@login_required
def settings_view(request):
    """User settings view"""
    user = request.user
    
    if request.method == 'POST':
        # Handle settings updates
        user.email_notifications = request.POST.get('email_notifications') == 'on'
        user.sms_notifications = request.POST.get('sms_notifications') == 'on'
        user.whatsapp_notifications = request.POST.get('whatsapp_notifications') == 'on'
        user.save()
        
        messages.success(request, '✅ Settings updated successfully!')
        return redirect('settings')
    
    return render(request, 'crm/settings.html', {'user': user})

# Booking Management Views
@login_required
def create_booking(request):
    """Enhanced booking creation with commission calculation and Team Head direct booking support"""
    if request.method == 'POST':
        form = BookingForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            booking = form.save(commit=False)
            
            # Set RM and CP based on user type
            if request.user.user_type == 'cp':
                booking.cp = request.user.channelpartner
                booking.rm = request.user
            elif request.user.user_type == 'vp':
                booking.cp = request.user.channelpartner
                booking.rm = request.user
            elif request.user.user_type == 'team_head' and request.user.can_act_as_cp:
                # Team Head acting as CP for direct bookings
                if not booking.cp:
                    # Create a virtual CP entry for Team Head if needed
                    team_head_cp, created = ChannelPartner.objects.get_or_create(
                        user=request.user,
                        defaults={
                            'company_name': f"{request.user.get_full_name()} - Direct Sales",
                            'pan_number': 'TEAMH0000A',  # Placeholder PAN
                            'bank_name': 'Internal',
                            'account_number': '0000000000',
                            'ifsc_code': 'INTERNAL01',
                            'address': 'Internal Team Head Account'
                        }
                    )
                    booking.cp = team_head_cp
                    booking.is_direct_sale = True
                booking.rm = request.user
            else:
                # Internal user creating booking
                booking.rm = request.user
                if not booking.cp:
                    messages.error(request, '❌ Please select a Channel Partner.')
                    return render(request, 'crm/create_booking.html', {'form': form})
            
            # Calculate commission
            booking.calculate_commission()
            
            # Set booking date with timezone awareness
            booking.booking_date = timezone.now().date()
            
            booking.save()
            
            # Log activity
            log_activity(
                request.user,
                'booking_created',
                f'Created booking {booking.booking_id} for {booking.customer_name}',
                booking=booking,
                project=booking.project,
                cp=booking.cp
            )
            
            # Create notification for CP (if created by internal user and not direct sale)
            if request.user != booking.cp.user and not booking.is_direct_sale:
                create_notification(
                    booking.cp.user,
                    "New Booking Created",
                    f"A new booking {booking.booking_id} has been created for {booking.project.name}",
                    'booking',
                    booking=booking,
                    action_url=f'/booking/{booking.id}/',
                    action_text='View Booking'
                )
            
            # 🚀 NEW: Notify all admins about new booking requests
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_users = User.objects.filter(
                user_type__in=['admin_l1', 'admin_l2', 'admin_l3']
            )
            
            for admin in admin_users:
                create_notification(
                    admin,
                    "📋 New Booking Request",
                    f"New booking {booking.booking_id} from {booking.cp.cp_code} requires approval for {booking.project.name}. Amount: ₹{booking.total_amount:,.0f}",
                    'booking',
                    booking=booking,
                    action_url=f'/booking/{booking.id}/',
                    action_text='Review Booking'
                )
            
            # Send WhatsApp notification (only for non-direct sales)
            if not booking.is_direct_sale:
                notification_message = f"📋 *New Booking Created*\n\n🆔 Booking ID: *{booking.booking_id}*\n🏢 Project: {booking.project.name}\n👤 Customer: {booking.customer_name}\n📊 Status: {booking.get_status_display()}\n💰 Amount: ₹{booking.total_amount:,.0f}\n💵 Commission: ₹{booking.commission_amount:,.0f}\n\n- United Network Team"
                send_whatsapp_message(booking.cp.user.phone_number, notification_message)
            
            messages.success(request, f'✅ Booking {booking.booking_id} created successfully!')
            return redirect('booking_detail', booking_id=booking.id)
    else:
        form = BookingForm(user=request.user)
    
    # Get available projects and CPs for form
    projects = Project.objects.filter(status='active').order_by('name')
    
    if request.user.user_type in ['cp', 'vp']:
        # CP can only create bookings for themselves
        cps = ChannelPartner.objects.filter(user=request.user)
    elif request.user.user_type == 'team_head' and request.user.can_act_as_cp:
        # Team Head can create direct bookings or for other CPs
        cps = ChannelPartner.objects.filter(is_active=True).order_by('cp_code')
    else:
        # Internal users can create bookings for any CP
        cps = ChannelPartner.objects.filter(is_active=True).order_by('cp_code')
    
    context = {
        'form': form,
        'projects': projects,
        'cps': cps,
        'can_create_direct': request.user.user_type == 'team_head' and request.user.can_act_as_cp,
    }
    
    return render(request, 'crm/create_booking.html', context)

@login_required
def booking_detail(request, booking_id):
    """Enhanced booking detail view with comprehensive information"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permissions based on user type
    if request.user.user_type in ['cp', 'vp']:
        # CP can only see their own bookings
        if booking.cp.user != request.user:
            raise PermissionDenied("You can only view your own bookings.")
    elif request.user.user_type in ['rm', 'team_head', 'team_leader']:
        # Internal team members can see bookings they're involved with
        if booking.rm != request.user:
            if request.user.user_type == 'team_head':
                # Team head can see team member bookings
                if booking.rm.parent_user != request.user:
                    raise PermissionDenied("Access denied.")
            elif request.user.user_type == 'team_leader':
                # Team leader can see their team's bookings
                if booking.rm.parent_user != request.user:
                    raise PermissionDenied("Access denied.")
            else:
                raise PermissionDenied("Access denied.")
    # Admin can see all bookings
    
    # Customer details visibility - Only admins can see customer details
    show_customer_details = is_admin(request.user)
    
    # Commission history
    commission_history = Commission.objects.filter(
        booking=booking
    ).order_by('-created_at')
    
    # Activity log for this booking
    activities = ActivityLog.objects.filter(
        booking=booking
    ).order_by('-created_at')
    
    # Related documents/collaterals
    project_collaterals = ProjectCollateral.objects.filter(
        project=booking.project
    ).exclude(file='').order_by('collateral_type', 'title')
    
    context = {
        'booking': booking,
        'show_customer_details': show_customer_details,
        'commission_history': commission_history,
        'activities': activities,
        'project_collaterals': project_collaterals,
        'can_approve': is_admin(request.user) and booking.status == 'requested',
        'can_edit': request.user == booking.rm or is_admin(request.user),
    }
    
    return render(request, 'crm/booking_detail.html', context)

@login_required
@require_http_methods(["POST"])
def approve_booking(request, booking_id):
    """Approve booking with enhanced workflow"""
    if not is_admin(request.user):
        raise PermissionDenied("Only admins can approve bookings.")
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    if booking.status != 'requested':
        messages.error(request, '❌ Only requested bookings can be approved.')
        return redirect('booking_detail', booking_id=booking.id)
    
    old_status = booking.status
    booking.status = 'approved'
    booking.approved_by = request.user
    booking.approved_at = timezone.now()
    booking.save()
    
    # Log activity
    log_activity(
        request.user,
        'booking_approved',
        f'Approved booking {booking.booking_id}',
        booking=booking,
        cp=booking.cp
    )
    
    # 🚀 Enhanced: Create notification for CP about approval
    create_notification(
        booking.cp.user,
        "✅ Booking Approved!",
        f"Great news! Your booking {booking.booking_id} for {booking.project.name} has been approved by {request.user.get_display_name()}. Amount: ₹{booking.total_amount:,.0f}",
        'success',
        booking=booking,
        action_url=f'/booking/{booking.id}/',
        action_text='View Booking'
    )
    
    # Also notify RM if different from admin
    if booking.rm and booking.rm != request.user:
        create_notification(
            booking.rm,
            "📋 Booking Approved",
            f"Booking {booking.booking_id} from CP {booking.cp.cp_code} has been approved",
            'info',
            booking=booking,
            action_url=f'/booking/{booking.id}/',
            action_text='View Booking'
        )
    
    # Send WhatsApp status update
    send_booking_status_update(booking, old_status, 'approved')
    
    messages.success(request, f'✅ Booking {booking.booking_id} approved successfully!')
    return redirect('booking_detail', booking_id=booking.id)

@login_required
@require_http_methods(["POST"])
def reject_booking(request, booking_id):
    """Reject booking with reason"""
    if not is_admin(request.user):
        raise PermissionDenied("Only admins can reject bookings.")
    
    booking = get_object_or_404(Booking, id=booking_id)
    rejection_reason = request.POST.get('rejection_reason', '')
    
    if booking.status != 'requested':
        messages.error(request, '❌ Only requested bookings can be rejected.')
        return redirect('booking_detail', booking_id=booking.id)
    
    if not rejection_reason:
        messages.error(request, '❌ Please provide a rejection reason.')
        return redirect('booking_detail', booking_id=booking.id)
    
    old_status = booking.status
    booking.status = 'rejected'
    booking.rejection_reason = rejection_reason
    booking.approved_by = request.user
    booking.approved_at = timezone.now()
    booking.save()
    
    # Log activity
    log_activity(
        request.user,
        'booking_rejected',
        f'Rejected booking {booking.booking_id}: {rejection_reason}',
        booking=booking,
        cp=booking.cp
    )
    
    # 🚀 Enhanced: Create notification for CP about rejection
    create_notification(
        booking.cp.user,
        "❌ Booking Rejected",
        f"Your booking {booking.booking_id} for {booking.project.name} has been rejected by {request.user.get_display_name()}. Reason: {rejection_reason}",
        'error',
        booking=booking,
        action_url=f'/booking/{booking.id}/',
        action_text='View Booking'
    )
    
    # Also notify RM if different from admin
    if booking.rm and booking.rm != request.user:
        create_notification(
            booking.rm,
            "📋 Booking Rejected",
            f"Booking {booking.booking_id} from CP {booking.cp.cp_code} has been rejected",
            'warning',
            booking=booking,
            action_url=f'/booking/{booking.id}/',
            action_text='View Booking'
        )
    
    # Send WhatsApp status update
    rejection_message = f"❌ *Booking Rejected*\n\n🆔 Booking ID: *{booking.booking_id}*\n🏢 Project: {booking.project.name}\n📊 Status: Rejected\n📝 Reason: {rejection_reason}\n\n- United Network Team"
    send_whatsapp_message(booking.cp.user.phone_number, rejection_message)
    
    messages.success(request, f'✅ Booking {booking.booking_id} rejected.')
    return redirect('booking_detail', booking_id=booking.id)

@login_required
def bookings_list(request):
    """Enhanced bookings list with advanced filtering and search"""
    user = request.user
    
    # Base queryset based on user type
    if is_admin(user):
        bookings = Booking.objects.all()
    elif user.user_type in ['cp', 'vp']:
        bookings = Booking.objects.filter(cp__user=user)
    elif user.user_type == 'branch':
        bookings = Booking.objects.all()
    elif user.user_type == 'team_head':
        bookings = Booking.objects.filter(
            Q(rm=user) | Q(rm__parent_user=user)
        )
    else:
        bookings = Booking.objects.filter(rm=user)
    
    # Apply filters
    status = request.GET.get('status')
    project_id = request.GET.get('project')
    cp_id = request.GET.get('cp')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')
    
    if status:
        bookings = bookings.filter(status=status)
    
    if project_id:
        bookings = bookings.filter(project_id=project_id)
    
    if cp_id and is_internal_user(user):
        bookings = bookings.filter(cp_id=cp_id)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            bookings = bookings.filter(created_at__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            bookings = bookings.filter(created_at__lte=to_date)
        except ValueError:
            pass
    
    if search:
        bookings = bookings.filter(
            Q(booking_id__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search) |
            Q(project__name__icontains=search)
        )
    
    # Ordering
    order_by = request.GET.get('order_by', '-created_at')
    valid_order_fields = [
        'created_at', '-created_at', 'booking_id', '-booking_id',
        'customer_name', '-customer_name', 'total_amount', '-total_amount',
        'status', '-status'
    ]
    if order_by in valid_order_fields:
        bookings = bookings.order_by(order_by)
    else:
        bookings = bookings.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(bookings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    projects = Project.objects.filter(status='active').order_by('name')
    cps = ChannelPartner.objects.filter(is_active=True).order_by('cp_code')
    
    # Hide customer details from non-admin users
    show_customer_details = is_admin(user)
    
    context = {
        'page_obj': page_obj,
        'bookings': page_obj,  # For template compatibility
        'status_choices': Booking.BOOKING_STATUS,
        'projects': projects,
        'cps': cps,
        'show_customer_details': show_customer_details,
        'search_params': {
            'status': status,
            'project': project_id,
            'cp': cp_id,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
            'order_by': order_by,
        }
    }
    
    return render(request, 'crm/bookings_list.html', context)

# Continue with remaining view functions...
@login_required
def leaderboard(request):
    """Enhanced leaderboard with comprehensive performance metrics"""
    # Only internal teams can access leaderboard
    if request.user.user_type in ['cp', 'vp']:
        messages.error(request, '❌ Access denied! Leaderboard is for internal teams only.')
        return redirect('dashboard')
    
    if not is_internal_user(request.user):
        raise PermissionDenied("Access denied!")
    
    # Get filter parameters
    period = request.GET.get('period', 'all_time')
    metric = request.GET.get('metric', 'total_amount')
    
    # Use raw SQL to avoid property conflicts
    from django.db import connection
    
    # Build time filter for SQL
    time_filter = ""
    if period == 'this_month':
        today = timezone.now().date()
        start_date = today.replace(day=1)
        time_filter = f"AND b.created_at >= '{start_date}'"
    elif period == 'last_month':
        today = timezone.now().date()
        last_month = (today.replace(day=1) - timedelta(days=1))
        start_date = last_month.replace(day=1)
        end_date = today.replace(day=1)
        time_filter = f"AND b.created_at >= '{start_date}' AND b.created_at < '{end_date}'"
    elif period == 'this_year':
        today = timezone.now().date()
        start_date = today.replace(month=1, day=1)
        time_filter = f"AND b.created_at >= '{start_date}'"
    
    # Build user role filter
    role_filter = ""
    if request.user.user_type == 'team_head':
        team_rms = User.objects.filter(parent_user=request.user, user_type='rm')
        rm_ids = list(team_rms.values_list('id', flat=True)) + [request.user.id]
        if rm_ids:
            role_filter = f"AND b.rm_id IN ({','.join(map(str, rm_ids))})"
    elif request.user.user_type == 'team_leader':
        team_rms = User.objects.filter(parent_user=request.user, user_type='rm')
        rm_ids = list(team_rms.values_list('id', flat=True))
        if rm_ids:
            role_filter = f"AND b.rm_id IN ({','.join(map(str, rm_ids))})"
    elif request.user.user_type == 'rm':
        role_filter = f"AND b.rm_id = {request.user.id}"
    
    # Order by clause
    order_clause = "total_sales DESC"
    if metric == 'total_bookings':
        order_clause = "booking_count DESC"
    elif metric == 'commission':
        order_clause = "total_commission DESC"
    
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT cp.id, cp.cp_code, u.first_name, u.last_name, cp.company_name,
                   COUNT(b.id) as booking_count,
                   COALESCE(SUM(b.total_amount), 0) as total_sales,
                   COALESCE(SUM(b.commission_amount), 0) as total_commission,
                   COALESCE(AVG(b.total_amount), 0) as avg_booking_value
            FROM crm_channelpartner cp
            JOIN crm_user u ON cp.user_id = u.id
            LEFT JOIN crm_booking b ON cp.id = b.cp_id {time_filter} {role_filter}
            WHERE cp.is_active = 1
            GROUP BY cp.id, cp.cp_code, u.first_name, u.last_name, cp.company_name
            HAVING booking_count > 0
            ORDER BY {order_clause}
            LIMIT 20
        """)
        
        top_cps_data = []
        for row in cursor.fetchall():
            top_cps_data.append({
                'cp_code': row[1],
                'full_name': f"{row[2]} {row[3]}".strip(),
                'company_name': row[4],
                'total_bookings': row[5],
                'total_amount': row[6],
                'total_commission': row[7],
                'avg_booking_value': row[8]
            })
    
    # Get additional statistics
    total_cps = ChannelPartner.objects.filter(is_active=True).count()
    active_cps = len(top_cps_data)
    
    context = {
        'top_cps': top_cps_data,
        'user_role': request.user.get_user_type_display(),
        'period': period,
        'metric': metric,
        'total_cps': total_cps,
        'active_cps': active_cps,
        'period_choices': [
            ('all_time', 'All Time'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('this_year', 'This Year'),
        ],
        'metric_choices': [
            ('total_amount', 'Total Sales Value'),
            ('total_bookings', 'Total Bookings'),
            ('commission', 'Total Commission'),
        ]
    }
    
    return render(request, 'crm/leaderboard.html', context)

# MLM and VP Management
@login_required
def create_vp(request):
    """Create VP (Sub-CP) under current CP - Enhanced MLM feature"""
    if request.user.user_type != 'cp':
        messages.error(request, '❌ Only Channel Partners can create VPs!')
        return redirect('dashboard')
    
    try:
        cp = request.user.channelpartner
        settings = SystemSettings.objects.get(id=1)
        
        if not settings.mlm_activated:
            messages.error(request, f'❌ MLM feature is not yet activated. Available after {settings.mlm_activation_threshold} CP registrations.')
            return redirect('dashboard')
        
        if not cp.can_create_vps:
            messages.error(request, '❌ You are not authorized to create VPs yet.')
            return redirect('dashboard')
    except (ChannelPartner.DoesNotExist, SystemSettings.DoesNotExist):
        messages.error(request, '❌ Error accessing MLM features.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CPRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Check if user already exists
                    phone_number = form.cleaned_data['phone_number']
                    email = form.cleaned_data['email']
                    
                    if User.objects.filter(phone_number=phone_number).exists():
                        messages.error(request, f'❌ Phone number {phone_number} is already registered.')
                        return render(request, 'crm/create_vp.html', {'form': form})
                    
                    if User.objects.filter(email=email).exists():
                        messages.error(request, f'❌ Email {email} is already registered.')
                        return render(request, 'crm/create_vp.html', {'form': form})
                    
                    # Create VP user
                    vp_user = User.objects.create_user(
                        username=phone_number,
                        phone_number=phone_number,
                        email=email,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        user_type='vp',
                        sponsor=request.user,
                        level=request.user.level + 1,
                        is_verified=True
                    )
                    
                    # Create VP profile
                    vp = ChannelPartner.objects.create(
                        user=vp_user,
                        company_name=form.cleaned_data['company_name'],
                        rera_number=form.cleaned_data.get('rera_number', ''),
                        pan_number=form.cleaned_data['pan_number'],
                        gst_number=form.cleaned_data.get('gst_number', ''),
                        bank_name=form.cleaned_data['bank_name'],
                        account_number=form.cleaned_data['account_number'],
                        ifsc_code=form.cleaned_data['ifsc_code'],
                        address=form.cleaned_data['address']
                    )
                    
                    # Log activity
                    log_activity(
                        request.user,
                        'vp_created',
                        f'Created VP {vp.cp_code} under {cp.cp_code}',
                        cp=vp
                    )
                    
                    # Send welcome message to VP
                    welcome_message = f"🎉 *Welcome to United Network as VP!*\n\n✅ Your VP Code: *{vp.cp_code}*\n👤 Sponsor: {cp.cp_code} ({request.user.get_full_name()})\n🏢 Company: {vp.company_name}\n📱 You can now login using your phone number.\n\n📋 Next Steps:\n• Complete your profile\n• Explore available projects\n• Start creating bookings\n\n- United Network Team"
                    send_whatsapp_message(vp_user.phone_number, welcome_message)
                    
                    # Send MLM notification to sponsor
                    send_mlm_notification(request.user, vp)
                    
                    # Create notifications
                    create_notification(
                        vp_user,
                        "Welcome to United Network!",
                        f"Your VP registration is successful. Your VP Code is {vp.cp_code}",
                        'success',
                        action_url='/dashboard/',
                        action_text='Go to Dashboard'
                    )
                    
                    create_notification(
                        request.user,
                        "New VP Created!",
                        f"VP {vp.cp_code} has been successfully created under your network",
                        'success',
                        action_url='/dashboard/',
                        action_text='View Dashboard'
                    )
                    
                    messages.success(request, f'🎉 VP created successfully! VP Code: {vp.cp_code}')
                    return redirect('dashboard')
                    
            except IntegrityError as e:
                messages.error(request, '❌ Phone number or email already exists.')
            except Exception as e:
                logger.error(f"VP creation error: {e}")
                messages.error(request, '❌ VP creation failed. Please try again.')
    else:
        form = CPRegistrationForm()
    
    context = {
        'form': form,
        'cp': cp,
        'settings': settings,
    }
    
    return render(request, 'crm/create_vp.html', context)

# Project and Collateral Management
@login_required
def download_brochure_whatsapp(request, project_id):
    """Send project brochure via WhatsApp with tracking"""
    project = get_object_or_404(Project, id=project_id)
    
    if not project.brochure:
        messages.error(request, '❌ Brochure not available for this project.')
        return redirect('project_detail', project_id=project_id)
    
    # Log activity
    log_activity(
        request.user,
        'document_downloaded',
        f'Downloaded brochure for {project.name}',
        project=project
    )
    
    # Send brochure via WhatsApp
    brochure_url = request.build_absolute_uri(project.brochure.url)
    success, result = send_project_collateral_whatsapp(
        request.user.phone_number,
        project,
        'Project Brochure',
        brochure_url
    )
    
    if success:
        messages.success(request, '✅ Brochure sent to your WhatsApp successfully!')
        
        # Log WhatsApp message
        WhatsAppLog.objects.create(
            user=request.user,
            message_type='project_collateral',
            message_content=f'Brochure for {project.name}',
            phone_number=request.user.phone_number,
            status='sent'
        )
    else:
        messages.error(request, f'❌ Failed to send brochure: {result}')
    
    return redirect('project_detail', project_id=project_id)

@login_required
def send_collateral_whatsapp(request, project_id, collateral_id):
    """Send project collateral via WhatsApp with enhanced tracking"""
    project = get_object_or_404(Project, id=project_id)
    collateral = get_object_or_404(ProjectCollateral, id=collateral_id, project=project)
    
    # Check if file exists
    if not collateral.file:
        messages.error(request, f'❌ File not found for {collateral.title}.')
        return redirect('project_detail', project_id=project_id)
    
    # Check access permissions
    if collateral.access_level == 'internal' and not is_internal_user(request.user):
        raise PermissionDenied("Access denied to this collateral.")
    
    if collateral.access_level == 'cp_only' and request.user.user_type not in ['cp', 'vp'] and not is_internal_user(request.user):
        raise PermissionDenied("Access denied to this collateral.")
    
    # Increment download count
    collateral.download_count += 1
    collateral.save()
    
    # Log activity
    log_activity(
        request.user,
        'document_downloaded',
        f'Downloaded {collateral.title} for {project.name}',
        project=project
    )
    
    try:
        # Send collateral via WhatsApp
        file_url = request.build_absolute_uri(collateral.file.url)
        success, result = send_project_collateral_whatsapp(
            request.user.phone_number,
            project,
            collateral.title,
            file_url
        )
        
        if success:
            messages.success(request, f'✅ {collateral.title} sent to your WhatsApp successfully!')
            
            # Log WhatsApp message
            WhatsAppLog.objects.create(
                user=request.user,
                message_type='project_collateral',
                message_content=f'{collateral.title} for {project.name}',
                phone_number=request.user.phone_number,
                status='sent'
            )
        else:
            messages.error(request, f'❌ Failed to send {collateral.title}: {result}')
    except Exception as e:
        messages.error(request, f'❌ Error accessing file: {str(e)}')
    
    return redirect('project_detail', project_id=project_id)

# API and AJAX Views
@login_required
def get_commission_slabs(request, project_id):
    """Get commission slabs for a project (AJAX)"""
    project = get_object_or_404(Project, id=project_id)
    
    # Get slabs based on user type
    if hasattr(request.user, 'channelpartner'):
        slabs = CommissionSlab.objects.filter(
            project=project,
            cp=request.user.channelpartner,
            is_active=True
        )
        if not slabs.exists():
            slabs = CommissionSlab.objects.filter(
                project=project,
                cp=None,
                is_default=True,
                is_active=True
            )
    else:
        slabs = CommissionSlab.objects.filter(
            project=project,
            is_default=True,
            is_active=True
        )
    
    slab_data = []
    for slab in slabs:
        slab_data.append({
            'min_amount': float(slab.min_amount),
            'max_amount': float(slab.max_amount),
            'commission_percentage': float(slab.commission_percentage),
            'level_1_percentage': float(slab.level_1_percentage),
            'level_2_percentage': float(slab.level_2_percentage),
        })
    
    return JsonResponse({'slabs': slab_data})

@login_required
def calculate_commission(request):
    """Calculate commission for given amount and project (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')
            amount = float(data.get('amount', 0))
            
            project = get_object_or_404(Project, id=project_id)
            
            # Get appropriate commission slab
            if hasattr(request.user, 'channelpartner'):
                slab = CommissionSlab.objects.filter(
                    project=project,
                    cp=request.user.channelpartner,
                    min_amount__lte=amount,
                    max_amount__gte=amount,
                    is_active=True
                ).first()
                
                if not slab:
                    slab = CommissionSlab.objects.filter(
                        project=project,
                        cp=None,
                        min_amount__lte=amount,
                        max_amount__gte=amount,
                        is_default=True,
                        is_active=True
                    ).first()
            else:
                slab = CommissionSlab.objects.filter(
                    project=project,
                    cp=None,
                    min_amount__lte=amount,
                    max_amount__gte=amount,
                    is_default=True,
                    is_active=True
                ).first()
            
            if slab:
                commission_amount = (amount * slab.commission_percentage) / 100
                level_1_commission = (amount * slab.level_1_percentage) / 100
                level_2_commission = (amount * slab.level_2_percentage) / 100
                
                return JsonResponse({
                    'success': True,
                    'commission_percentage': float(slab.commission_percentage),
                    'commission_amount': commission_amount,
                    'level_1_commission': level_1_commission,
                    'level_2_commission': level_2_commission,
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No commission slab found for this amount'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read (AJAX)"""
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id, 
            user=request.user
        )
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_notifications(request):
    """Get user notifications (AJAX)"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    notification_data = []
    for notification in notifications:
        notification_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'action_url': notification.action_url,
            'action_text': notification.action_text,
        })
    
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'notifications': notification_data,
        'unread_count': unread_count
    })

# Debug and Utility Views
@login_required
def check_users(request):
    """Debug view to check existing users (Admin only)"""
    if not is_admin(request.user):
        raise PermissionDenied("Admin access required")
    
    users = User.objects.all().values(
        'id', 'username', 'phone_number', 'email', 'user_type', 
        'is_active', 'is_verified', 'created_at'
    ).order_by('-created_at')
    
    return JsonResponse({'users': list(users)})

@login_required
def system_stats(request):
    """Get system statistics (Admin only)"""
    if not is_admin(request.user):
        raise PermissionDenied("Admin access required")
    
    stats = {
        'total_users': User.objects.count(),
        'total_cps': ChannelPartner.objects.filter(is_active=True).count(),
        'total_projects': Project.objects.count(),
        'total_bookings': Booking.objects.count(),
        'total_sales': Booking.objects.filter(
            status__in=['approved', 'completed', 'registered']
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        'total_commission': Booking.objects.aggregate(
            total=Sum('commission_amount')
        )['total'] or 0,
        'pending_approvals': Booking.objects.filter(status='requested').count(),
        'active_projects': Project.objects.filter(status='active').count(),
    }
    
    return JsonResponse(stats)

# Error Handlers
def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Custom 500 error handler"""
    return render(request, 'errors/500.html', status=500)

def handler403(request, exception):
    """Custom 403 error handler"""
    return render(request, 'errors/403.html', status=403)
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

# Notification Views
@login_required
def notifications_view(request):
    """View all notifications for the user"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Mark all as read when viewing notifications page
    if request.GET.get('mark_read') != 'false':
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
    
    context = {
        'page_obj': page_obj,
        'notifications': page_obj,
    }
    
    return render(request, 'crm/notifications.html', context)

@login_required
def notification_count(request):
    """Get unread notification count (AJAX)"""
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({'count': count})

@login_required
def mark_notifications_read(request):
    """Mark all notifications as read (AJAX)"""
    try:
        updated_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return JsonResponse({'success': True, 'updated_count': updated_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def my_bookings(request):
    """CP's personal bookings view"""
    if request.user.user_type not in ['cp', 'vp']:
        messages.error(request, '❌ Access denied! This page is for Channel Partners only.')
        return redirect('dashboard')
    
    try:
        cp = request.user.channelpartner
        bookings = Booking.objects.filter(cp=cp).order_by('-created_at')
        
        # Apply filters
        status = request.GET.get('status')
        project_id = request.GET.get('project')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if status:
            bookings = bookings.filter(status=status)
        
        if project_id:
            bookings = bookings.filter(project_id=project_id)
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                bookings = bookings.filter(created_at__gte=from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                bookings = bookings.filter(created_at__lte=to_date)
            except ValueError:
                pass
        
        # Pagination
        paginator = Paginator(bookings, 15)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get filter options
        projects = Project.objects.filter(status='active').order_by('name')
        
        # Calculate summary stats
        total_bookings = bookings.count()
        total_amount = bookings.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        total_commission = bookings.aggregate(
            total=Sum('commission_amount')
        )['total'] or 0
        
        context = {
            'page_obj': page_obj,
            'bookings': page_obj,
            'cp': cp,
            'projects': projects,
            'status_choices': Booking.BOOKING_STATUS,
            'total_bookings': total_bookings,
            'total_amount': total_amount,
            'total_commission': total_commission,
            'search_params': {
                'status': status,
                'project': project_id,
                'date_from': date_from,
                'date_to': date_to,
            }
        }
        
        return render(request, 'crm/my_bookings.html', context)
        
    except ChannelPartner.DoesNotExist:
        messages.error(request, '❌ Channel Partner profile not found!')
        return redirect('dashboard')

def test_navbar(request):
    """Debug view to verify navbar visibility and troubleshoot issues"""
    return render(request, 'crm/debug_navbar.html')

def simple_test(request):
    """Simple standalone test"""
    return render(request, 'crm/simple_test.html')

# User Management Views
@login_required
def user_management(request):
    """User management page - Admin only"""
    if not is_admin(request.user):
        raise PermissionDenied("Only admins can access user management.")
    
    # Get search parameters
    search = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')
    is_active = request.GET.get('is_active', '')
    
    # Base queryset
    users = User.objects.all()
    
    # Apply filters
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search) |
            Q(phone_number__icontains=search) |
            Q(email__icontains=search)
        )
    
    if user_type:
        users = users.filter(user_type=user_type)
    
    if is_active:
        users = users.filter(is_active=is_active == 'true')
    
    # Ordering
    users = users.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'users': page_obj,
        'user_types': User.USER_TYPES,
        'search_params': {
            'search': search,
            'user_type': user_type,
            'is_active': is_active,
        }
    }
    
    return render(request, 'crm/user_management.html', context)

@login_required
def create_user(request):
    """Create new user - Admin only"""
    if not is_admin(request.user):
        raise PermissionDenied("Only admins can create users.")
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Check if user already exists
                    phone_number = form.cleaned_data['phone_number']
                    email = form.cleaned_data['email']
                    
                    if User.objects.filter(phone_number=phone_number).exists():
                        messages.error(request, f'❌ Phone number {phone_number} is already registered.')
                        return render(request, 'crm/create_user.html', {'form': form})
                    
                    if User.objects.filter(email=email).exists():
                        messages.error(request, f'❌ Email {email} is already registered.')
                        return render(request, 'crm/create_user.html', {'form': form})
                    
                    # Create user
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        phone_number=phone_number,
                        email=email,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        user_type=form.cleaned_data['user_type'],
                        password=form.cleaned_data['password'],
                        is_verified=True
                    )
                    
                    # Log activity
                    log_activity(
                        request.user,
                        'user_created',
                        f'Created new user: {user.username} ({user.get_user_type_display()})',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    # Create notification for new user
                    create_notification(
                        user,
                        "Welcome to United Network!",
                        f"Your account has been created by {request.user.get_display_name()}. You can now login using your phone number.",
                        'success',
                        action_url='/dashboard/',
                        action_text='Go to Dashboard'
                    )
                    
                    # Send welcome message
                    welcome_message = f"🎉 *Welcome to United Network!*\n\n👤 Account created for: {user.get_full_name()}\n📱 Phone: {phone_number}\n👔 Role: {user.get_user_type_display()}\n\n📱 You can now login using your phone number.\n\n- United Network Team"
                    send_whatsapp_message(phone_number, welcome_message)
                    
                    messages.success(request, f'✅ User {user.get_full_name()} created successfully!')
                    return redirect('user_management')
                    
            except Exception as e:
                logger.error(f"User creation error: {e}")
                messages.error(request, '❌ User creation failed. Please try again.')
    else:
        form = UserCreateForm(user=request.user)
    
    return render(request, 'crm/create_user.html', {'form': form})

@login_required
def edit_user(request, user_id):
    """Edit user - Admin only"""
    if not is_admin(request.user):
        raise PermissionDenied("Only admins can edit users.")
    
    user_to_edit = get_object_or_404(User, id=user_id)
    
    # Prevent editing super admin unless you are super admin
    if user_to_edit.user_type == 'super_admin' and request.user.user_type != 'super_admin':
        raise PermissionDenied("Only super admin can edit super admin accounts.")
    
    if request.method == 'POST':
        # Handle basic user info updates
        user_to_edit.first_name = request.POST.get('first_name', user_to_edit.first_name)
        user_to_edit.last_name = request.POST.get('last_name', user_to_edit.last_name)
        user_to_edit.email = request.POST.get('email', user_to_edit.email)
        user_to_edit.is_active = request.POST.get('is_active') == 'on'
        
        # Only super admin can change user types
        if request.user.user_type == 'super_admin':
            new_user_type = request.POST.get('user_type')
            if new_user_type and new_user_type != user_to_edit.user_type:
                user_to_edit.user_type = new_user_type
        
        user_to_edit.save()
        
        # Log activity
        log_activity(
            request.user,
            'user_updated',
            f'Updated user: {user_to_edit.username}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f'✅ User {user_to_edit.get_full_name()} updated successfully!')
        return redirect('user_management')
    
    context = {
        'user_to_edit': user_to_edit,
        'user_types': User.USER_TYPES,
        'can_change_type': request.user.user_type == 'super_admin'
    }
    
    return render(request, 'crm/edit_user.html', context)

# Project Management Views
@login_required
def project_management(request):
    """Project management page - Admin, RM, and Team Head only"""
    user = request.user
    
    # Check permissions: Admin, RM, and Team Head can access
    if not (is_admin(user) or user.user_type in ['rm', 'team_head']):
        raise PermissionDenied("Access denied. Only admins, RMs, and Team Heads can manage projects.")
    
    # Get search parameters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    property_type = request.GET.get('property_type', '')
    developer = request.GET.get('developer', '')
    
    # Base queryset
    projects = Project.objects.all()
    
    # Apply filters
    if search:
        projects = projects.filter(
            Q(name__icontains=search) |
            Q(developer__icontains=search) |
            Q(location__icontains=search) |
            Q(description__icontains=search)
        )
    
    if status:
        projects = projects.filter(status=status)
    
    if property_type:
        projects = projects.filter(property_type=property_type)
    
    if developer:
        projects = projects.filter(developer__icontains=developer)
    
    # Ordering
    projects = projects.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(projects, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    developers = Project.objects.values_list('developer', flat=True).distinct().order_by('developer')
    
    context = {
        'page_obj': page_obj,
        'projects': page_obj,
        'status_choices': Project.STATUS_CHOICES,
        'property_types': Project.PROPERTY_TYPES,
        'developers': developers,
        'search_params': {
            'search': search,
            'status': status,
            'property_type': property_type,
            'developer': developer,
        },
        'can_create': True,  # All users with access can create projects
        'can_edit': True,    # All users with access can edit projects
    }
    
    return render(request, 'crm/project_management.html', context)

@login_required
def create_project(request):
    """Create new project - Admin, RM, and Team Head only"""
    user = request.user
    
    # Check permissions
    if not (is_admin(user) or user.user_type in ['rm', 'team_head']):
        raise PermissionDenied("Access denied. Only admins, RMs, and Team Heads can create projects.")
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                project = form.save()
                
                # Log activity
                log_activity(
                    request.user,
                    'project_created',
                    f'Created new project: {project.name}',
                    project=project,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                # Create notifications for all admins
                admin_users = User.objects.filter(
                    user_type__in=['super_admin', 'admin_l1', 'admin_l2', 'admin_l3']
                ).exclude(id=request.user.id)
                
                for admin in admin_users:
                    create_notification(
                        admin,
                        "🏢 New Project Created",
                        f"Project '{project.name}' has been created by {request.user.get_display_name()} in {project.location}",
                        'info',
                        action_url=f'/project/{project.id}/',
                        action_text='View Project'
                    )
                
                messages.success(request, f'✅ Project "{project.name}" created successfully!')
                return redirect('project_management')
                
            except Exception as e:
                logger.error(f"Project creation error: {e}")
                messages.error(request, '❌ Project creation failed. Please try again.')
    else:
        form = ProjectForm()
    
    return render(request, 'crm/create_project.html', {'form': form})

@login_required
def edit_project(request, project_id):
    """Edit project - Admin, RM, and Team Head only"""
    user = request.user
    
    # Check permissions
    if not (is_admin(user) or user.user_type in ['rm', 'team_head']):
        raise PermissionDenied("Access denied. Only admins, RMs, and Team Heads can edit projects.")
    
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            try:
                project = form.save()
                
                # Log activity
                log_activity(
                    request.user,
                    'project_updated',
                    f'Updated project: {project.name}',
                    project=project,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'✅ Project "{project.name}" updated successfully!')
                return redirect('project_management')
                
            except Exception as e:
                logger.error(f"Project update error: {e}")
                messages.error(request, '❌ Project update failed. Please try again.')
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
        'is_edit': True
    }
    
    return render(request, 'crm/edit_project.html', context)

# Admin Management Views
@login_required
def create_admin(request):
    """Create new admin user - Super Admin and Admin L1 only"""
    if not (request.user.user_type in ['super_admin', 'admin_l1']):
        raise PermissionDenied("Only super admin and admin L1 can create admin users.")
    
    if request.method == 'POST':
        form = AdminCreateForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Check if user already exists
                    phone_number = form.cleaned_data['phone_number']
                    email = form.cleaned_data['email']
                    
                    if User.objects.filter(phone_number=phone_number).exists():
                        messages.error(request, f'❌ Phone number {phone_number} is already registered.')
                        return render(request, 'crm/create_admin.html', {'form': form})
                    
                    if User.objects.filter(email=email).exists():
                        messages.error(request, f'❌ Email {email} is already registered.')
                        return render(request, 'crm/create_admin.html', {'form': form})
                    
                    # Create admin user
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        phone_number=phone_number,
                        email=email,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        user_type=form.cleaned_data['user_type'],
                        password=form.cleaned_data['password'],
                        is_verified=True,
                        is_staff=True  # Admin users should have staff access
                    )
                    
                    # Log activity
                    log_activity(
                        request.user,
                        'admin_created',
                        f'Created new admin: {user.username} ({user.get_user_type_display()})',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    # Create notification for new admin
                    create_notification(
                        user,
                        "Welcome to United Network Admin Panel!",
                        f"Your admin account has been created by {request.user.get_display_name()}. You now have {user.get_user_type_display()} access.",
                        'success',
                        action_url='/dashboard/',
                        action_text='Go to Dashboard'
                    )
                    
                    # Send welcome message
                    welcome_message = f"🎉 *Welcome to United Network Admin Panel!*\n\n👤 Admin account created for: {user.get_full_name()}\n📱 Phone: {phone_number}\n👔 Role: {user.get_user_type_display()}\n\n🔐 You now have administrative access to the system.\n📱 Login using your phone number.\n\n- United Network Team"
                    send_whatsapp_message(phone_number, welcome_message)
                    
                    messages.success(request, f'✅ Admin {user.get_full_name()} created successfully!')
                    return redirect('user_management')
                    
            except Exception as e:
                logger.error(f"Admin creation error: {e}")
                messages.error(request, '❌ Admin creation failed. Please try again.')
    else:
        form = AdminCreateForm(user=request.user)
    
    return render(request, 'crm/create_admin.html', {'form': form})

@login_required
def create_rm(request):
    """Create new RM/TL user - Admin only"""
    if not is_admin(request.user):
        raise PermissionDenied("Only admins can create RM/TL users.")
    
    if request.method == 'POST':
        form = RMCreateForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Check if user already exists
                    phone_number = form.cleaned_data['phone_number']
                    email = form.cleaned_data['email']
                    
                    if User.objects.filter(phone_number=phone_number).exists():
                        messages.error(request, f'❌ Phone number {phone_number} is already registered.')
                        return render(request, 'crm/create_rm.html', {'form': form})
                    
                    if User.objects.filter(email=email).exists():
                        messages.error(request, f'❌ Email {email} is already registered.')
                        return render(request, 'crm/create_rm.html', {'form': form})
                    
                    # Create RM/TL user
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        phone_number=phone_number,
                        email=email,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        user_type=form.cleaned_data['user_type'],
                        password=form.cleaned_data['password'],
                        parent_user=form.cleaned_data.get('parent_user'),
                        is_verified=True
                    )
                    
                    # Log activity
                    log_activity(
                        request.user,
                        'rm_created',
                        f'Created new {user.get_user_type_display()}: {user.username}',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    # Create notification for new user
                    create_notification(
                        user,
                        "Welcome to United Network Team!",
                        f"Your {user.get_user_type_display()} account has been created by {request.user.get_display_name()}.",
                        'success',
                        action_url='/dashboard/',
                        action_text='Go to Dashboard'
                    )
                    
                    # Send welcome message
                    welcome_message = f"🎉 *Welcome to United Network Team!*\n\n👤 Account created for: {user.get_full_name()}\n📱 Phone: {phone_number}\n👔 Role: {user.get_user_type_display()}\n\n📱 You can now login using your phone number.\n\n- United Network Team"
                    send_whatsapp_message(phone_number, welcome_message)
                    
                    messages.success(request, f'✅ {user.get_user_type_display()} {user.get_full_name()} created successfully!')
                    return redirect('user_management')
                    
            except Exception as e:
                logger.error(f"RM/TL creation error: {e}")
                messages.error(request, '❌ User creation failed. Please try again.')
    else:
        form = RMCreateForm(user=request.user)
    
    return render(request, 'crm/create_rm.html', {'form': form})

@login_required
def admin_management(request):
    """Admin management dashboard - Super Admin and Admin L1 only"""
    if not (request.user.user_type in ['super_admin', 'admin_l1']):
        raise PermissionDenied("Access denied.")
    
    # Get admin users
    admin_users = User.objects.filter(
        user_type__in=['super_admin', 'admin_l1', 'admin_l2', 'admin_l3']
    ).order_by('-created_at')
    
    # Get RM/TL users
    rm_users = User.objects.filter(
        user_type__in=['rm', 'team_head', 'team_leader', 'branch']
    ).order_by('-created_at')
    
    context = {
        'admin_users': admin_users,
        'rm_users': rm_users,
        'can_create_admin': request.user.user_type in ['super_admin', 'admin_l1'],
        'can_create_rm': True,
    }
    
    return render(request, 'crm/admin_management.html', context)
