from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from core.decorator import login_required
from django.utils import timezone
from core.models import User, PatientProfile, DoctorProfile, Appointment
from django.db.models import Q, Count
from django.utils.timezone import now
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
from .common_views import update_outdated_appointments
import pytz

india_tz = pytz.timezone('Asia/Kolkata')

def patient_register(request):
    if request.method == 'POST':
        full_name = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').lower().strip()
        pwd1 = request.POST.get('password1')
        pwd2 = request.POST.get('password2')

        if pwd1 != pwd2:
            messages.error(request, 'Passwords do not match.')
            return redirect('patient_register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('patient_register')
        
        user = User.objects.create_user(
            email=email,
            password=pwd1,
            role='PATIENT',
            username=full_name 
        )
       
        PatientProfile.objects.create(user=user)

        messages.success(request, 'Account created. Please log in.')
        return redirect('patient_login')

    return render(request, 'auth/patient_register.html')


def patient_login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').lower().strip()
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user and user.role == 'PATIENT':
            login(request, user)
            return redirect('patient_dashboard')
        
        messages.error(request, 'Invalid credentials for patient login.')
        return redirect('patient_login')
    return render(request, 'auth/patient_login.html')


# ---------- Patient Side ----------
@login_required
def patient_dashboard(request):
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')
    
    update_outdated_appointments()
    
    profile = PatientProfile.objects.get(user=request.user)
    counts = Appointment.objects.filter(patient=profile).values('status').annotate(c=Count('id'))
    by_status = {row['status']: row['c'] for row in counts}

    upcoming = Appointment.objects.filter(
        patient=profile,

        status="APPROVED",
        date__gte=now()
    ).order_by("date").first()
    
    return render(request, 'patient/dashboard.html', {'by_status': by_status,"upcoming": upcoming})


@login_required
def make_appointment(request):
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')
        

    q = request.GET.get('q', '').strip()
    doctors = DoctorProfile.objects.select_related('user').all()
    
    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q) | Q(specialization__icontains=q)
        )
    
    now=timezone.localtime(timezone.now())
    
    return render(request, 'patient/make_appointment.html', {
        'q': q,
        'doctors': doctors,
        'now': now.strftime("%Y-%m-%dT%H:%M"),
        
    })

@login_required
def doctor_detail(request, doctor_id):
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')

    doctor = get_object_or_404(DoctorProfile.objects.select_related('user'), pk=doctor_id)

    approved_appointments = Appointment.objects.filter(
        doctor=doctor, status='APPROVED'
    ).select_related('patient__user').order_by('-date')

    
    now=timezone.now().astimezone(india_tz)

    return render(request, 'patient/doctor_detail.html', {
        'doctor': doctor,
        "now": now.strftime("%Y-%m-%dT%H:%M"),
        'approved_appointments': approved_appointments,
        "available_days": doctor.availability_days()
    })


@login_required
def request_appointment(request, doctor_id):

    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')

    doctor = get_object_or_404(DoctorProfile.objects.select_related('user'), pk=doctor_id)

   
    patient_profile, created = PatientProfile.objects.get_or_create(user=request.user)

    now = timezone.now().astimezone(india_tz)

    if request.method == "POST":
        raw_date = request.POST.get("date")
        reason = request.POST.get("reason")
        date = parse_datetime(raw_date)

        if not date:
            messages.error(request, "Invalid date format.")
            return redirect("doctor_detail", doctor_id=doctor.id)

        date = date.astimezone(india_tz)
        if date <= now:
            messages.error(request, "Please select a future date and time.")
            return redirect("doctor_detail", doctor_id=doctor.id)


          # --- Check if doctor is available on this day ---
        if not doctor.is_available_on(date):
            next_available = None
            
            for i in range(1, 8):  # next 7 days
                check_date = date + timedelta(days=i)
                
                if doctor.is_available_on(check_date):
                    next_available = check_date.strftime("%A, %d %b %Y")
                    break
           
            messages.error(
                request,
                f"Doctor is not available on {date.strftime('%A')}. "
                f"Next available day is {next_available}."
            )
            
            return redirect("doctor_detail", doctor_id=doctor.id)
       
        appointment = Appointment(
            doctor=doctor,
            patient=patient_profile,
            date=date,
            reason=reason,
            status="PENDING"
        )

        
        # --- Check conflicts ---
        conflict = appointment.has_conflict()

        if conflict:
            if conflict["type"] == "PATIENT_CONFLICT":
                messages.error(
                    request,
                    f"❌ You already have an appointment with Dr. {conflict['doctor_name']} on "
                    f"{conflict['date'].strftime('%d %b %Y')}."
                )
            elif conflict["type"] == "DOCTOR_CONFLICT":
                messages.error(
                    request,
                    f"❌ Dr. {conflict['doctor_name']} already has an appointment at this time. "
                    f"Please choose another slot."
                )
        else:
            appointment.save()
            messages.success(request, "✅ Your appointment request has been submitted!")


        return redirect("doctor_detail", doctor_id=doctor.id)

    return render(request, "doctor_details.html", {
        "doctor": doctor,
        "now": now
    })

