from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from core.decorator import login_required
from django.utils import timezone
from core.models import User,DoctorProfile, Appointment,InactiveDoctor
from .common_views import update_outdated_appointments
from datetime import timedelta



def doctor_register(request):
    if request.method == "POST":
    
        email = request.POST.get("email")
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("doctor_register")

        name = request.POST.get("name")     
        password = request.POST.get("password")
        specialization = request.POST.get("specialization")
        availability = request.POST.getlist("availability")  # list of strings
        availability = [int(day) for day in availability]  # convert to integers

        doc = InactiveDoctor(
            username=name,
            email=email,
            specialization=specialization,
            availability=availability
        )

        doc.set_password(password)  # hash manually
        doc.save()

        messages.success(request, "Registration successful! Wait for admin approval.")
        return redirect("doctor_login")

    return render(request, "auth/doctor_register.html")

def doctor_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user and user.role == "DOCTOR":
            login(request, user)
            return redirect("doctor_dashboard")
        else:
            messages.error(request, "Invalid credentials")

    return render(request, "auth/doctor_login.html")



# ---------- Doctor Side ----------
@login_required
def doctor_dashboard(request):
    if request.user.role != 'DOCTOR':
        return redirect('patient_dashboard')
    
    doc = DoctorProfile.objects.get(user=request.user)

    update_outdated_appointments()
    pending = Appointment.objects.filter(doctor=doc, status='PENDING').count()
    approved = Appointment.objects.filter(doctor=doc, status='APPROVED').count()
    rejected = Appointment.objects.filter(doctor=doc, status='REJECTED').count()
    
    upcoming = Appointment.objects.filter(doctor=doc, status='APPROVED', date__gte=timezone.now()).order_by('date').first()

    return render(request, 'doctor/dashboard.html', {
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



def reject_conflicting_appointments(approved_appt):
    pending_appointments = Appointment.objects.filter(
        status="PENDING",
        doctor_id=approved_appt.doctor_id,
        date__gte=approved_appt.date - timedelta(minutes=30),
        date__lte=approved_appt.date + timedelta(minutes=30),
    )

    for pending in pending_appointments:
        pending.status = "REJECTED"
        pending.rejection_message = (
            "Rejected due to conflict with another approved appointment."
        )

        pending.save()

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
        reject_conflicting_appointments(appt)
    
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
        request.user.username = request.POST.get('name', request.user.username)
        new_email = request.POST.get('email', request.user.email).lower().strip()
        
        if new_email != request.user.email and User.objects.filter(email=new_email).exists():
            messages.error(request, 'Email already in use.')
            return redirect('doctor_profile_edit')
        
        request.user.email = new_email

        request.user.save()

        profile.specialization = request.POST.get('specialization', profile.specialization)
        selected_days = request.POST.getlist('availability')  # list of strings
        profile.availability = [int(d) for d in selected_days]

        profile.save()

        messages.success(request, 'Profile updated.')
        return redirect('doctor_profile')

    return render(request, 'doctor/profile_edit.html', {'profile': profile})
