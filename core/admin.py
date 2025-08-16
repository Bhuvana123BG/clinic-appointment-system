from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PatientProfile, DoctorProfile, Appointment


# ------------------------
# Custom User Admin
# ------------------------
class CustomUserAdmin(BaseUserAdmin):
    # fields visible when editing a user
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("username", "role")}),
    )

    # fields visible when adding a new user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2", "role"),
        }),
    )

    list_display = ("email", "username", "role", "is_active")
    search_fields = ("email", "username")
    ordering = ("email",)


# ------------------------
# Patient Admin
# ------------------------
@admin.register(PatientProfile)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "address")

    # filter users so only PATIENT role appears
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(role="PATIENT")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ------------------------
# Doctor Admin
# ------------------------
@admin.register(DoctorProfile)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "availability")

    # filter users so only DOCTOR role appears
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(role="DOCTOR")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ------------------------
# Appointment Admin
# ------------------------
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "date", "status")
    list_filter = ("status", "date")
    search_fields = ("patient__user__username", "doctor__user__username")


# ------------------------
# Register Custom User
# ------------------------
admin.site.register(User, CustomUserAdmin)
