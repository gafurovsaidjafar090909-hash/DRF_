from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActiveTimetableView, BootstrapView, GenerationView, LoginView, LogoutView, MeView, MyTimetableView, RegisterDirectorView, SchoolClassViewSet, SettingsView, SubjectViewSet, TeacherAvailabilityBulkView, TeacherUnavailableViewSet, TeacherViewSet, WeeklyRequirementViewSet

router = DefaultRouter()
router.register("subjects", SubjectViewSet)
router.register("classes", SchoolClassViewSet)
router.register("teachers", TeacherViewSet)
router.register("requirements", WeeklyRequirementViewSet)
router.register("unavailable", TeacherUnavailableViewSet)

urlpatterns = [
    path("auth/bootstrap/", BootstrapView.as_view()),
    path("auth/register/", RegisterDirectorView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("settings/", SettingsView.as_view()),
    path("availability/teachers/<int:teacher_id>/", TeacherAvailabilityBulkView.as_view()),
    path("generations/", GenerationView.as_view()),
    path("timetable/", ActiveTimetableView.as_view()),
    path("my-timetable/", MyTimetableView.as_view()),
    path("", include(router.urls)),
]
