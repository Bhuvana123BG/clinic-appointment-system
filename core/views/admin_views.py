from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from core.decorator import login_required
from core.models import User

from django.contrib import messages
from django.contrib.auth import authenticate, login
from core.models import User,InactiveDoctor,DoctorProfile


def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    pending_doctors = InactiveDoctor.objects.all()
    return render(request, "auth/admin_dashboard.html", {"pending_doctors": pending_doctors})


@login_required
@user_passes_test(is_admin)
def update_doctor_status(request, doctor_id, action):
    
    doctor = get_object_or_404(InactiveDoctor, id=doctor_id)

    if action == "approve":

        user = User(
            email=doctor.email,
            role="DOCTOR",
            username=doctor.username
        )
        # doctor.password here is already hashed
        user.password = doctor.password  
        user.save()

        DoctorProfile.objects.create(user=user,specialization=doctor.specialization,availability=doctor.availability)
    
    doctor.delete()
    
    return redirect('admin_dashboard') 


def admin_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user and user.is_superuser:
            login(request, user)
            return redirect("admin_dashboard")
        else:
            messages.error(request, "Invalid credentials or not an admin")

    return render(request, "auth/admin_login.html")