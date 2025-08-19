from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    username = models.CharField(max_length=150, blank=True)  
    email = models.EmailField(unique=True)  

    ROLE_CHOICES = (
        ("PATIENT", "Patient"),
        ("DOCTOR", "Doctor"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="PATIENT")

    USERNAME_FIELD = "email"        
    REQUIRED_FIELDS = ["username"]  

    def __str__(self):
        return f"{self.username} ({self.email} - {self.role})"


class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Patient: {self.user.username} ({self.user.email})"


class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="doctor_profile")
    specialization = models.CharField(max_length=100)
    availability = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Dr. {self.user.username} - {self.specialization}"


class Appointment(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    reason = models.TextField()
    date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    doctor_message = models.TextField(blank=True)
    rejection_message = models.TextField(blank=True)



    @property
    def is_outdated(self):
        return self.date < timezone.now() and self.status == "PENDING"


    def has_conflict(self):
        appointment_date = self.date.date()  
        return Appointment.objects.filter(
            patient=self.patient,
            doctor=self.doctor,   
            date__date=appointment_date,
            status__in=["PENDING", "APPROVED"]
        ).exclude(id=self.id).exists()


    def __str__(self):
        return f"{self.patient.user.username} → Dr. {self.doctor.user.username} ({self.status})"
