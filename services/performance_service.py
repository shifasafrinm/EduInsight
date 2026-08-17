from statistics import mean


def _clamp(value, low=0, high=100):
    return max(low, min(high, value))


def predict_grade(student, attendance=None, study_hours=None):
    attendance = student.attendance_rate if attendance is None else float(attendance)
    study_hours = student.study_hours_per_week if study_hours is None else float(study_hours)
    support = {"Low": -2.2, "Medium": 0, "High": 2.4}.get(student.parental_support, 0)
    online = 1.3 if student.online_classes_taken else 0
    activities = min(student.extracurricular_activities or 0, 4) * 0.45
    prediction = (0.55 * (student.previous_grade or student.final_grade or 50)
                  + 0.24 * attendance + 0.52 * study_hours + support
                  + online + activities - 7.5)
    return round(_clamp(prediction), 1)


def recommendations(student):
    items = []
    attendance = student.attendance_rate or 0
    hours = student.study_hours_per_week or 0
    grade = student.final_grade or 0
    if attendance < 75:
        items.append({"title": "Rebuild attendance consistency", "detail": f"Raise attendance from {attendance:.0f}% toward 85%. Start with one reliable week and resolve missed-class patterns.", "impact": "High impact", "type": "attendance"})
    elif attendance < 88:
        items.append({"title": "Protect the attendance streak", "detail": "Aim for 90%+ next month and review notes within 24 hours of every class.", "impact": "Medium impact", "type": "attendance"})
    if hours < 12:
        target = max(12, round(hours + 4))
        items.append({"title": "Add focused study blocks", "detail": f"Move from {hours:.0f} to {target} hours per week using four distraction-free sessions.", "impact": "High impact", "type": "study"})
    elif hours < 18:
        items.append({"title": "Use active recall", "detail": "Turn two weekly sessions into practice questions and spaced review instead of rereading.", "impact": "Medium impact", "type": "study"})
    if student.parental_support == "Low":
        items.append({"title": "Create a support check-in", "detail": "Schedule a short weekly mentor or guardian update with one win and one next action.", "impact": "Medium impact", "type": "support"})
    if not student.online_classes_taken:
        items.append({"title": "Add one guided online lesson", "detail": "Use one targeted online class each week for the weakest topic, followed by a five-question check.", "impact": "Quick win", "type": "online"})
    if grade >= 85:
        items.append({"title": "Stretch with exam simulation", "detail": "Keep momentum with one timed paper each fortnight and an error log.", "impact": "Growth", "type": "stretch"})
    if not items:
        items.append({"title": "Sharpen with error analysis", "detail": "Keep an error log after each assessment and revisit the two most common mistake patterns every week.", "impact": "Growth", "type": "stretch"})
    return items[:3]


def student_insights(student, detailed=False):
    data = student.to_dict()
    predicted = predict_grade(student)
    optimistic = predict_grade(student, attendance=min(98, (student.attendance_rate or 0) + 10), study_hours=min(30, (student.study_hours_per_week or 0) + 5))
    risk = "high" if (student.final_grade or 0) < 60 or (student.attendance_rate or 0) < 70 else ("watch" if (student.final_grade or 0) < 75 else "strong")
    data.update({"predicted_grade": predicted, "potential_grade": optimistic, "potential_gain": round(max(0, optimistic - predicted), 1), "risk": risk, "recommendations": recommendations(student)})
    if detailed:
        current = student.final_grade or student.previous_grade or 0
        data["trajectory"] = [round(student.previous_grade or current, 1), round((student.previous_grade or current) * .45 + current * .55, 1), round(current, 1), predicted, optimistic]
    return data


def dashboard_summary(students):
    if not students:
        return {"students": 0, "average_grade": 0, "attendance": 0, "at_risk": 0, "projected_gain": 0, "grade_distribution": [], "attendance_bands": [], "top_movers": []}
    grades = [s.final_grade or 0 for s in students]
    attendance = [s.attendance_rate or 0 for s in students]
    at_risk = [s for s in students if (s.final_grade or 0) < 60 or (s.attendance_rate or 0) < 70]
    predictions = [predict_grade(s) for s in students]
    bands = [("0–49", 0, 50), ("50–59", 50, 60), ("60–69", 60, 70), ("70–79", 70, 80), ("80–89", 80, 90), ("90–100", 90, 101)]
    attendance_bands = [("<70%", 0, 70), ("70–79%", 70, 80), ("80–89%", 80, 90), ("90%+", 90, 101)]
    movers = sorted((student_insights(s) for s in students), key=lambda item: item["potential_gain"], reverse=True)[:5]
    return {
        "students": len(students), "average_grade": round(mean(grades), 1),
        "attendance": round(mean(attendance), 1), "at_risk": len(at_risk),
        "projected_gain": round(mean(predictions) - mean(grades), 1),
        "grade_distribution": [{"label": label, "value": sum(low <= g < high for g in grades)} for label, low, high in bands],
        "attendance_bands": [{"label": label, "value": sum(low <= a < high for a in attendance)} for label, low, high in attendance_bands],
        "top_movers": movers,
    }

