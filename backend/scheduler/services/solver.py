from collections import defaultdict

from ortools.sat.python import cp_model


def solve(classes, teachers, requirements, unavailable, days, periods, time_limit=20):
    """
    Assign teacher and time for every required lesson with CP-SAT.

    Rules:
    - A class can have only one lesson in one period.
    - A teacher can teach only one lesson in one period.
    - Teacher unavailable slots are blocked.
    - Teacher weekly maximum hours are respected.
    - Lessons for the same class on the same day start from period 1
      and continue without gaps.
    """

    model = cp_model.CpModel()

    # ---------------------------------------------------------
    # 1. BLOCKED TEACHER SLOTS
    # ---------------------------------------------------------

    blocked = {
        (row.teacher_id, row.day, row.period)
        for row in unavailable
    }

    # ---------------------------------------------------------
    # 2. SUBJECTS THAT EACH TEACHER CAN TEACH
    # ---------------------------------------------------------

    teacher_subjects = {
        teacher.id: {
            subject.id
            for subject in teacher.subjects.all()
        }
        for teacher in teachers
    }

    # ---------------------------------------------------------
    # 3. VARIABLES
    # ---------------------------------------------------------

    options = {}

    by_requirement = defaultdict(list)
    by_class_slot = defaultdict(list)
    by_teacher_slot = defaultdict(list)
    by_teacher = defaultdict(list)
    by_class_day = defaultdict(list)
    by_requirement_day = defaultdict(list)

    for requirement in requirements:

        for teacher in teachers:

            # Teacher must teach this subject.
            if requirement.subject_id not in teacher_subjects[teacher.id]:
                continue

            for day in days:

                for period in range(1, periods + 1):

                    # Teacher is unavailable.
                    if (teacher.id, day, period) in blocked:
                        continue

                    key = (
                        requirement.id,
                        teacher.id,
                        day,
                        period,
                    )

                    var = model.NewBoolVar(
                        f"r{requirement.id}_"
                        f"t{teacher.id}_"
                        f"d{day}_"
                        f"p{period}"
                    )

                    options[key] = var

                    by_requirement[requirement.id].append(var)

                    by_class_slot[
                        (requirement.school_class_id, day, period)
                    ].append(var)

                    by_teacher_slot[
                        (teacher.id, day, period)
                    ].append(var)

                    by_teacher[teacher.id].append(var)

                    by_class_day[
                        (requirement.school_class_id, day)
                    ].append(var)

                    by_requirement_day[
                        (requirement.id, day)
                    ].append(var)

    # ---------------------------------------------------------
    # 4. EVERY REQUIREMENT MUST GET EXACTLY ITS HOURS
    # ---------------------------------------------------------

    for requirement in requirements:

        model.Add(
            sum(by_requirement[requirement.id])
            == requirement.hours
        )

    # ---------------------------------------------------------
    # 5. ONE LESSON PER CLASS PER PERIOD
    # ---------------------------------------------------------

    for vars_at_slot in by_class_slot.values():

        model.Add(
            sum(vars_at_slot) <= 1
        )

    # ---------------------------------------------------------
    # 6. ONE LESSON PER TEACHER PER PERIOD
    # ---------------------------------------------------------

    for vars_at_slot in by_teacher_slot.values():

        model.Add(
            sum(vars_at_slot) <= 1
        )

    # ---------------------------------------------------------
    # 7. TEACHER WEEKLY MAXIMUM HOURS
    # ---------------------------------------------------------

    for teacher in teachers:

        model.Add(
            sum(by_teacher[teacher.id])
            <= teacher.max_weekly_hours
        )

    # =========================================================
    # 8. NO GAPS FOR A CLASS
    # =========================================================
    #
    # Example:
    #
    #   1 -> Math
    #   2 -> Physics
    #   3 -> English
    #   4 -> History
    #
    # Allowed.
    #
    # But:
    #
    #   1 -> Math
    #   2 -> EMPTY
    #   3 -> Physics
    #
    # NOT allowed.
    #
    # If period N is used, every previous period must be used.
    # =========================================================

    class_day_busy = {}

    for school_class in classes:

        for day in days:

            for period in range(1, periods + 1):

                busy = model.NewBoolVar(
                    f"class{school_class.id}_"
                    f"day{day}_"
                    f"period{period}_busy"
                )

                vars_at_slot = by_class_slot[
                    (school_class.id, day, period)
                ]

                if vars_at_slot:
                    model.Add(
                        busy == sum(vars_at_slot)
                    )
                else:
                    model.Add(
                        busy == 0
                    )

                class_day_busy[
                    (school_class.id, day, period)
                ] = busy

            # -------------------------------------------------
            # NO GAP RULE
            #
            # busy[period] = 1
            # => busy[period - 1] = 1
            #
            # Therefore:
            #
            # 1,2,3,4 = allowed
            # 1,2,3   = allowed
            # 1,2     = allowed
            # 1,3     = forbidden
            # -------------------------------------------------

            for period in range(2, periods + 1):

                current = class_day_busy[
                    (school_class.id, day, period)
                ]

                previous = class_day_busy[
                    (school_class.id, day, period - 1)
                ]

                model.Add(
                    current <= previous
                )

    # =========================================================
    # 9. BALANCE CLASS LESSONS BETWEEN SCHOOL DAYS
    # =========================================================

    objective = []

    for school_class in classes:

        daily = []

        for day in days:

            count = model.NewIntVar(
                0,
                periods,
                f"class{school_class.id}_day{day}_count"
            )

            model.Add(
                count
                == sum(
                    by_class_day[
                        (school_class.id, day)
                    ]
                )
            )

            daily.append(count)

        maximum = model.NewIntVar(
            0,
            periods,
            f"class{school_class.id}_max"
        )

        minimum = model.NewIntVar(
            0,
            periods,
            f"class{school_class.id}_min"
        )

        model.AddMaxEquality(
            maximum,
            daily
        )

        model.AddMinEquality(
            minimum,
            daily
        )

        objective.append(
            3 * (maximum - minimum)
        )

    # =========================================================
    # 10. REPEATING SAME SUBJECT ON SAME DAY
    # =========================================================

    for requirement in requirements:

        for day in days:

            count = model.NewIntVar(
                0,
                min(requirement.hours, periods),
                f"req{requirement.id}_day{day}_count"
            )

            model.Add(
                count
                == sum(
                    by_requirement_day[
                        (requirement.id, day)
                    ]
                )
            )

            excess = model.NewIntVar(
                0,
                periods,
                f"req{requirement.id}_day{day}_excess"
            )

            model.Add(
                excess >= count - 1
            )

            objective.append(
                4 * excess
            )

    # =========================================================
    # 11. TEACHER FREE PERIODS / HOLES
    # =========================================================

    for teacher in teachers:

        for day in days:

            busy = {}

            for period in range(1, periods + 1):

                busy[period] = model.NewBoolVar(
                    f"teacher{teacher.id}_"
                    f"day{day}_"
                    f"period{period}_busy"
                )

                vars_at_slot = by_teacher_slot[
                    (teacher.id, day, period)
                ]

                if vars_at_slot:
                    model.Add(
                        busy[period]
                        == sum(vars_at_slot)
                    )
                else:
                    model.Add(
                        busy[period] == 0
                    )

            for period in range(2, periods):

                before = model.NewBoolVar(
                    f"teacher{teacher.id}_"
                    f"day{day}_"
                    f"before{period}"
                )

                after = model.NewBoolVar(
                    f"teacher{teacher.id}_"
                    f"day{day}_"
                    f"after{period}"
                )

                model.AddMaxEquality(
                    before,
                    [
                        busy[index]
                        for index in range(1, period)
                    ]
                )

                model.AddMaxEquality(
                    after,
                    [
                        busy[index]
                        for index in range(
                            period + 1,
                            periods + 1
                        )
                    ]
                )

                hole = model.NewBoolVar(
                    f"teacher{teacher.id}_"
                    f"day{day}_"
                    f"period{period}_hole"
                )

                model.Add(
                    hole
                    >= before + after - busy[period] - 1
                )

                objective.append(
                    2 * hole
                )

    # =========================================================
    # 12. MINIMIZE PENALTIES
    # =========================================================

    model.Minimize(
        sum(objective)
    )

    # =========================================================
    # 13. RUN CP-SAT
    # =========================================================

    engine = cp_model.CpSolver()

    engine.parameters.max_time_in_seconds = time_limit

    engine.parameters.num_search_workers = 8

    status = engine.Solve(model)

    status_name = engine.StatusName(status)

    # =========================================================
    # 14. SOLVER FAILED
    # =========================================================

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):

        return {
            "status": (
                "infeasible"
                if status == cp_model.INFEASIBLE
                else "timeout"
                if status == cp_model.UNKNOWN
                else "error"
            ),
            "solver_status": status_name,
            "duration": engine.WallTime(),
            "assignments": [],
        }

    # =========================================================
    # 15. CREATE ASSIGNMENTS
    # =========================================================

    assignments = []

    requirement_by_id = {
        row.id: row
        for row in requirements
    }

    for (
        requirement_id,
        teacher_id,
        day,
        period,
    ), var in options.items():

        if engine.Value(var):

            requirement = requirement_by_id[
                requirement_id
            ]

            assignments.append(
                {
                    "school_class_id":
                        requirement.school_class_id,

                    "subject_id":
                        requirement.subject_id,

                    "teacher_id":
                        teacher_id,

                    "day":
                        day,

                    "period":
                        period,
                }
            )

    # =========================================================
    # 16. SORT TIMETABLE
    # =========================================================

    assignments.sort(
        key=lambda row: (
            row["day"],
            row["period"],
            row["school_class_id"],
        )
    )

    # =========================================================
    # 17. RETURN RESULT
    # =========================================================

    return {
        "status": "completed",
        "solver_status": status_name,
        "duration": engine.WallTime(),
        "assignments": assignments,
    }