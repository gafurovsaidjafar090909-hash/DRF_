from collections import defaultdict

from ortools.sat.python import cp_model


def solve(classes, teachers, requirements, unavailable, days, periods, time_limit=20):
    """Assign teacher and time for every required lesson with CP-SAT."""
    model = cp_model.CpModel()
    blocked = {(row.teacher_id, row.day, row.period) for row in unavailable}
    teacher_subjects = {teacher.id: {subject.id for subject in teacher.subjects.all()} for teacher in teachers}
    options = {}
    by_requirement = defaultdict(list)
    by_class_slot = defaultdict(list)
    by_teacher_slot = defaultdict(list)
    by_teacher = defaultdict(list)
    by_class_day = defaultdict(list)
    by_requirement_day = defaultdict(list)
    for requirement in requirements:
        for teacher in teachers:
            if requirement.subject_id not in teacher_subjects[teacher.id]:
                continue
            for day in days:
                for period in range(1, periods + 1):
                    if (teacher.id, day, period) in blocked:
                        continue
                    key = (requirement.id, teacher.id, day, period)
                    var = model.NewBoolVar(f"r{requirement.id}_t{teacher.id}_d{day}_p{period}")
                    options[key] = var
                    by_requirement[requirement.id].append(var)
                    by_class_slot[(requirement.school_class_id, day, period)].append(var)
                    by_teacher_slot[(teacher.id, day, period)].append(var)
                    by_teacher[teacher.id].append(var)
                    by_class_day[(requirement.school_class_id, day)].append(var)
                    by_requirement_day[(requirement.id, day)].append(var)
    for requirement in requirements:
        model.Add(sum(by_requirement[requirement.id]) == requirement.hours)
    for vars_at_slot in by_class_slot.values():
        model.Add(sum(vars_at_slot) <= 1)
    for vars_at_slot in by_teacher_slot.values():
        model.Add(sum(vars_at_slot) <= 1)
    for teacher in teachers:
        model.Add(sum(by_teacher[teacher.id]) <= teacher.max_weekly_hours)

    objective = []
    # Balance the number of class lessons between school days.
    for school_class in classes:
        daily = []
        for day in days:
            count = model.NewIntVar(0, periods, f"class{school_class.id}_day{day}_count")
            model.Add(count == sum(by_class_day[(school_class.id, day)]))
            daily.append(count)
        maximum = model.NewIntVar(0, periods, f"class{school_class.id}_max")
        minimum = model.NewIntVar(0, periods, f"class{school_class.id}_min")
        model.AddMaxEquality(maximum, daily)
        model.AddMinEquality(minimum, daily)
        objective.append(3 * (maximum - minimum))

    # Repeating a subject on the same day is allowed, but costs a small penalty.
    for requirement in requirements:
        for day in days:
            count = model.NewIntVar(0, min(requirement.hours, periods), f"req{requirement.id}_day{day}_count")
            model.Add(count == sum(by_requirement_day[(requirement.id, day)]))
            excess = model.NewIntVar(0, periods, f"req{requirement.id}_day{day}_excess")
            model.Add(excess >= count - 1)
            objective.append(4 * excess)

    # Penalize every free period between a teacher's first and last lesson.
    for teacher in teachers:
        for day in days:
            busy = {}
            for period in range(1, periods + 1):
                busy[period] = model.NewBoolVar(f"teacher{teacher.id}_day{day}_period{period}_busy")
                model.Add(busy[period] == sum(by_teacher_slot[(teacher.id, day, period)]))
            for period in range(2, periods):
                before = model.NewBoolVar(f"teacher{teacher.id}_day{day}_before{period}")
                after = model.NewBoolVar(f"teacher{teacher.id}_day{day}_after{period}")
                model.AddMaxEquality(before, [busy[index] for index in range(1, period)])
                model.AddMaxEquality(after, [busy[index] for index in range(period + 1, periods + 1)])
                hole = model.NewBoolVar(f"teacher{teacher.id}_day{day}_period{period}_hole")
                model.Add(hole >= before + after - busy[period] - 1)
                objective.append(2 * hole)

    model.Minimize(sum(objective))
    engine = cp_model.CpSolver()
    engine.parameters.max_time_in_seconds = time_limit
    engine.parameters.num_search_workers = 8
    status = engine.Solve(model)
    status_name = engine.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "infeasible" if status == cp_model.INFEASIBLE else "timeout" if status == cp_model.UNKNOWN else "error", "solver_status": status_name, "duration": engine.WallTime(), "assignments": []}
    assignments = []
    requirement_by_id = {row.id: row for row in requirements}
    for (requirement_id, teacher_id, day, period), var in options.items():
        if engine.Value(var):
            requirement = requirement_by_id[requirement_id]
            assignments.append({
                "school_class_id": requirement.school_class_id, "subject_id": requirement.subject_id,
                "teacher_id": teacher_id, "day": day, "period": period,
            })
    assignments.sort(key=lambda row: (row["day"], row["period"], row["school_class_id"]))
    return {"status": "completed", "solver_status": status_name, "duration": engine.WallTime(), "assignments": assignments}
