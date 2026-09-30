from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class Role(models.TextChoices):
        DIRECTOR = "director", "Director"
        TEACHER = "teacher", "Teacher"

    role = models.CharField(max_length=12, choices=Role.choices, default=Role.TEACHER)


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class SchoolClass(models.Model):
    grade = models.PositiveSmallIntegerField(validators=[MinValueValidator(5), MaxValueValidator(11)])
    section = models.CharField(max_length=5, default="A")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["grade", "section"], name="unique_grade_section"),
            models.CheckConstraint(condition=Q(grade__gte=5) & Q(grade__lte=11), name="grade_5_to_11"),
        ]
        ordering = ["grade", "section"]

    def __str__(self):
        return f"{self.grade}{self.section}"


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="teacher_profile")
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    subjects = models.ManyToManyField(Subject, related_name="teachers")
    max_weekly_hours = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(60)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["first_name", "last_name", "id"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class WeeklyRequirement(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="requirements")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="requirements")
    hours = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(60)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["school_class", "subject"], name="unique_class_subject_requirement")]
        ordering = ["school_class__grade", "school_class__section", "subject__name"]


class SchoolSettings(models.Model):
    days = models.JSONField(default=list)
    periods_per_day = models.PositiveSmallIntegerField(default=6, validators=[MinValueValidator(1), MaxValueValidator(10)])
    revision = models.PositiveBigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def current(cls):
        value, _ = cls.objects.get_or_create(pk=1, defaults={"days": [0, 1, 2, 3, 4, 5], "periods_per_day": 6})
        return value


class TeacherUnavailable(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="unavailable_slots")
    day = models.PositiveSmallIntegerField(validators=[MaxValueValidator(5)])
    period = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["teacher", "day", "period"], name="unique_teacher_unavailable_slot"),
            models.CheckConstraint(condition=Q(day__gte=0) & Q(day__lte=5), name="unavailable_day_range"),
            models.CheckConstraint(condition=Q(period__gte=1) & Q(period__lte=10), name="unavailable_period_range"),
        ]


class TimetableGeneration(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        INFEASIBLE = "infeasible", "Infeasible"
        TIMEOUT = "timeout", "Timeout / unknown"
        ERROR = "error", "Error"

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="generations")
    diagnostics = models.JSONField(default=list)
    solver_status = models.CharField(max_length=30, blank=True)
    duration_seconds = models.FloatField(default=0)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["is_active"], condition=Q(is_active=True), name="one_active_generation")]


class Lesson(models.Model):
    generation = models.ForeignKey(TimetableGeneration, on_delete=models.CASCADE, related_name="lessons")
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="lessons")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="lessons")
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name="lessons")
    day = models.PositiveSmallIntegerField()
    period = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["day", "period", "school_class__grade", "school_class__section"]
        constraints = [
            models.UniqueConstraint(fields=["generation", "school_class", "day", "period"], name="one_class_per_generation_slot"),
            models.UniqueConstraint(fields=["generation", "teacher", "day", "period"], name="one_teacher_per_generation_slot"),
            models.CheckConstraint(condition=Q(day__gte=0) & Q(day__lte=5), name="lesson_day_range"),
            models.CheckConstraint(condition=Q(period__gte=1) & Q(period__lte=10), name="lesson_period_range"),
        ]
