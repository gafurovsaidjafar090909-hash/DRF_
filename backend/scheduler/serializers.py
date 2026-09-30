from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Lesson, SchoolClass, SchoolSettings, Subject, Teacher, TeacherUnavailable, TimetableGeneration, WeeklyRequirement

User = get_user_model()


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "is_active"]


class SchoolClassSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = SchoolClass
        fields = ["id", "grade", "section", "label", "is_active"]


class TeacherSerializer(serializers.ModelSerializer):
    subject_ids = serializers.PrimaryKeyRelatedField(source="subjects", many=True, queryset=Subject.objects.all())
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    account_username = serializers.CharField(source="user.username", read_only=True)
    assigned_hours = serializers.SerializerMethodField()
    remaining_hours = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ["id", "first_name", "last_name", "subject_ids", "max_weekly_hours", "is_active", "username", "password", "account_username", "assigned_hours", "remaining_hours"]

    def validate(self, attrs):
        subjects = attrs.get("subjects", None)
        if subjects is not None and not subjects:
            raise serializers.ValidationError({"subject_ids": "At least one subject is required."})
        username = attrs.get("username")
        if self.instance is None and (not username or not attrs.get("password")):
            raise serializers.ValidationError({"username": "Username and password are required for a teacher account."})
        if username and User.objects.filter(username=username).exclude(pk=self.instance.user_id if self.instance else None).exists():
            raise serializers.ValidationError({"username": "Username is already used."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        subjects = validated_data.pop("subjects")
        username = validated_data.pop("username")
        password = validated_data.pop("password")
        user = User.objects.create_user(username=username, password=password, role=User.Role.TEACHER)
        teacher = Teacher.objects.create(user=user, **validated_data)
        teacher.subjects.set(subjects)
        return teacher

    @transaction.atomic
    def update(self, instance, validated_data):
        subjects = validated_data.pop("subjects", None)
        username = validated_data.pop("username", None)
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if subjects is not None:
            instance.subjects.set(subjects)
        if username:
            instance.user.username = username
        if password:
            instance.user.set_password(password)
        instance.user.is_active = instance.is_active
        instance.user.save()
        return instance

    def get_assigned_hours(self, obj):
        generation = self.context.get("active_generation")
        return obj.lessons.filter(generation=generation).count() if generation else 0

    def get_remaining_hours(self, obj):
        return obj.max_weekly_hours - self.get_assigned_hours(obj)


class WeeklyRequirementSerializer(serializers.ModelSerializer):
    class_label = serializers.CharField(source="school_class.__str__", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = WeeklyRequirement
        fields = ["id", "school_class", "class_label", "subject", "subject_name", "hours"]
        validators = [serializers.UniqueTogetherValidator(queryset=WeeklyRequirement.objects.all(), fields=["school_class", "subject"])]

    def validate(self, attrs):
        school_class = attrs.get("school_class", getattr(self.instance, "school_class", None))
        subject = attrs.get("subject", getattr(self.instance, "subject", None))
        if school_class and not school_class.is_active:
            raise serializers.ValidationError({"school_class": "Class is inactive."})
        if subject and not subject.is_active:
            raise serializers.ValidationError({"subject": "Subject is inactive."})
        return attrs


class SchoolSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolSettings
        fields = ["days", "periods_per_day", "revision", "updated_at"]
        read_only_fields = ["revision", "updated_at"]

    def validate_days(self, value):
        if not isinstance(value, list) or not value or len(value) != len(set(str(day) for day in value)) or any(type(day) is not int or day not in range(6) for day in value):
            raise serializers.ValidationError("Select unique school days from Monday to Saturday.")
        return sorted(value)


class TeacherUnavailableSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.__str__", read_only=True)

    class Meta:
        model = TeacherUnavailable
        fields = ["id", "teacher", "teacher_name", "day", "period"]
        validators = [serializers.UniqueTogetherValidator(queryset=TeacherUnavailable.objects.all(), fields=["teacher", "day", "period"])]

    def validate(self, attrs):
        config = SchoolSettings.current()
        day = attrs.get("day", getattr(self.instance, "day", None))
        period = attrs.get("period", getattr(self.instance, "period", None))
        if day not in config.days or period not in range(1, config.periods_per_day + 1):
            raise serializers.ValidationError("Unavailable slot must be inside the school week.")
        return attrs


class LessonSerializer(serializers.ModelSerializer):
    class_label = serializers.CharField(source="school_class.__str__", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.__str__", read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "school_class", "class_label", "subject", "subject_name", "teacher", "teacher_name", "day", "period"]


class GenerationSerializer(serializers.ModelSerializer):
    lesson_count = serializers.IntegerField(source="lessons.count", read_only=True)

    class Meta:
        model = TimetableGeneration
        fields = ["id", "status", "is_active", "created_at", "diagnostics", "solver_status", "duration_seconds", "lesson_count"]
