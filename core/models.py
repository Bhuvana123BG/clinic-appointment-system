from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import datetime, timedelta

class User(AbstractUser):
    username = models.CharField(max_length=150, blank=True)  
    email = models.EmailField(unique=True)  

    ROLE_CHOICES = (
        ("PATIENT", "Patient"),
        ("DOCTOR", "Doctor"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="PATIENT")
    is_approved = models.BooleanField(default=False)

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
    # availability = models.CharField(max_length=100, blank=True)
    availability = models.JSONField(default=list, blank=True)
    # Example: availability = [0, 2, 4] → 0=Monday, 2=Wednesday, 4=Friday

    # def is_available_on(self, date):
    #     """Check if the doctor is available on the given date."""
    #     weekday = date.weekday()  # 0=Monday, 6=Sunday
    #     return weekday in self.availability

    WEEKDAY_MAP = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday",
    }

    def is_available_on(self, date):
        """Check if doctor is available on a given date."""
        return date.weekday() in self.availability

    def availability_days(self):
        """Return availability as day names."""
        return [self.WEEKDAY_MAP[i] for i in self.availability]

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


    # def has_conflict(self):
    #     appointment_date = self.date.date()  
    #     return Appointment.objects.filter(
    #         patient=self.patient,
    #         doctor=self.doctor,   
    #         date__date=appointment_date,
    #         status__in=["PENDING", "APPROVED"]
    #     ).exclude(id=self.id).exists()


    def has_conflict(self):
        """
        Check for conflicts:
        1. Patient already has an appointment with this doctor on the same day.
        2. Doctor has an appointment within ±30 minutes.
        Returns:
            None -> no conflict
            dict -> details of conflict
        """
        # -------------------------
        # 1) Same-day conflict (patient + doctor)
        # -------------------------
        start_of_day = self.date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        patient_conflict = Appointment.objects.filter(
            doctor=self.doctor,
            patient=self.patient,
            date__gte=start_of_day,
            date__lt=end_of_day,
            status__in=["PENDING", "APPROVED"]
        ).exclude(id=self.id).first()

        if patient_conflict:
            return {
                "type": "PATIENT_CONFLICT",
                "doctor_name": self.doctor.user.username,
                "date": patient_conflict.date
            }

        # -------------------------
        # 2) Doctor overlapping conflict (±30 mins)
        # -------------------------
        start_time = self.date - timedelta(minutes=30)
        end_time = self.date + timedelta(minutes=30)

        doctor_conflict = Appointment.objects.filter(
            doctor=self.doctor,
            date__range=(start_time, end_time),
            status="APPROVED"
        ).exclude(id=self.id).first()

        if doctor_conflict:
            return {
                "type": "DOCTOR_CONFLICT",
                "doctor_name": self.doctor.user.username,
                "date": doctor_conflict.date
            }

        # -------------------------
        # No conflict
        # -------------------------
        return None


    def __str__(self):
        return f"{self.patient.user.username} → Dr. {self.doctor.user.username} ({self.status})"
