from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Subject, SchoolClass, Teacher, WeeklyRequirement, SchoolSettings, TeacherUnavailable, TimetableGeneration, Lesson


@admin.register(User)
class SchedulerUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("School role", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("School role", {"fields": ("role",)}),)
    list_display = ("username", "role", "is_staff", "is_active")


for model in (Subject, SchoolClass, Teacher, WeeklyRequirement, SchoolSettings, TeacherUnavailable, TimetableGeneration, Lesson):
    admin.site.register(model)
