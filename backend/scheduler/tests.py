from collections import Counter
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import Lesson, SchoolClass, SchoolSettings, Subject, Teacher, TeacherUnavailable, TimetableGeneration, WeeklyRequirement
from .services.generation import generate

User = get_user_model()


class GeneratorTests(TestCase):
    def setUp(self):
        self.director = User.objects.create_user(username="director", password="safe-password-123", role=User.Role.DIRECTOR)
        self.english = Subject.objects.create(name="English")
        self.math = Subject.objects.create(name="Mathematics")
        self.classes = [SchoolClass.objects.create(grade=grade, section="A") for grade in (5, 6)]
        SchoolSettings.objects.update_or_create(pk=1, defaults={"days": [0, 1, 2], "periods_per_day": 3})
        self.teachers = []
        for username, subject, capacity in (("ali", self.english, 4), ("farida", self.english, 2), ("said", self.math, 4)):
            user = User.objects.create_user(username=username, password="safe-password-123", role=User.Role.TEACHER)
            teacher = Teacher.objects.create(user=user, first_name=username.title(), last_name="Test", max_weekly_hours=capacity)
            teacher.subjects.add(subject)
            self.teachers.append(teacher)
        for school_class in self.classes:
            WeeklyRequirement.objects.create(school_class=school_class, subject=self.english, hours=3)
            WeeklyRequirement.objects.create(school_class=school_class, subject=self.math, hours=2)
        TeacherUnavailable.objects.create(teacher=self.teachers[0], day=0, period=1)

    def test_feasible_schedule_satisfies_all_hard_constraints(self):
        generation = generate(self.director)
        self.assertEqual(generation.status, TimetableGeneration.Status.COMPLETED, generation.diagnostics)
        lessons = list(Lesson.objects.filter(generation=generation).select_related("teacher", "subject", "school_class"))
        self.assertEqual(len(lessons), 10)
        counts = Counter((item.school_class_id, item.subject_id) for item in lessons)
        for requirement in WeeklyRequirement.objects.all():
            self.assertEqual(counts[(requirement.school_class_id, requirement.subject_id)], requirement.hours)
        self.assertEqual(len({(item.school_class_id, item.day, item.period) for item in lessons}), len(lessons))
        self.assertEqual(len({(item.teacher_id, item.day, item.period) for item in lessons}), len(lessons))
        for lesson in lessons:
            self.assertIn(lesson.subject, lesson.teacher.subjects.all())
            self.assertNotEqual((lesson.teacher_id, lesson.day, lesson.period), (self.teachers[0].id, 0, 1))
            self.assertIn(lesson.day, [0, 1, 2])
            self.assertIn(lesson.period, [1, 2, 3])
        for teacher in self.teachers:
            self.assertLessEqual(sum(item.teacher_id == teacher.id for item in lessons), teacher.max_weekly_hours)

    def test_insufficient_capacity_is_proven_infeasible(self):
        self.teachers[1].is_active = False
        self.teachers[1].save(update_fields=["is_active"])
        generation = generate(self.director)
        self.assertEqual(generation.status, TimetableGeneration.Status.INFEASIBLE)
        self.assertFalse(generation.is_active)
        self.assertIn("subject_capacity", [item["code"] for item in generation.diagnostics])
        self.assertEqual(Lesson.objects.count(), 0)

    def test_failed_generation_preserves_previous_active_schedule(self):
        first = generate(self.director)
        self.assertTrue(first.is_active)
        original_count = first.lessons.count()
        self.teachers[1].is_active = False
        self.teachers[1].save(update_fields=["is_active"])
        second = generate(self.director)
        self.assertEqual(second.status, TimetableGeneration.Status.INFEASIBLE)
        first.refresh_from_db()
        self.assertTrue(first.is_active)
        self.assertEqual(first.lessons.count(), original_count)
        self.assertEqual(TimetableGeneration.objects.filter(is_active=True).count(), 1)

    @patch("scheduler.services.generation.solve")
    def test_timeout_remains_distinct_from_infeasible(self, mocked_solve):
        mocked_solve.return_value = {"status": "timeout", "solver_status": "UNKNOWN", "duration": 5.0, "assignments": []}
        generation = generate(self.director)
        self.assertEqual(generation.status, TimetableGeneration.Status.TIMEOUT)
        self.assertEqual(generation.diagnostics[0]["code"], "solver_timeout")


class AuthenticationAndApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_first_director_can_register_once(self):
        first = self.client.post("/api/auth/register/", {"username": "director", "password": "secure-password-123"}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["user"]["role"], "director")
        again = self.client.post("/api/auth/register/", {"username": "another", "password": "secure-password-123"}, format="json")
        self.assertEqual(again.status_code, 403)

    def test_teacher_can_only_see_personal_timetable(self):
        director = User.objects.create_user(username="director", password="secure-password-123", role=User.Role.DIRECTOR)
        teacher_user = User.objects.create_user(username="teacher", password="secure-password-123", role=User.Role.TEACHER)
        subject = Subject.objects.create(name="English")
        teacher = Teacher.objects.create(user=teacher_user, first_name="Ali", last_name="Test", max_weekly_hours=8)
        teacher.subjects.add(subject)
        token = Token.objects.create(user=teacher_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(self.client.get("/api/my-timetable/").status_code, 200)
        self.assertEqual(self.client.get("/api/timetable/").status_code, 403)
        self.assertEqual(self.client.get("/api/teachers/").status_code, 403)
        self.assertEqual(self.client.post("/api/generations/").status_code, 403)
        self.assertEqual(self.client.get("/api/settings/").status_code, 200)
        self.assertEqual(self.client.put("/api/settings/", {"days": [0], "periods_per_day": 2}, format="json").status_code, 403)
        self.assertEqual(director.role, User.Role.DIRECTOR)
