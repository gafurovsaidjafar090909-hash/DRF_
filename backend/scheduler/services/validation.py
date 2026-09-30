from collections import Counter, defaultdict


def diagnostic(code, **params):
    return {"code": code, "params": params}


def preflight(classes, subjects, teachers, requirements, unavailable, days, periods):
    """Only report failures that prove infeasibility for the given hard constraints."""
    issues = []
    if not days or len(set(days)) != len(days) or any(day not in range(6) for day in days):
        return [diagnostic("invalid_days")]
    slots = {(day, period) for day in days for period in range(1, periods + 1)}
    class_by_id = {item.id: item for item in classes}
    subject_by_id = {item.id: item for item in subjects}
    eligible = defaultdict(list)
    for teacher in teachers:
        for subject in teacher.subjects.all():
            eligible[subject.id].append(teacher)
    blocked = {(item.teacher_id, item.day, item.period) for item in unavailable}
    requirements_by_class = defaultdict(list)
    requirements_by_subject = defaultdict(list)
    for requirement in requirements:
        school_class = class_by_id.get(requirement.school_class_id)
        subject = subject_by_id.get(requirement.subject_id)
        if not school_class or not school_class.is_active or not subject or not subject.is_active:
            issues.append(diagnostic("inactive_requirement", school_class=str(requirement.school_class), subject=requirement.subject.name))
            continue
        requirements_by_class[requirement.school_class_id].append(requirement)
        requirements_by_subject[requirement.subject_id].append(requirement)
    for class_id, rows in requirements_by_class.items():
        demand = sum(row.hours for row in rows)
        if demand > len(slots):
            issues.append(diagnostic("class_capacity", school_class=str(class_by_id[class_id]), required=demand, capacity=len(slots)))
    for subject_id, rows in requirements_by_subject.items():
        subject = subject_by_id[subject_id]
        subject_teachers = eligible[subject_id]
        demand = sum(row.hours for row in rows)
        if not subject_teachers:
            issues.append(diagnostic("no_teacher", subject=subject.name, required=demand, capacity=0))
            continue
        effective = {teacher.id: min(teacher.max_weekly_hours, sum((teacher.id, day, period) not in blocked for day, period in slots)) for teacher in subject_teachers}
        capacity = sum(effective.values())
        if capacity < demand:
            issues.append(diagnostic("subject_capacity", subject=subject.name, required=demand, capacity=capacity))
        for row in rows:
            available_slots = sum(any((teacher.id, day, period) not in blocked for teacher in subject_teachers) for day, period in slots)
            if row.hours > available_slots:
                issues.append(diagnostic("class_subject_slots", school_class=str(class_by_id[row.school_class_id]), subject=subject.name, required=row.hours, capacity=available_slots))
        slot_capacity = sum(min(len(rows), sum((teacher.id, day, period) not in blocked for teacher in subject_teachers)) for day, period in slots)
        if demand > slot_capacity:
            issues.append(diagnostic("subject_slots", subject=subject.name, required=demand, capacity=slot_capacity))
    total_demand = sum(row.hours for row in requirements)
    total_capacity = sum(min(teacher.max_weekly_hours, sum((teacher.id, day, period) not in blocked for day, period in slots)) for teacher in teachers)
    if total_demand > total_capacity:
        issues.append(diagnostic("school_capacity", required=total_demand, capacity=total_capacity))
    if not requirements:
        issues.append(diagnostic("no_requirements"))
    return issues


def validate_solution(assignments, teachers, requirements, unavailable, days, periods):
    """Run independently of CP-SAT before writing any lesson."""
    errors = []
    by_teacher = {teacher.id: teacher for teacher in teachers}
    blocked = {(item.teacher_id, item.day, item.period) for item in unavailable}
    expected = {(row.school_class_id, row.subject_id): row.hours for row in requirements}
    actual = Counter()
    teacher_load = Counter()
    class_slots = set()
    teacher_slots = set()
    allowed_days = set(days)
    for row in assignments:
        teacher = by_teacher.get(row["teacher_id"])
        if not teacher or row["subject_id"] not in {subject.id for subject in teacher.subjects.all()}:
            errors.append(diagnostic("wrong_teacher", subject_id=row["subject_id"], teacher_id=row["teacher_id"]))
        if row["day"] not in allowed_days or row["period"] not in range(1, periods + 1):
            errors.append(diagnostic("outside_school_hours", day=row["day"], period=row["period"]))
        if (row["teacher_id"], row["day"], row["period"]) in blocked:
            errors.append(diagnostic("teacher_unavailable", teacher_id=row["teacher_id"], day=row["day"], period=row["period"]))
        class_key = (row["school_class_id"], row["day"], row["period"])
        teacher_key = (row["teacher_id"], row["day"], row["period"])
        if class_key in class_slots:
            errors.append(diagnostic("class_collision", school_class_id=row["school_class_id"], day=row["day"], period=row["period"]))
        if teacher_key in teacher_slots:
            errors.append(diagnostic("teacher_collision", teacher_id=row["teacher_id"], day=row["day"], period=row["period"]))
        class_slots.add(class_key)
        teacher_slots.add(teacher_key)
        actual[(row["school_class_id"], row["subject_id"])] += 1
        teacher_load[row["teacher_id"]] += 1
    for key, hours in expected.items():
        if actual[key] != hours:
            errors.append(diagnostic("requirement_mismatch", school_class_id=key[0], subject_id=key[1], required=hours, assigned=actual[key]))
    for key in actual.keys() - expected.keys():
        errors.append(diagnostic("unexpected_lesson", school_class_id=key[0], subject_id=key[1]))
    for teacher in teachers:
        if teacher_load[teacher.id] > teacher.max_weekly_hours:
            errors.append(diagnostic("teacher_overload", teacher_id=teacher.id, assigned=teacher_load[teacher.id], capacity=teacher.max_weekly_hours))
    return errors
