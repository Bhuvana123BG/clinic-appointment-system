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
# def dashboard_counts(request):
#     if request.user.is_staff:
#         qs = Appointment.objects.all()
#     elif request.user.role == "DOCTOR":
#         qs = Appointment.objects.filter(doctor=request.user.doctorprofile)
#     elif request.user.role == "PATIENT":
#         qs = Appointment.objects.filter(patient=request.user.patientprofile)
#     else:
#         qs = Appointment.objects.none()

#     counts = {
#         "PENDING": qs.filter(status="PENDING").count(),
#         "APPROVED": qs.filter(status="APPROVED").count(),
#         "REJECTED": qs.filter(status="REJECTED").count(),
#     }
#     return JsonResponse(counts)


# ---------- Public ----------
def home(request):
    return render(request, 'home.html')

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

    return render(request, 'patient/make_appointment.html', {
        'q': q,
        'doctors': doctors,
    })


@login_required
def doctor_detail(request, doctor_id):
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')
    doc = get_object_or_404(DoctorProfile.objects.select_related('user'), pk=doctor_id)
    return render(request, 'patient/doctor_detail.html', {'doc': doc})
@login_required
def request_appointment(request, doctor_id):
    # Ensure only patients can request
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')

    doctor = get_object_or_404(DoctorProfile.objects.select_related('user'), pk=doctor_id)

    # 👇 Ensure the patient profile exists (auto-create if missing)
    patient_profile, created = PatientProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        raw_date = request.POST.get("date")
        reason = request.POST.get("reason")

        # Convert string -> datetime
        date = parse_datetime(raw_date)

        if not date:
            messages.error(request, "Invalid date format.")
            return redirect("doctor_detail", doctor_id=doctor.id)

        appointment = Appointment(
            doctor=doctor,
            patient=patient_profile,   # ✅ use patient_profile, not request.user.patient_profile
            date=date,
            reason=reason,
            status="PENDING"
        )

        # ✅ Now inside POST block
        if appointment.has_conflict():
            messages.error(request, "You already have an appointment with this doctor at this time.")
        else:
            appointment.save()
            messages.success(request, "Your appointment request has been submitted!")

        return redirect("doctor_detail", doctor_id=doctor.id)

    return redirect("doctor_detail", doctor_id=doctor.id)





@login_required
def patient_history(request):
    if request.user.role != 'PATIENT':
        return redirect('doctor_dashboard')
    patient = PatientProfile.objects.get(user=request.user)
    approved = Appointment.objects.filter(patient=patient, status='APPROVED').select_related('doctor__user').order_by('-date')
    rejected = Appointment.objects.filter(patient=patient, status='REJECTED').select_related('doctor__user').order_by('-date')
    return render(request, 'patient/history.html', {'approved': approved, 'rejected': rejected})

@login_required
def patient_history_status(request, status):
    """Show only appointments of a specific status (separate page)."""
    status = status.upper()  # convert 'pending' -> 'PENDING'
    appointments = Appointment.objects.filter(
        patient=request.user.patient_profile, status=status
    )
    return render(request, "patient/patient_history_status.html", {
        "appointments": appointments,
        "status": status,
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


# ---------- Doctor Side ----------
@login_required
def doctor_dashboard(request):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    doc = DoctorProfile.objects.get(user=request.user)
    pending = Appointment.objects.filter(doctor=doc, status='PENDING').count()
    approved = Appointment.objects.filter(doctor=doc, status='APPROVED').count()
    rejected = Appointment.objects.filter(doctor=doc, status='REJECTED').count()
    return render(request, 'doctor/dashboard.html', {
        'pending': pending, 'approved': approved, 'rejected': rejected
    })


@login_required
def doctor_requests(request):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    doc = DoctorProfile.objects.get(user=request.user)
    pending = Appointment.objects.filter(doctor=doc, status='PENDING').select_related('patient__user').order_by('date')
    return render(request, 'doctor/requests.html', {'pending': pending})


@login_required
def approve_request(request, appt_id):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
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
    approved = Appointment.objects.filter(doctor=doc, status='APPROVED').select_related('patient__user').order_by('-date')
    rejected = Appointment.objects.filter(doctor=doc, status='REJECTED').select_related('patient__user').order_by('-date')
    return render(request, 'doctor/history.html', {'approved': approved, 'rejected': rejected})


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