@login_required
def patient_history(request):
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')

    patient = PatientProfile.objects.get(user=request.user)
    
    update_outdated_appointments()

    approved = Appointment.objects.filter(
        patient=patient, status='APPROVED'
    ).select_related('doctor__user').order_by('-date')

    rejected = Appointment.objects.filter(
        patient=patient, status='REJECTED'
    ).select_related('doctor__user').order_by('-date')

    pending = Appointment.objects.filter(
        patient=patient, status='PENDING'
    ).select_related('doctor__user').order_by('-date')

    return render(request, 'patient/history.html', {
        'approved': approved,
        'rejected': rejected,
        'pending': pending,
    })


@login_required
def patient_history_status(request, status):
    patient = request.user.patient_profile

    update_outdated_appointments()

    """Show only appointments of a specific status for the logged-in patient."""
    status_upper = status.upper() 
    # Ensure valid status
    if status_upper not in ["PENDING", "APPROVED", "REJECTED"]:
        status_upper = "PENDING"

    appointments = Appointment.objects.filter(
        patient=request.user.patient_profile,
        status=status_upper
    ).select_related('doctor__user').order_by("-date")

    return render(request, "patient/patient_history_status.html", {
        "appointments": appointments,
        "status": status_upper,
    })


@login_required
def patient_profile(request):
   
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')
    
    profile = PatientProfile.objects.get(user=request.user)
    return render(request, 'patient/profile.html', {'profile': profile})


@login_required
def patient_profile_edit(request):
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')
    profile = PatientProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        request.user.username = request.POST.get('name', request.user.username)
        new_email = request.POST.get('email', request.user.email).lower().strip()
        
        if new_email != request.user.email and User.objects.filter(email=new_email).exists():
            messages.error(request, 'Email already in use.')
            return redirect('patient_profile_edit')
        request.user.email = new_email
       
        request.user.save()

        profile.phone = request.POST.get('phone', profile.phone)
        profile.address = request.POST.get('address', profile.address)
        
        profile.save()

        messages.success(request, 'Profile updated.')
        return redirect('patient_profile')

    return render(request, 'patient/profile_edit.html', {'profile': profile})


@login_required
def edit_appointment(request, appointment_id):

    update_outdated_appointments()
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.user.role != 'PATIENT' or appointment.patient.user != request.user:
        messages.error(request, "You are not allowed to edit this appointment.")
        return redirect('patient_history')
    
    if appointment.status != "PENDING":
        messages.error(request, "You cannot edit this appointment as it is already processed.")
        return redirect('patient_history')

    now =timezone.now().astimezone(india_tz)
    
    if request.method == "POST":
        raw_date = request.POST.get("date")
        reason = request.POST.get("reason")
        
        try:
            new_date = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M")
        except (TypeError, ValueError):
            messages.error(request, "Invalid date format.")
            return redirect('edit_appointment', appointment_id=appointment.id)
        
        new_date = new_date.astimezone(india_tz)
        
        if new_date <= now:
            messages.error(request, "Please select a future date and time.")
            return redirect('edit_appointment', appointment_id=appointment.id)

        conflict_exists = Appointment.objects.filter(
            patient=appointment.patient,
            doctor=appointment.doctor,
            date__date=new_date.date(),
            status__in=["PENDING", "APPROVED"]
        ).exclude(id=appointment.id).exists()

        if conflict_exists:
            messages.error(request, "You already have an appointment with this doctor on the same day.")
            return redirect('edit_appointment', appointment_id=appointment.id)
        
        appointment.date = new_date
        appointment.reason = reason
        appointment.save()
        messages.success(request, "Your appointment request has been updated!")
        return redirect('patient_history')

    if appointment.date > now:
        default_value = appointment.date.strftime("%Y-%m-%dT%H:%M")
   
    else:
        default_value = now.strftime("%Y-%m-%dT%H:%M")

    return render(request, "patient/edit_appointment.html", {
        "appointment": appointment,
        "now": now.strftime("%Y-%m-%dT%H:%M"), 
        "default_value": default_value           
    })