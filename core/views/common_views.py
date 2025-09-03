from django.shortcuts import render, redirect
from django.contrib.auth import logout
from core.decorator import login_required
from django.utils import timezone
from core.models import Appointment
from django.db.models import Q
from django.utils import timezone
from core.models import Appointment
from django.db.models import Q
import pytz

def home(request):
    return render(request, 'home.html')

india_tz = pytz.timezone('Asia/Kolkata')
def update_outdated_appointments():

    now = timezone.now().astimezone(india_tz)
    Appointment.objects.filter(Q(status='PENDING') & Q(date__lt=now)).update(status='REJECTED', rejection_message="Time passed, auto-rejected.")



def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def post_login(request):
    if request.user.role == 'DOCTOR':
        return redirect('doctor_dashboard')
    return redirect('patient_dashboard')