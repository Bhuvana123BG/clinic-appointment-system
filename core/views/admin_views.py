from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from core.decorator import login_required
from core.models import User

from django.contrib import messages
from django.contrib.auth import authenticate, login
from core.models import User


def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    pending_doctors = User.objects.filter(role="DOCTOR", is_approved=False)
    return render(request, "auth/admin_dashboard.html", {"pending_doctors": pending_doctors})


@login_required
@user_passes_test(is_admin)
def approve_doctor(request, doctor_id):
    doctor = User.objects.get(id=doctor_id, role="DOCTOR")
    doctor.is_approved = True     
    doctor.is_active = True       
   
    doctor.save()
    
    return redirect("admin_dashboard")


@login_required
@user_passes_test(is_admin)
def reject_doctor(request, doctor_id):
    doctor = User.objects.get(id=doctor_id, role="DOCTOR")
    
    doctor.delete()
    
    return redirect("admin_dashboard")


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