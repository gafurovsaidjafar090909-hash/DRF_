import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from scheduler.models import SchoolClass, SchoolSettings, Subject, Teacher, TeacherUnavailable, WeeklyRequirement
from scheduler.services.revision import bump_revision

User = get_user_model()


class Command(BaseCommand):
    help = "Create a feasible or provably infeasible example school."

    def add_arguments(self, parser):
        parser.add_argument("--scenario", choices=["feasible", "infeasible"], default="feasible")
        parser.add_argument("--director-password", default=os.getenv("DEMO_DIRECTOR_PASSWORD"))
        parser.add_argument("--teacher-password", default=os.getenv("DEMO_TEACHER_PASSWORD"))

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["director_password"] or not options["teacher_password"]:
            raise CommandError("Set DEMO_DIRECTOR_PASSWORD and DEMO_TEACHER_PASSWORD or pass both password options.")
        director, _ = User.objects.get_or_create(username="director", defaults={"role": User.Role.DIRECTOR, "is_staff": True, "is_superuser": True})
        director.role = User.Role.DIRECTOR
        director.is_staff = True
        director.is_superuser = True
        director.is_active = True
        director.set_password(options["director_password"])
        director.save()
        subjects = {name: Subject.objects.update_or_create(name=name, defaults={"is_active": True})[0] for name in ["English", "Mathematics", "Physics"]}
        SchoolSettings.objects.update_or_create(pk=1, defaults={"days": [0, 1, 2, 3, 4, 5], "periods_per_day": 6})
        classes = {grade: SchoolClass.objects.update_or_create(grade=grade, section="A", defaults={"is_active": True})[0] for grade in range(5, 12)}
        teachers = [
            ("ali", "Али", "", ["English"], 18),
            ("farida", "Фарида", "", ["English"], 3),
            ("said", "Саид", "", ["Mathematics"], 20),
            ("farzona", "Фарзона", "", ["Mathematics"], 15),
            ("madina", "Мадина", "", ["Physics"], 16),
        ]
        for username, first_name, last_name, subject_names, maximum in teachers:
            user, _ = User.objects.get_or_create(username=username, defaults={"role": User.Role.TEACHER})
            user.role = User.Role.TEACHER
            user.is_active = True
            user.set_password(options["teacher_password"])
            user.save()
            teacher, _ = Teacher.objects.update_or_create(user=user, defaults={"first_name": first_name, "last_name": last_name, "max_weekly_hours": maximum, "is_active": options["scenario"] != "infeasible" or username != "farida"})
            teacher.subjects.set([subjects[name] for name in subject_names])
        for grade in range(5, 12):
            for subject_name, hours in [("English", 3), ("Mathematics", 5), ("Physics", 3 if grade >= 10 else 2)]:
                WeeklyRequirement.objects.update_or_create(school_class=classes[grade], subject=subjects[subject_name], defaults={"hours": hours})
        TeacherUnavailable.objects.update_or_create(teacher=Teacher.objects.get(user__username="madina"), day=0, period=1)
        TeacherUnavailable.objects.update_or_create(teacher=Teacher.objects.get(user__username="said"), day=1, period=2)
        bump_revision()
        self.stdout.write(self.style.SUCCESS(f"Seeded {options['scenario']} school. Director username: director; teacher usernames: ali, farida, said, farzona, madina."))
