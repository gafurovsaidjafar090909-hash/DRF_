from django.db.models import F
from scheduler.models import SchoolSettings


def bump_revision():
    SchoolSettings.current()
    SchoolSettings.objects.filter(pk=1).update(revision=F("revision") + 1)
