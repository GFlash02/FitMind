"""
个人助理 - 自动化任务脚本
由 OpenClaw cron 定时触发，通过 stdout 输出消息文本，
由芬达(agent)读取后通过飞书发送给用户。

用法:
  python automation.py <action>

动作:
  daily_plan       — 早8点：生成今日饮食+运动计划
  meal_inquiry     — 10/14/20点：主动问询对应餐次
  exercise_inquiry — 21点：运动问询
  daily_review     — 22点：每日复盘
  weekly_review    — 周日：周复盘
  monthly_review   — 每月1号：月复盘
  check_alerts     — 运行异常检测

所有输出为 JSON 格式:
  {"action": "...", "message": "要发送的文本", "skip": false, "reason": "..."}
"""

import sys
import os
import json
from datetime import date, datetime

# ── Windows 编码修复 ──────────────────────────────────────
os.environ['PYTHONUTF8'] = '1'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(__file__))
import core
import ai_engine


def output(data: dict):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def action_daily_plan():
    """生成今日计划（每天早上推送）"""
    if core.is_holiday_mode():
        output({"action": "daily_plan", "skip": True, "reason": "假期模式已开启", "message": "🌴 假期模式中～今天放松一下，不安排计划了。想记录随时告诉我哦！"})
        return

    context = core.get_full_context()
    plan = ai_engine.generate_daily_plan(context)
    output({"action": "daily_plan", "skip": False, "message": plan})


def action_meal_inquiry():
    """主动问询餐食（根据当前时间判断餐次）"""
    if core.is_holiday_mode():
        output({"action": "meal_inquiry", "skip": True, "reason": "假期模式"})
        return

    hour = datetime.now().hour
    if hour < 12:
        meal_type = "早餐"
    elif hour < 18:
        meal_type = "午餐"
    else:
        meal_type = "晚餐"

    # 检查该餐次是否已提交
    pending = core.get_pending_meals()
    if meal_type not in pending:
        output({"action": "meal_inquiry", "skip": True, "reason": f"{meal_type}已记录"})
        return

    # 获取问询次数
    tracking = core.get_meal_tracking()
    inquiry_count = 0
    for t in tracking:
        if t["meal_type"] == meal_type:
            inquiry_count = t["inquiry_count"]
            break

    # 超过2次不再追问
    if inquiry_count >= 2:
        output({"action": "meal_inquiry", "skip": True, "reason": f"{meal_type}已问询{inquiry_count}次"})
        return

    context = core.get_full_context()
    message = ai_engine.generate_meal_inquiry(meal_type, context, inquiry_count)
    core.mark_meal_inquired(meal_type)

    output({"action": "meal_inquiry", "skip": False, "meal_type": meal_type, "inquiry_count": inquiry_count + 1, "message": message})


def action_exercise_inquiry():
    """晚间运动问询"""
    if core.is_holiday_mode():
        output({"action": "exercise_inquiry", "skip": True, "reason": "假期模式"})
        return

    context = core.get_full_context()
    today_exercise = context["today"]["exercise"]

    if today_exercise["total_minutes"] > 0:
        # 今天已有运动记录，鼓励而非询问
        message = ai_engine.generate_exercise_inquiry(context)
        output({"action": "exercise_inquiry", "skip": False, "has_exercise": True, "message": message})
    else:
        message = ai_engine.generate_exercise_inquiry(context)
        output({"action": "exercise_inquiry", "skip": False, "has_exercise": False, "message": message})


def action_daily_review():
    """每日复盘"""
    context = core.get_full_context()
    # 也顺便运行异常检测
    anomalies = core.run_all_anomaly_checks()
    context["new_anomalies"] = anomalies

    review = ai_engine.generate_daily_review(context)

    # 如果有异常，附加在复盘后面
    if anomalies:
        alert_text = "\n\n⚠️ 健康提醒：\n"
        for a in anomalies:
            icon = "🔴" if a["severity"] == "warning" else "🟡"
            alert_text += f"{icon} {a['message']}\n"
        review += alert_text

    output({"action": "daily_review", "skip": False, "message": review, "anomalies": anomalies})


def action_weekly_review():
    """周复盘"""
    weekly_data = core.get_weekly_summary()
    context = core.get_full_context()
    review = ai_engine.generate_weekly_review(weekly_data, context)
    output({"action": "weekly_review", "skip": False, "message": review})


def action_monthly_review():
    """月复盘"""
    monthly_data = core.get_monthly_summary()
    context = core.get_full_context()
    review = ai_engine.generate_monthly_review(monthly_data, context)
    output({"action": "monthly_review", "skip": False, "message": review})


def action_check_alerts():
    """运行异常检测"""
    anomalies = core.run_all_anomaly_checks()
    if anomalies:
        alert_text = "⚠️ 健康异常提醒：\n\n"
        for a in anomalies:
            icon = "🔴" if a["severity"] == "warning" else "🟡"
            alert_text += f"{icon} {a['message']}\n"
        output({"action": "check_alerts", "skip": False, "anomalies": anomalies, "message": alert_text})
    else:
        output({"action": "check_alerts", "skip": True, "reason": "无异常"})


ACTIONS = {
    "daily_plan": action_daily_plan,
    "meal_inquiry": action_meal_inquiry,
    "exercise_inquiry": action_exercise_inquiry,
    "daily_review": action_daily_review,
    "weekly_review": action_weekly_review,
    "monthly_review": action_monthly_review,
    "check_alerts": action_check_alerts,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        output({
            "usage": "python automation.py <action>",
            "actions": list(ACTIONS.keys()),
        })
        return

    action_name = sys.argv[1]
    if action_name not in ACTIONS:
        output({"error": f"未知动作: {action_name}", "available": list(ACTIONS.keys())})
        sys.exit(1)

    ACTIONS[action_name]()


if __name__ == "__main__":
    main()
