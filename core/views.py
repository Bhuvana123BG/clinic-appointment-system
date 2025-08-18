from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import User, PatientProfile, DoctorProfile, Appointment
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils.timezone import now
from django.utils.dateparse import parse_datetime
from datetime import datetime
import pytz



#timezone
india_tz = pytz.timezone('Asia/Kolkata')

# ---------- Public ----------
def home(request):
    return render(request, 'home.html')


def update_outdated_appointments():

    now = timezone.now().astimezone(india_tz)
    # print("check",now)
    Appointment.objects.filter(Q(status='PENDING') & Q(date__lt=now)).update(status='REJECTED', rejection_message="Time passed, auto-rejected.")

# ---------- Auth (manual forms) ---------- 
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

        # create user
        user = User.objects.create_user(
            email=email,
            password=pwd1,
            role='PATIENT',
            username=full_name  # ✅ store full name in username
        )

        # create an empty patient profile
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


def doctor_login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').lower().strip()
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user and user.role == 'DOCTOR':
            login(request, user)
            return redirect('doctor_dashboard')
        messages.error(request, 'Invalid credentials for doctor login.')
        return redirect('doctor_login')
    return render(request, 'auth/doctor_login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def post_login(request):
    if request.user.role == 'DOCTOR':
        return redirect('doctor_dashboard')
    return redirect('patient_dashboard')


# ---------- Patient Side ----------
@login_required
def patient_dashboard(request):
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')

    #update db
    update_outdated_appointments()

    # quick counts
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
        'now': now.strftime("%Y-%m-%dT%H:%M")
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
    })



@login_required
def request_appointment(request, doctor_id):
    # Ensure only patients can request
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')

    # Get the doctor
    doctor = get_object_or_404(DoctorProfile.objects.select_related('user'), pk=doctor_id)

    # Ensure the patient profile exists
    patient_profile, created = PatientProfile.objects.get_or_create(user=request.user)

    now = timezone.now().astimezone(india_tz)

    if request.method == "POST":
        raw_date = request.POST.get("date")
        reason = request.POST.get("reason")

        # print("raw",raw_date)
        # Convert string -> naive datetime
        date = parse_datetime(raw_date)


        if not date:
            messages.error(request, "Invalid date format.")
            return redirect("doctor_detail", doctor_id=doctor.id)

        date = date.astimezone(india_tz)

        # Check that date is in the future
        if date <= now:
            messages.error(request, "Please select a future date and time.")
            return redirect("doctor_detail", doctor_id=doctor.id)

        # Create appointment instance (not saved yet)
        appointment = Appointment(
            doctor=doctor,
            patient=patient_profile,
            date=date,
            reason=reason,
            status="PENDING"
        )

        # Check conflict: one appointment per doctor per day
        if appointment.has_conflict():
            messages.error(request, "You already have an appointment today with this doctor. Cannot make another request.")
        else:
            appointment.save()
            messages.success(request, "Your appointment request has been submitted!")

        return redirect("doctor_detail", doctor_id=doctor.id)

    # Render the doctor detail page with current datetime for modal
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
    # Fetch all 3 categories
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
    status_upper = status.upper()  # 'pending' -> 'PENDING'

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
        # Update user's display name + email
        request.user.first_name = request.POST.get('name', request.user.first_name)
        new_email = request.POST.get('email', request.user.email).lower().strip()
        if new_email != request.user.email and User.objects.filter(email=new_email).exists():
            messages.error(request, 'Email already in use.')
            return redirect('patient_profile_edit')
        request.user.email = new_email
        request.user.save()

        # Update profile
        profile.phone = request.POST.get('phone', profile.phone)
        profile.address = request.POST.get('address', profile.address)
        profile.save()

        messages.success(request, 'Profile updated.')
        return redirect('patient_profile')

    return render(request, 'patient/profile_edit.html', {'profile': profile})


@login_required
def edit_appointment(request, appointment_id):

    update_outdated_appointments()

    # Ensure only the patient who owns the appointment can edit
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.user.role != 'PATIENT' or appointment.patient.user != request.user:
        messages.error(request, "You are not allowed to edit this appointment.")
        return redirect('patient_history')

    # Only allow editing if the appointment is still pending
    if appointment.status != "PENDING":
        messages.error(request, "You cannot edit this appointment as it is already processed.")
        return redirect('patient_history')

    now =timezone.now().astimezone(india_tz) # timezone-aware current datetime
    
    if request.method == "POST":
        raw_date = request.POST.get("date")
        reason = request.POST.get("reason")

        # Parse datetime-local string (e.g. "2025-08-17T14:30")
        try:
            new_date = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M")
        except (TypeError, ValueError):
            messages.error(request, "Invalid date format.")
            return redirect('edit_appointment', appointment_id=appointment.id)

        # Make it timezone-aware
        new_date = new_date.astimezone(india_tz)

        # Prevent past dates
        if new_date <= now:
            messages.error(request, "Please select a future date and time.")
            return redirect('edit_appointment', appointment_id=appointment.id)

        # Check conflicts with the same doctor (same day)
        conflict_exists = Appointment.objects.filter(
            patient=appointment.patient,
            doctor=appointment.doctor,
            date__date=new_date.date(),
            status__in=["PENDING", "APPROVED"]
        ).exclude(id=appointment.id).exists()

        if conflict_exists:
            messages.error(request, "You already have an appointment with this doctor on the same day.")
            return redirect('edit_appointment', appointment_id=appointment.id)

        # Save updated appointment
        appointment.date = new_date
        appointment.reason = reason
        appointment.save()
        messages.success(request, "Your appointment request has been updated!")
        return redirect('patient_history')

    # --- default value for input ---
    if appointment.date > now:
        default_value = appointment.date.strftime("%Y-%m-%dT%H:%M")
    else:
        default_value = now.strftime("%Y-%m-%dT%H:%M")

    return render(request, "patient/edit_appointment.html", {
        "appointment": appointment,
        "now": now.strftime("%Y-%m-%dT%H:%M"),  # min
        "default_value": default_value           # input value
    })

