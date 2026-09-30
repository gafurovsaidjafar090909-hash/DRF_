from django.conf import settings
from django.db import transaction

from scheduler.models import Lesson, SchoolClass, SchoolSettings, Subject, Teacher, TeacherUnavailable, TimetableGeneration, WeeklyRequirement
from .solver import solve
from .validation import diagnostic, preflight, validate_solution


MESSAGE = "Timetable cannot be generated with the current constraints."


def generate(created_by, time_limit=None):
    config = SchoolSettings.current()
    revision = config.revision
    days = list(config.days)
    periods = config.periods_per_day
    classes = list(SchoolClass.objects.filter(is_active=True))
    subjects = list(Subject.objects.filter(is_active=True))
    teachers = list(Teacher.objects.filter(is_active=True, user__is_active=True).prefetch_related("subjects"))
    requirements = list(WeeklyRequirement.objects.select_related("school_class", "subject").filter(school_class__is_active=True))
    unavailable = list(TeacherUnavailable.objects.filter(teacher__in=teachers))
    generation = TimetableGeneration.objects.create(created_by=created_by)
    issues = preflight(classes, subjects, teachers, requirements, unavailable, days, periods)
    if issues:
        generation.status = TimetableGeneration.Status.INFEASIBLE
        generation.diagnostics = issues
        generation.solver_status = "PREFLIGHT_PROOF"
        generation.save(update_fields=["status", "diagnostics", "solver_status"])
        return generation
    try:
        result = solve(classes, teachers, requirements, unavailable, days, periods, time_limit or settings.SOLVER_TIME_LIMIT_SECONDS)
    except Exception:
        generation.status = TimetableGeneration.Status.ERROR
        generation.diagnostics = [diagnostic("solver_error")]
        generation.save(update_fields=["status", "diagnostics"])
        return generation
    generation.status = result["status"]
    generation.solver_status = result["solver_status"]
    generation.duration_seconds = result["duration"]
    if result["status"] != "completed":
        code = "solver_proved_infeasible" if result["status"] == "infeasible" else "solver_timeout" if result["status"] == "timeout" else "solver_error"
        generation.diagnostics = [diagnostic(code, solver_status=result["solver_status"]) ]
        generation.save(update_fields=["status", "solver_status", "duration_seconds", "diagnostics"])
        return generation
    errors = validate_solution(result["assignments"], teachers, requirements, unavailable, days, periods)
    if errors:
        generation.status = TimetableGeneration.Status.ERROR
        generation.diagnostics = errors
        generation.save(update_fields=["status", "solver_status", "duration_seconds", "diagnostics"])
        return generation
    with transaction.atomic():
        locked = SchoolSettings.objects.select_for_update().get(pk=1)
        if locked.revision != revision:
            generation.status = TimetableGeneration.Status.ERROR
            generation.diagnostics = [diagnostic("input_changed")]
            generation.save(update_fields=["status", "diagnostics"])
            return generation
        # The old active timetable survives unless every new lesson is valid and saved.
        TimetableGeneration.objects.filter(is_active=True).update(is_active=False)
        Lesson.objects.bulk_create([Lesson(generation=generation, **row) for row in result["assignments"]])
        generation.is_active = True
        generation.save(update_fields=["status", "solver_status", "duration_seconds", "is_active"])
    return generation
