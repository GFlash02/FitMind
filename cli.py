"""
个人助理 CLI - OpenClaw 集成接口
芬达通过此 CLI 工具操作个人助理的所有功能。
输出 JSON 格式，方便 agent 解析。

用法:
  python cli.py <command> [args...]

命令:
  parse <message>                   — 智能解析自然语言消息并自动执行
  exercise <type> <min> <强度>      — 记录运动
  diet <餐次> <描述>                — 记录饮食
  weight <kg>                       — 记录体重
  schedule <自然语言>               — 添加日程
  schedules [--from DATE]           — 查看日程
  summary [--date DATE]             — 今日摘要
  weekly                            — 周报摘要
  monthly [--year Y --month M]      — 月报
  advice                            — 获取 AI 建议
  goal [<json>]                     — 查看/设定健康目标
  status                            — 系统状态
  profile [<json>]                  — 查看/设定用户画像
  rules [<key> <value>]             — 查看/修改时间规则
  holiday <on|off>                  — 开关假期模式
  plan                              — 立即生成今日计划
  review [daily|weekly|monthly]     — 立即生成复盘
  alerts [--ack <id>]               — 查看/确认预警
  meals                             — 查看今日各餐跟踪状态

所有输出均为 JSON 格式。
"""

import sys
import os
import json
from datetime import date

# ── Windows 编码修复 ──────────────────────────────────────
os.environ['PYTHONUTF8'] = '1'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 确保可以 import 同目录下的模块
sys.path.insert(0, os.path.dirname(__file__))

import core
import ai_engine