# ---------- Doctor Side ----------
@login_required
def doctor_dashboard(request):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    
    doc = DoctorProfile.objects.get(user=request.user)

    update_outdated_appointments()
    
    # total_patients = Appointment.objects.filter(doctor=doc).values('patient').distinct().count()
    pending = Appointment.objects.filter(doctor=doc, status='PENDING').count()
    approved = Appointment.objects.filter(doctor=doc, status='APPROVED').count()
    rejected = Appointment.objects.filter(doctor=doc, status='REJECTED').count()
    
    upcoming = Appointment.objects.filter(doctor=doc, status='APPROVED', date__gte=timezone.now()).order_by('date').first()

    return render(request, 'doctor/dashboard.html', {
        # 'total_patients': total_patients,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'upcoming': upcoming,
    })


@login_required
def doctor_requests(request):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    doc = DoctorProfile.objects.get(user=request.user)

    update_outdated_appointments()

    pending = Appointment.objects.filter(doctor=doc, status='PENDING').select_related('patient__user').order_by('-date')
    return render(request, 'doctor/requests.html', {'pending': pending})


@login_required
def approve_request(request, appt_id):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    
    update_outdated_appointments()

    appt = get_object_or_404(Appointment, pk=appt_id, doctor__user=request.user, status='PENDING')
    if request.method == 'POST':
        msg = request.POST.get('doctor_message', '').strip()
        appt.status = 'APPROVED'
        appt.doctor_message = msg
        appt.rejection_message = ''
        appt.save()
        messages.success(request, 'Appointment approved.')
    return redirect('doctor_requests')


@login_required
def reject_request(request, appt_id):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    
    update_outdated_appointments()
    appt = get_object_or_404(Appointment, pk=appt_id, doctor__user=request.user, status='PENDING')
    if request.method == 'POST':
        reason = request.POST.get('rejection_message', '').strip()
        if not reason:
            messages.error(request, 'Please provide a rejection reason.')
            return redirect('doctor_requests')
        appt.status = 'REJECTED'
        appt.rejection_message = reason
        appt.doctor_message = ''
        appt.save()
        messages.info(request, 'Appointment rejected.')
    return redirect('doctor_requests')


@login_required
def doctor_history(request):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    
    doc = DoctorProfile.objects.get(user=request.user)

    update_outdated_appointments()
    
    # Appointments by status
    pending = Appointment.objects.filter(doctor=doc, status='PENDING').select_related('patient__user').order_by('-date')
    approved = Appointment.objects.filter(doctor=doc, status='APPROVED').select_related('patient__user').order_by('-date')
    rejected = Appointment.objects.filter(doctor=doc, status='REJECTED').select_related('patient__user').order_by('-date')
    
    return render(request, 'doctor/history.html', {
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
    })


@login_required
def doctor_history_status(request, status=None):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    
    doc = DoctorProfile.objects.get(user=request.user)

    update_outdated_appointments()

    status_lower = status.lower() if status else None

    if status_lower == 'pending':
        appointments = Appointment.objects.filter(doctor=doc, status='PENDING').select_related('patient__user').order_by('-date')
        title = "Pending Appointments"
    elif status_lower == 'approved':
        appointments = Appointment.objects.filter(doctor=doc, status='APPROVED').select_related('patient__user').order_by('-date')
        title = "Approved Appointments"
    elif status_lower == 'rejected':
        appointments = Appointment.objects.filter(doctor=doc, status='REJECTED').select_related('patient__user').order_by('-date')
        title = "Rejected Appointments"
    else:
        appointments = Appointment.objects.filter(doctor=doc).select_related('patient__user').order_by('-date')
        title = "All Appointments"
     
    return render(request, 'doctor/history_status.html', {
        'appointments': appointments,
        'title': title,
        'status_filter': status_lower,
       
    })


@login_required
def doctor_profile(request):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    profile = DoctorProfile.objects.get(user=request.user)
    return render(request, 'doctor/profile.html', {'profile': profile})


@login_required
def doctor_profile_edit(request):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    profile = DoctorProfile.objects.get(user=request.user)
    if request.method == 'POST':
        # Store doctor display name in user.first_name (simple & already present)
        request.user.first_name = request.POST.get('name', request.user.first_name)
        new_email = request.POST.get('email', request.user.email).lower().strip()
        if new_email != request.user.email and User.objects.filter(email=new_email).exists():
            messages.error(request, 'Email already in use.')
            return redirect('doctor_profile_edit')
        request.user.email = new_email
        request.user.save()

        profile.specialization = request.POST.get('specialization', profile.specialization)
        profile.availability = request.POST.get('availability', profile.availability)
        profile.save()

        messages.success(request, 'Profile updated.')
        return redirect('doctor_profile')

    return render(request, 'doctor/profile_edit.html', {'profile': profile})
