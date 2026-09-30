from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Lesson, SchoolClass, SchoolSettings, Subject, Teacher, TeacherUnavailable, TimetableGeneration, WeeklyRequirement
from .permissions import IsDirector
from .serializers import GenerationSerializer, LessonSerializer, SchoolClassSerializer, SchoolSettingsSerializer, SubjectSerializer, TeacherSerializer, TeacherUnavailableSerializer, WeeklyRequirementSerializer
from .services.generation import MESSAGE, generate
from .services.revision import bump_revision

User = get_user_model()


class BootstrapView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"needs_registration": not User.objects.filter(role=User.Role.DIRECTOR).exists()})


class RegisterDirectorView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", ""))
        if len(username) < 3 or len(password) < 10:
            return Response({"code": "invalid_credentials", "detail": "Username must have 3+ characters and password 10+ characters."}, status=400)
        with transaction.atomic():
            if User.objects.filter(role=User.Role.DIRECTOR).exists():
                return Response({"code": "registration_closed", "detail": "Director registration is closed."}, status=403)
            if User.objects.filter(username=username).exists():
                return Response({"code": "username_used", "detail": "Username is already used."}, status=400)
            user = User.objects.create_superuser(username=username, password=password, role=User.Role.DIRECTOR)
            token = Token.objects.create(user=user)
        return Response({"token": token.key, "user": user_payload(user)}, status=201)


def user_payload(user):
    teacher = getattr(user, "teacher_profile", None)
    return {"id": user.id, "username": user.username, "role": user.role, "teacher_id": teacher.id if teacher else None}


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        user = authenticate(username=request.data.get("username", ""), password=request.data.get("password", ""))
        if not user or not user.is_active:
            return Response({"code": "login_failed", "detail": "Invalid username or password."}, status=400)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": user_payload(user)})


class MeView(APIView):
    def get(self, request):
        return Response(user_payload(request.user))


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"ok": True})


class DirectorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsDirector]

    def perform_create(self, serializer):
        with transaction.atomic():
            serializer.save()
            bump_revision()

    def perform_update(self, serializer):
        with transaction.atomic():
            serializer.save()
            bump_revision()

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.delete()
            bump_revision()


class SubjectViewSet(DirectorViewSet):
    queryset = Subject.objects.all().order_by("name")
    serializer_class = SubjectSerializer

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.is_active = False
            instance.save(update_fields=["is_active"])
            bump_revision()


class SchoolClassViewSet(DirectorViewSet):
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassSerializer

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.is_active = False
            instance.save(update_fields=["is_active"])
            bump_revision()


class TeacherViewSet(DirectorViewSet):
    queryset = Teacher.objects.select_related("user").prefetch_related("subjects").all()
    serializer_class = TeacherSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["active_generation"] = TimetableGeneration.objects.filter(is_active=True).first()
        return context

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.is_active = False
            instance.save(update_fields=["is_active"])
            instance.user.is_active = False
            instance.user.save(update_fields=["is_active"])
            bump_revision()


class WeeklyRequirementViewSet(DirectorViewSet):
    queryset = WeeklyRequirement.objects.select_related("school_class", "subject").all()
    serializer_class = WeeklyRequirementSerializer


class TeacherUnavailableViewSet(DirectorViewSet):
    queryset = TeacherUnavailable.objects.select_related("teacher").all()
    serializer_class = TeacherUnavailableSerializer


class TeacherAvailabilityBulkView(APIView):
    permission_classes = [IsDirector]

    def put(self, request, teacher_id):
        teacher = Teacher.objects.filter(pk=teacher_id).first()
        if not teacher:
            return Response({"code": "not_found"}, status=404)
        slots = request.data.get("slots")
        config = SchoolSettings.current()
        if not isinstance(slots, list) or len(slots) > len(config.days) * config.periods_per_day:
            return Response({"code": "invalid_availability"}, status=400)
        seen = set()
        for slot in slots:
            if not isinstance(slot, dict) or type(slot.get("day")) is not int or type(slot.get("period")) is not int or slot["day"] not in config.days or slot["period"] not in range(1, config.periods_per_day + 1):
                return Response({"code": "invalid_availability"}, status=400)
            seen.add((slot["day"], slot["period"]))
        if len(seen) != len(slots):
            return Response({"code": "invalid_availability"}, status=400)
        with transaction.atomic():
            TeacherUnavailable.objects.filter(teacher=teacher).delete()
            TeacherUnavailable.objects.bulk_create([TeacherUnavailable(teacher=teacher, day=day, period=period) for day, period in sorted(seen)])
            bump_revision()
        return Response({"teacher": teacher.id, "slots": slots})


class SettingsView(APIView):
    def get_permissions(self):
        return [IsDirector()] if self.request.method != "GET" else [permissions.IsAuthenticated()]

    def get(self, request):
        return Response(SchoolSettingsSerializer(SchoolSettings.current()).data)

    def put(self, request):
        setting = SchoolSettings.current()
        serializer = SchoolSettingsSerializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save()
            bump_revision()
        return Response(serializer.data)


class GenerationView(APIView):
    permission_classes = [IsDirector]

    def get(self, request):
        rows = TimetableGeneration.objects.all()[:20]
        return Response(GenerationSerializer(rows, many=True).data)

    def post(self, request):
        generation = generate(request.user)
        payload = GenerationSerializer(generation).data
        if generation.status != TimetableGeneration.Status.COMPLETED:
            payload["message"] = MESSAGE
        return Response(payload, status=status.HTTP_200_OK)


class ActiveTimetableView(APIView):
    permission_classes = [IsDirector]

    def get(self, request):
        generation = TimetableGeneration.objects.filter(is_active=True).first()
        if not generation:
            return Response({"generation": None, "lessons": []})
        lessons = Lesson.objects.filter(generation=generation).select_related("school_class", "subject", "teacher")
        return Response({"generation": GenerationSerializer(generation).data, "lessons": LessonSerializer(lessons, many=True).data})


class MyTimetableView(APIView):
    def get(self, request):
        if request.user.role != User.Role.TEACHER:
            return Response({"code": "teacher_only", "detail": "Teacher account required."}, status=403)
        teacher = getattr(request.user, "teacher_profile", None)
        if not teacher:
            return Response({"code": "profile_missing", "detail": "Teacher profile missing."}, status=404)
        generation = TimetableGeneration.objects.filter(is_active=True).first()
        lessons = Lesson.objects.filter(generation=generation, teacher=teacher).select_related("school_class", "subject", "teacher") if generation else Lesson.objects.none()
        return Response({"teacher": {"id": teacher.id, "name": str(teacher), "max_weekly_hours": teacher.max_weekly_hours}, "generation": GenerationSerializer(generation).data if generation else None, "assigned_hours": lessons.count(), "lessons": LessonSerializer(lessons, many=True).data})