def output(data: dict):
    """统一输出 JSON"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_parse(args: list[str]):
    """智能解析用户自然语言消息，自动执行对应操作"""
    message = " ".join(args)
    if not message:
        output({"error": "请提供消息内容"})
        return

    parsed = ai_engine.smart_parse_feishu_message(message)
    intent = parsed.get("intent", "general_chat")
    data = parsed.get("data", {})
    reply_hint = parsed.get("reply_hint", "")

    result = {"intent": intent, "parsed_data": data, "reply_hint": reply_hint}

    # 自动执行对应操作
    if intent == "record_exercise":
        exercise_result = ai_engine.analyze_exercise(
            data.get("exercise_type", "运动"),
            data.get("duration_min", 30),
            data.get("intensity", "中"),
        )
        row_id = core.add_exercise(
            exercise_type=data.get("exercise_type", "运动"),
            duration_min=data.get("duration_min", 30),
            intensity=data.get("intensity", "中"),
            calories_burned=exercise_result.get("calories_burned", 0),
            notes=data.get("notes", ""),
            log_date=data.get("log_date"),
        )
        result["action"] = "exercise_recorded"
        result["record_id"] = row_id
        result["calories_burned"] = exercise_result.get("calories_burned", 0)
        result["tips"] = exercise_result.get("tips", "")

    elif intent == "record_diet":
        exercise_cal = core.get_today_exercise_calories(data.get("log_date"))
        diet_result = ai_engine.analyze_diet(
            data.get("meal_type", "餐食"),
            data.get("description", ""),
            exercise_cal,
        )
        row_id = core.add_diet(
            meal_type=data.get("meal_type", "餐食"),
            description=data.get("description", ""),
            calories_est=diet_result.get("calories", 0),
            protein_g=diet_result.get("protein_g", 0),
            carbs_g=diet_result.get("carbs_g", 0),
            fat_g=diet_result.get("fat_g", 0),
            ai_advice=diet_result.get("advice", ""),
            log_date=data.get("log_date"),
        )
        result["action"] = "diet_recorded"
        result["record_id"] = row_id
        result["nutrition"] = diet_result

    elif intent == "record_weight":
        row_id = core.add_weight(
            weight_kg=data.get("weight_kg", 0),
            log_date=data.get("log_date"),
        )
        result["action"] = "weight_recorded"
        result["record_id"] = row_id

    elif intent == "add_schedule":
        row_id = core.add_schedule(
            title=data.get("title", ""),
            event_date=data.get("event_date", date.today().isoformat()),
            event_time=data.get("event_time", ""),
            location=data.get("location", ""),
            reminder=data.get("reminder", ""),
        )
        result["action"] = "schedule_added"
        result["record_id"] = row_id

    elif intent == "query_summary":
        summary = core.get_daily_summary(data.get("target_date"))
        result["action"] = "summary_retrieved"
        result["summary"] = summary

    elif intent == "query_weekly":
        weekly = core.get_weekly_summary()
        result["action"] = "weekly_retrieved"
        result["weekly"] = weekly

    elif intent == "set_goal":
        row_id = core.set_health_goal(**data)
        plan = ai_engine.generate_health_plan(**data)
        result["action"] = "goal_set"
        result["record_id"] = row_id
        result["plan"] = plan

    elif intent == "update_profile":
        row_id = core.set_user_profile(**data)
        result["action"] = "profile_updated"
        result["record_id"] = row_id

    elif intent == "set_rules":
        key = data.get("rule_key", "")
        val = data.get("rule_value", "")
        if key and val:
            core.set_time_rule(key, val)
            result["action"] = "rule_updated"
        else:
            result["action"] = "no_auto_action"

    elif intent == "meal_reply":
        # 用户回复了餐食问询 → 自动记录饮食
        exercise_cal = core.get_today_exercise_calories(data.get("log_date"))
        diet_result = ai_engine.analyze_diet(
            data.get("meal_type", "餐食"),
            data.get("description", ""),
            exercise_cal,
        )
        row_id = core.add_diet(
            meal_type=data.get("meal_type", "餐食"),
            description=data.get("description", ""),
            calories_est=diet_result.get("calories", 0),
            protein_g=diet_result.get("protein_g", 0),
            carbs_g=diet_result.get("carbs_g", 0),
            fat_g=diet_result.get("fat_g", 0),
            ai_advice=diet_result.get("advice", ""),
            log_date=data.get("log_date"),
        )
        result["action"] = "diet_recorded"
        result["record_id"] = row_id
        result["nutrition"] = diet_result

    elif intent == "exercise_reply":
        if data.get("skipped"):
            result["action"] = "exercise_skipped"
            result["reason"] = data.get("reason", "")
        else:
            analysis = ai_engine.analyze_exercise(
                data.get("exercise_type", "运动"),
                data.get("duration_min", 30),
                data.get("intensity", "中"),
            )
            row_id = core.add_exercise(
                exercise_type=data.get("exercise_type", "运动"),
                duration_min=data.get("duration_min", 30),
                intensity=data.get("intensity", "中"),
                calories_burned=analysis.get("calories_burned", 0),
                notes=data.get("notes", ""),
                log_date=data.get("log_date"),
            )
            result["action"] = "exercise_recorded"
            result["record_id"] = row_id
            result["calories_burned"] = analysis.get("calories_burned", 0)
            result["tips"] = analysis.get("tips", "")

    else:
        result["action"] = "no_auto_action"

    output(result)


def cmd_exercise(args: list[str]):
    """记录运动: exercise <类型> <分钟> <强度> [备注]"""
    if len(args) < 3:
        output({"error": "用法: exercise <类型> <分钟> <强度> [备注]"})
        return

    exercise_type = args[0]
    duration_min = int(args[1])
    intensity = args[2]
    notes = " ".join(args[3:]) if len(args) > 3 else ""

    analysis = ai_engine.analyze_exercise(exercise_type, duration_min, intensity)
    row_id = core.add_exercise(
        exercise_type=exercise_type,
        duration_min=duration_min,
        intensity=intensity,
        calories_burned=analysis.get("calories_burned", 0),
        notes=notes,
    )

    output({
        "action": "exercise_recorded",
        "id": row_id,
        "exercise_type": exercise_type,
        "duration_min": duration_min,
        "intensity": intensity,
        "calories_burned": analysis.get("calories_burned", 0),
        "tips": analysis.get("tips", ""),
    })


def cmd_diet(args: list[str]):
    """记录饮食: diet <餐次> <描述>"""
    if len(args) < 2:
        output({"error": "用法: diet <餐次> <描述>"})
        return

    meal_type = args[0]
    description = " ".join(args[1:])
    exercise_cal = core.get_today_exercise_calories()
    analysis = ai_engine.analyze_diet(meal_type, description, exercise_cal)

    row_id = core.add_diet(
        meal_type=meal_type,
        description=description,
        calories_est=analysis.get("calories", 0),
        protein_g=analysis.get("protein_g", 0),
        carbs_g=analysis.get("carbs_g", 0),
        fat_g=analysis.get("fat_g", 0),
        ai_advice=analysis.get("advice", ""),
    )

    today_total = core.get_today_diet_calories()
    output({
        "action": "diet_recorded",
        "id": row_id,
        "meal_type": meal_type,
        "nutrition": analysis,
        "today_total_calories": today_total,
        "today_exercise_calories": exercise_cal,
        "today_net_calories": today_total - exercise_cal,
    })


def cmd_weight(args: list[str]):
    """记录体重: weight <kg>"""
    if len(args) < 1:
        output({"error": "用法: weight <kg>"})
        return

    weight_kg = float(args[0])
    row_id = core.add_weight(weight_kg)
    goal = core.get_health_goal()

    result = {
        "action": "weight_recorded",
        "id": row_id,
        "weight_kg": weight_kg,
        "date": date.today().isoformat(),
    }
    if goal:
        diff = weight_kg - goal["target_weight"]
        result["target_weight"] = goal["target_weight"]
        result["distance_to_goal"] = round(abs(diff), 1)
        result["direction"] = "还需减" if diff > 0 else "已低于目标"

    output(result)


def cmd_schedule(args: list[str]):
    """添加日程: schedule <自然语言>"""
    text = " ".join(args)
    if not text:
        output({"error": "请描述日程内容"})
        return

    parsed = ai_engine.analyze_schedule(text)
    row_id = core.add_schedule(
        title=parsed.get("title", ""),
        event_date=parsed.get("event_date", date.today().isoformat()),
        event_time=parsed.get("event_time", ""),
        location=parsed.get("location", ""),
        reminder=parsed.get("reminder", ""),
    )

    output({
        "action": "schedule_added",
        "id": row_id,
        **parsed,
    })


def cmd_schedules(args: list[str]):
    """查看日程: schedules [--from DATE]"""
    from_date = None
    if "--from" in args:
        idx = args.index("--from")
        if idx + 1 < len(args):
            from_date = args[idx + 1]
    if not from_date:
        from_date = date.today().isoformat()

    schedules = core.list_schedules(from_date=from_date)
    output({"schedules": schedules, "count": len(schedules)})


def cmd_summary(args: list[str]):
    """今日摘要: summary [--date DATE]"""
    target_date = None
    if "--date" in args:
        idx = args.index("--date")
        if idx + 1 < len(args):
            target_date = args[idx + 1]

    summary = core.get_daily_summary(target_date)
    output(summary)


def cmd_weekly(args: list[str]):
    """周报: weekly"""
    weekly = core.get_weekly_summary()
    output(weekly)


def cmd_advice(args: list[str]):
    """获取今日 AI 建议: advice"""
    summary = core.get_daily_summary()
    advice = ai_engine.generate_daily_advice(summary)
    output({
        "date": summary["date"],
        "summary": summary,
        "advice": advice,
    })


def cmd_goal(args: list[str]):
    """设定健康目标: goal <json>"""
    if not args:
        goal = core.get_health_goal()
        if goal:
            output({"current_goal": goal})
        else:
            output({"message": "未设定健康目标"})
        return

    data = json.loads(" ".join(args))
    row_id = core.set_health_goal(**data)
    plan = ai_engine.generate_health_plan(**data)
    output({"action": "goal_set", "id": row_id, "plan": plan})


def cmd_status(args: list[str]):
    """系统状态"""
    goal = core.get_health_goal()
    weight = core.get_latest_weight()
    exercise_stats = core.get_exercise_stats(days=7)
    today_intake = core.get_today_diet_calories()
    today_burned = core.get_today_exercise_calories()
    profile = core.get_user_profile()
    holiday = core.is_holiday_mode()
    pending_meals = core.get_pending_meals()
    alerts = core.get_unacknowledged_alerts(days=3)

    output({
        "status": "ok",
        "db_path": core.DB_PATH,
        "today": date.today().isoformat(),
        "latest_weight": weight,
        "health_goal": goal,
        "profile": profile,
        "holiday_mode": holiday,
        "today_intake_cal": today_intake,
        "today_burned_cal": today_burned,
        "today_net_cal": today_intake - today_burned,
        "exercise_7d_stats": exercise_stats,
        "pending_meals": pending_meals,
        "unacknowledged_alerts": len(alerts),
    })


def cmd_profile(args: list[str]):
    """查看/设定用户画像: profile [<json>]"""
    if not args:
        profile = core.get_user_profile()
        if profile:
            output({"profile": profile})
        else:
            output({"message": "未设定用户画像。用法: profile '{\"height_cm\":175, \"dietary_restrictions\":\"低糖\", \"food_allergies\":\"海鲜\"...}'"})
        return

    data = json.loads(" ".join(args))
    row_id = core.set_user_profile(**data)
    output({"action": "profile_updated", "id": row_id, "profile": data})


def cmd_rules(args: list[str]):
    """查看/修改时间规则: rules [<key> <value>]"""
    if not args:
        rules = core.get_all_time_rules()
        output({"rules": rules})
        return

    if len(args) < 2:
        val = core.get_time_rule(args[0])
        if val is not None:
            output({"rule_key": args[0], "rule_value": val})
        else:
            output({"error": f"不存在的规则: {args[0]}"})
        return

    key, value = args[0], args[1]
    ok = core.set_time_rule(key, value)
    if ok:
        output({"action": "rule_updated", "rule_key": key, "rule_value": value})
    else:
        output({"error": f"不存在的规则: {key}"})


def cmd_holiday(args: list[str]):
    """假期模式: holiday <on|off>"""
    if not args:
        mode = core.get_time_rule("holiday_mode")
        output({"holiday_mode": mode})
        return

    value = args[0].lower()
    if value not in ("on", "off"):
        output({"error": "用法: holiday <on|off>"})
        return

    core.set_time_rule("holiday_mode", value)
    output({"action": "holiday_mode_set", "holiday_mode": value})


def cmd_plan(args: list[str]):
    """立即生成今日计划: plan"""
    context = core.get_full_context()
    plan = ai_engine.generate_daily_plan(context)
    output({"action": "daily_plan", "message": plan})


def cmd_review(args: list[str]):
    """生成复盘: review [daily|weekly|monthly]"""
    review_type = args[0] if args else "daily"

    context = core.get_full_context()

    if review_type == "daily":
        anomalies = core.run_all_anomaly_checks()
        context["new_anomalies"] = anomalies
        review = ai_engine.generate_daily_review(context)
        output({"action": "daily_review", "message": review, "anomalies": anomalies})

    elif review_type == "weekly":
        weekly_data = core.get_weekly_summary()
        review = ai_engine.generate_weekly_review(weekly_data, context)
        output({"action": "weekly_review", "message": review})

    elif review_type == "monthly":
        monthly_data = core.get_monthly_summary()
        review = ai_engine.generate_monthly_review(monthly_data, context)
        output({"action": "monthly_review", "message": review})

    else:
        output({"error": "用法: review [daily|weekly|monthly]"})


def cmd_alerts(args: list[str]):
    """查看/确认预警: alerts [--ack <id>]"""
    if "--ack" in args:
        idx = args.index("--ack")
        if idx + 1 < len(args):
            alert_id = int(args[idx + 1])
            core.acknowledge_alert(alert_id)
            output({"action": "alert_acknowledged", "id": alert_id})
            return

    alerts = core.get_unacknowledged_alerts()
    output({"alerts": alerts, "count": len(alerts)})


def cmd_meals(args: list[str]):
    """查看今日各餐跟踪状态: meals"""
    tracking = core.get_meal_tracking()
    pending = core.get_pending_meals()
    output({"tracking": tracking, "pending_meals": pending})


def cmd_monthly(args: list[str]):
    """月报: monthly [--year Y --month M]"""
    year = month = 0
    if "--year" in args:
        idx = args.index("--year")
        if idx + 1 < len(args):
            year = int(args[idx + 1])
    if "--month" in args:
        idx = args.index("--month")
        if idx + 1 < len(args):
            month = int(args[idx + 1])

    monthly = core.get_monthly_summary(year, month)
    output(monthly)


COMMANDS = {
    "parse": cmd_parse,
    "exercise": cmd_exercise,
    "diet": cmd_diet,
    "weight": cmd_weight,
    "schedule": cmd_schedule,
    "schedules": cmd_schedules,
    "summary": cmd_summary,
    "weekly": cmd_weekly,
    "monthly": cmd_monthly,
    "advice": cmd_advice,
    "goal": cmd_goal,
    "status": cmd_status,
    "profile": cmd_profile,
    "rules": cmd_rules,
    "holiday": cmd_holiday,
    "plan": cmd_plan,
    "review": cmd_review,
    "alerts": cmd_alerts,
    "meals": cmd_meals,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        output({
            "usage": "python cli.py <command> [args...]",
            "commands": {
                "parse <message>": "智能解析自然语言消息并自动执行",
                "exercise <类型> <分钟> <强度> [备注]": "记录运动",
                "diet <餐次> <描述>": "记录饮食",
                "weight <kg>": "记录体重",
                "schedule <自然语言>": "添加日程",
                "schedules [--from DATE]": "查看日程",
                "summary [--date DATE]": "今日/某日数据摘要",
                "weekly": "近7天周报",
                "monthly [--year Y --month M]": "月报",
                "advice": "获取 AI 每日建议",
                "goal [<json>]": "查看/设定健康目标",
                "status": "系统状态",
                "profile [<json>]": "查看/设定用户画像",
                "rules [<key> <value>]": "查看/修改时间规则",
                "holiday <on|off>": "开关假期模式",
                "plan": "立即生成今日计划",
                "review [daily|weekly|monthly]": "生成复盘",
                "alerts [--ack <id>]": "查看/确认预警",
                "meals": "查看今日各餐跟踪状态",
            },
            "stdin_mode": "echo '{\"command\":\"parse\",\"args\":[\"中文消息\"]}' | python cli.py --stdin",
        })
        return

    # --stdin 模式：从 stdin 读取 JSON，彻底避免 Windows 命令行编码问题
    if sys.argv[1] == "--stdin":
        import io
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8-sig')
        payload = json.loads(sys.stdin.read())
        cmd_name = payload.get("command", "")
        cmd_args = payload.get("args", [])
        if cmd_name not in COMMANDS:
            output({"error": f"未知命令: {cmd_name}", "available": list(COMMANDS.keys())})
            sys.exit(1)
        COMMANDS[cmd_name](cmd_args)
        return

    cmd_name = sys.argv[1]
    cmd_args = sys.argv[2:]

    if cmd_name not in COMMANDS:
        output({"error": f"未知命令: {cmd_name}", "available": list(COMMANDS.keys())})
        sys.exit(1)

    COMMANDS[cmd_name](cmd_args)


if __name__ == "__main__":
    main()
