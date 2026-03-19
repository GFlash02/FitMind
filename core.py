"""
个人助理 - 核心数据层
所有数据库操作和业务逻辑集中在此模块，供 Streamlit UI 和 CLI 共同使用。
"""

import os
import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Optional

# ── 数据库路径（统一使用 assistant 目录下的 db）────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "assistant_data.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化所有表结构"""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        event_date TEXT NOT NULL,
        event_time TEXT,
        location TEXT,
        reminder TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS exercise_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        exercise_type TEXT NOT NULL,
        duration_min INTEGER NOT NULL,
        intensity TEXT NOT NULL,
        calories_burned INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS diet_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        meal_type TEXT NOT NULL,
        description TEXT NOT NULL,
        calories_est INTEGER,
        protein_g REAL,
        carbs_g REAL,
        fat_g REAL,
        ai_advice TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS weight_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        weight_kg REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS health_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        current_weight REAL,
        target_weight REAL,
        height_cm REAL,
        age INTEGER,
        gender TEXT,
        weeks_target INTEGER,
        activity_level TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── 新增：用户画像 ──────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        height_cm REAL,
        body_fat_pct REAL,
        dietary_restrictions TEXT DEFAULT '',
        food_allergies TEXT DEFAULT '',
        exercise_restrictions TEXT DEFAULT '',
        vitamin_deficiencies TEXT DEFAULT '',
        preferences TEXT DEFAULT '{}',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── 新增：时间规则（可自定义各项提醒时间）──────────
    c.execute("""CREATE TABLE IF NOT EXISTS time_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_key TEXT UNIQUE NOT NULL,
        rule_value TEXT NOT NULL,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── 新增：每餐跟踪状态（用于主动问询逻辑）─────────
    c.execute("""CREATE TABLE IF NOT EXISTS meal_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_date TEXT NOT NULL,
        meal_type TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        inquiry_count INTEGER DEFAULT 0,
        last_inquiry_at TEXT,
        submitted_at TEXT,
        UNIQUE(track_date, meal_type)
    )""")

    # ── 新增：异常预警记录 ──────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_date TEXT NOT NULL,
        alert_type TEXT NOT NULL,
        severity TEXT DEFAULT 'info',
        message TEXT NOT NULL,
        acknowledged INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── 插入默认时间规则（仅在首次初始化时）────────────
    default_rules = [
        ("plan_push_time", "08:00", "每日计划推送时间"),
        ("breakfast_inquiry_time", "10:00", "早餐问询时间"),
        ("lunch_inquiry_time", "14:00", "午餐问询时间"),
        ("dinner_inquiry_time", "20:00", "晚餐问询时间"),
        ("exercise_inquiry_time", "21:00", "运动问询时间"),
        ("daily_review_time", "22:00", "每日复盘推送时间"),
        ("weekly_review_day", "0", "周复盘日（0=周日，1=周一...）"),
        ("inquiry_delay_min", "30", "问询未回复后的二次提醒间隔（分钟）"),
        ("holiday_mode", "off", "假期模式（on/off）"),
    ]
    for key, val, desc in default_rules:
        c.execute(
            "INSERT OR IGNORE INTO time_rules (rule_key, rule_value, description) VALUES (?,?,?)",
            (key, val, desc),
        )

    conn.commit()
    conn.close()


# ── 日程管理 ──────────────────────────────────────────────

def add_schedule(title: str, event_date: str, event_time: str = "",
                 location: str = "", reminder: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO schedules (title, event_date, event_time, location, reminder) VALUES (?,?,?,?,?)",
        (title, event_date, event_time, location, reminder)
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def list_schedules(from_date: Optional[str] = None, limit: int = 20) -> list[dict]:
    conn = get_conn()
    if from_date:
        rows = conn.execute(
            "SELECT id, title, event_date, event_time, location, reminder FROM schedules WHERE event_date >= ? ORDER BY event_date, event_time LIMIT ?",
            (from_date, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, event_date, event_time, location, reminder FROM schedules ORDER BY event_date, event_time LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_schedule(schedule_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def get_today_schedules() -> list[dict]:
    return list_schedules(from_date=date.today().isoformat())


# ── 运动记录 ──────────────────────────────────────────────

def add_exercise(exercise_type: str, duration_min: int, intensity: str,
                 calories_burned: int = 0, notes: str = "",
                 log_date: Optional[str] = None) -> int:
    if not log_date:
        log_date = date.today().isoformat()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO exercise_logs (log_date, exercise_type, duration_min, intensity, calories_burned, notes) VALUES (?,?,?,?,?,?)",
        (log_date, exercise_type, duration_min, intensity, calories_burned, notes)
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def list_exercises(days: int = 7) -> list[dict]:
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, log_date, exercise_type, duration_min, intensity, calories_burned, notes FROM exercise_logs WHERE log_date >= ? ORDER BY log_date DESC",
        (since,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_exercise_stats(days: int = 30) -> dict:
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as count, COALESCE(SUM(duration_min),0) as total_min, COALESCE(SUM(calories_burned),0) as total_cal FROM exercise_logs WHERE log_date >= ?",
        (since,)
    ).fetchone()
    conn.close()
    return dict(row)


def get_today_exercise_calories(log_date: Optional[str] = None) -> int:
    if not log_date:
        log_date = date.today().isoformat()
    conn = get_conn()
    val = conn.execute(
        "SELECT COALESCE(SUM(calories_burned),0) FROM exercise_logs WHERE log_date=?",
        (log_date,)
    ).fetchone()[0]
    conn.close()
    return val


# ── 饮食记录 ──────────────────────────────────────────────

def add_diet(meal_type: str, description: str, calories_est: int = 0,
             protein_g: float = 0, carbs_g: float = 0, fat_g: float = 0,
             ai_advice: str = "", log_date: Optional[str] = None) -> int:
    if not log_date:
        log_date = date.today().isoformat()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO diet_logs (log_date, meal_type, description, calories_est, protein_g, carbs_g, fat_g, ai_advice) VALUES (?,?,?,?,?,?,?,?)",
        (log_date, meal_type, description, calories_est, protein_g, carbs_g, fat_g, ai_advice)
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    # 自动标记该餐次为已提交
    mark_meal_submitted(meal_type, log_date)
    return row_id


def list_diets(days: int = 7) -> list[dict]:
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, log_date, meal_type, description, calories_est, protein_g, carbs_g, fat_g, ai_advice FROM diet_logs WHERE log_date >= ? ORDER BY log_date DESC, meal_type",
        (since,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_today_diet_calories(log_date: Optional[str] = None) -> int:
    if not log_date:
        log_date = date.today().isoformat()
    conn = get_conn()
    val = conn.execute(
        "SELECT COALESCE(SUM(calories_est),0) FROM diet_logs WHERE log_date=?",
        (log_date,)
    ).fetchone()[0]
    conn.close()
    return val


# ── 体重记录 ──────────────────────────────────────────────

def add_weight(weight_kg: float, log_date: Optional[str] = None) -> int:
    if not log_date:
        log_date = date.today().isoformat()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO weight_logs (log_date, weight_kg) VALUES (?,?)",
        (log_date, weight_kg)
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def list_weights(days: int = 30) -> list[dict]:
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, log_date, weight_kg FROM weight_logs WHERE log_date >= ? ORDER BY log_date",
        (since,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_weight() -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT log_date, weight_kg FROM weight_logs ORDER BY log_date DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── 健康目标 ──────────────────────────────────────────────

def set_health_goal(current_weight: float, target_weight: float,
                    height_cm: float, age: int, gender: str,
                    weeks_target: int, activity_level: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO health_goals (current_weight, target_weight, height_cm, age, gender, weeks_target, activity_level, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (current_weight, target_weight, height_cm, age, gender, weeks_target, activity_level, datetime.now().isoformat())
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_health_goal() -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM health_goals ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


# ── 综合查询 ──────────────────────────────────────────────

def get_daily_summary(target_date: Optional[str] = None) -> dict:
    """获取指定日期的综合数据摘要"""
    if not target_date:
        target_date = date.today().isoformat()

    conn = get_conn()

    # 今日饮食
    diet_intake = conn.execute(
        "SELECT COALESCE(SUM(calories_est),0) as cal, COALESCE(SUM(protein_g),0) as protein, "
        "COALESCE(SUM(carbs_g),0) as carbs, COALESCE(SUM(fat_g),0) as fat FROM diet_logs WHERE log_date=?",
        (target_date,)
    ).fetchone()

    diet_items = conn.execute(
        "SELECT meal_type, description, calories_est FROM diet_logs WHERE log_date=? ORDER BY meal_type",
        (target_date,)
    ).fetchall()

    # 今日运动
    exercise_burned = conn.execute(
        "SELECT COALESCE(SUM(calories_burned),0) as cal, COALESCE(SUM(duration_min),0) as min FROM exercise_logs WHERE log_date=?",
        (target_date,)
    ).fetchone()

    exercise_items = conn.execute(
        "SELECT exercise_type, duration_min, intensity, calories_burned FROM exercise_logs WHERE log_date=?",
        (target_date,)
    ).fetchall()

    # 今日日程
    schedules = conn.execute(
        "SELECT title, event_time, location FROM schedules WHERE event_date=? ORDER BY event_time",
        (target_date,)
    ).fetchall()

    # 最近体重
    weight = conn.execute(
        "SELECT weight_kg FROM weight_logs ORDER BY log_date DESC LIMIT 1"
    ).fetchone()

    # 健康目标
    goal = conn.execute(
        "SELECT target_weight, current_weight FROM health_goals ORDER BY id DESC LIMIT 1"
    ).fetchone()

    conn.close()

    intake_cal = diet_intake["cal"]
    burned_cal = exercise_burned["cal"]

    return {
        "date": target_date,
        "diet": {
            "total_calories": intake_cal,
            "total_protein_g": round(diet_intake["protein"], 1),
            "total_carbs_g": round(diet_intake["carbs"], 1),
            "total_fat_g": round(diet_intake["fat"], 1),
            "meals": [dict(r) for r in diet_items],
        },
        "exercise": {
            "total_calories_burned": burned_cal,
            "total_minutes": exercise_burned["min"],
            "sessions": [dict(r) for r in exercise_items],
        },
        "calorie_balance": intake_cal - burned_cal,
        "schedules": [dict(r) for r in schedules],
        "latest_weight_kg": weight["weight_kg"] if weight else None,
        "goal_weight_kg": goal["target_weight"] if goal else None,
    }


def get_weekly_summary() -> dict:
    """获取近7天汇总数据"""
    conn = get_conn()
    since = (date.today() - timedelta(days=7)).isoformat()

    diet_sum = conn.execute(
        "SELECT COALESCE(SUM(calories_est),0) as cal, COUNT(*) as meals FROM diet_logs WHERE log_date >= ?",
        (since,)
    ).fetchone()

    exercise_sum = conn.execute(
        "SELECT COALESCE(SUM(calories_burned),0) as cal, COALESCE(SUM(duration_min),0) as min, COUNT(*) as sessions FROM exercise_logs WHERE log_date >= ?",
        (since,)
    ).fetchone()

    # 每日明细
    daily_intake = conn.execute(
        "SELECT log_date, SUM(calories_est) as cal FROM diet_logs WHERE log_date >= ? GROUP BY log_date ORDER BY log_date",
        (since,)
    ).fetchall()

    daily_burn = conn.execute(
        "SELECT log_date, SUM(calories_burned) as cal FROM exercise_logs WHERE log_date >= ? GROUP BY log_date ORDER BY log_date",
        (since,)
    ).fetchall()

    conn.close()

    return {
        "period": f"{since} ~ {date.today().isoformat()}",
        "diet_total_cal": diet_sum["cal"],
        "diet_avg_cal_per_day": round(diet_sum["cal"] / 7),
        "diet_meal_count": diet_sum["meals"],
        "exercise_total_cal": exercise_sum["cal"],
        "exercise_total_min": exercise_sum["min"],
        "exercise_session_count": exercise_sum["sessions"],
        "net_calories": diet_sum["cal"] - exercise_sum["cal"],
        "daily_intake": [dict(r) for r in daily_intake],
        "daily_burn": [dict(r) for r in daily_burn],
    }


# ── 用户画像管理 ──────────────────────────────────────────

def set_user_profile(height_cm: float = None, body_fat_pct: float = None,
                     dietary_restrictions: str = None, food_allergies: str = None,
                     exercise_restrictions: str = None, vitamin_deficiencies: str = None,
                     preferences: str = None) -> int:
    """更新用户画像。只更新传入的非 None 字段，其余保留原值。"""
    conn = get_conn()
    existing = conn.execute("SELECT * FROM user_profile LIMIT 1").fetchone()
    if existing:
        old = dict(existing)
        new_vals = {
            "height_cm": height_cm if height_cm is not None else old["height_cm"],
            "body_fat_pct": body_fat_pct if body_fat_pct is not None else old["body_fat_pct"],
            "dietary_restrictions": dietary_restrictions if dietary_restrictions is not None else old["dietary_restrictions"],
            "food_allergies": food_allergies if food_allergies is not None else old["food_allergies"],
            "exercise_restrictions": exercise_restrictions if exercise_restrictions is not None else old["exercise_restrictions"],
            "vitamin_deficiencies": vitamin_deficiencies if vitamin_deficiencies is not None else old["vitamin_deficiencies"],
            "preferences": preferences if preferences is not None else old["preferences"],
        }
        conn.execute(
            """UPDATE user_profile SET height_cm=?, body_fat_pct=?, dietary_restrictions=?,
               food_allergies=?, exercise_restrictions=?, vitamin_deficiencies=?,
               preferences=?, updated_at=? WHERE id=?""",
            (new_vals["height_cm"], new_vals["body_fat_pct"], new_vals["dietary_restrictions"],
             new_vals["food_allergies"], new_vals["exercise_restrictions"],
             new_vals["vitamin_deficiencies"], new_vals["preferences"],
             datetime.now().isoformat(), old["id"])
        )
        row_id = old["id"]
    else:
        cur = conn.execute(
            """INSERT INTO user_profile (height_cm, body_fat_pct, dietary_restrictions,
               food_allergies, exercise_restrictions, vitamin_deficiencies, preferences)
               VALUES (?,?,?,?,?,?,?)""",
            (height_cm or 0, body_fat_pct or 0, dietary_restrictions or "",
             food_allergies or "", exercise_restrictions or "",
             vitamin_deficiencies or "", preferences or "{}")
        )
        row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_user_profile() -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


# ── 时间规则管理 ──────────────────────────────────────────

def get_time_rule(rule_key: str) -> Optional[str]:
    conn = get_conn()
    row = conn.execute("SELECT rule_value FROM time_rules WHERE rule_key=?", (rule_key,)).fetchone()
    conn.close()
    return row["rule_value"] if row else None


def set_time_rule(rule_key: str, rule_value: str) -> bool:
    conn = get_conn()
    cur = conn.execute(
        "UPDATE time_rules SET rule_value=?, updated_at=? WHERE rule_key=?",
        (rule_value, datetime.now().isoformat(), rule_key)
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def get_all_time_rules() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT rule_key, rule_value, description FROM time_rules ORDER BY rule_key").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_holiday_mode() -> bool:
    return get_time_rule("holiday_mode") == "on"


# ── 每餐跟踪（主动问询逻辑）─────────────────────────────

def ensure_meal_tracking(track_date: Optional[str] = None):
    """确保当天的三餐跟踪记录已创建"""
    if not track_date:
        track_date = date.today().isoformat()
    conn = get_conn()
    for meal in ["早餐", "午餐", "晚餐"]:
        conn.execute(
            "INSERT OR IGNORE INTO meal_tracking (track_date, meal_type) VALUES (?,?)",
            (track_date, meal)
        )
    conn.commit()
    conn.close()


def get_meal_tracking(track_date: Optional[str] = None) -> list[dict]:
    if not track_date:
        track_date = date.today().isoformat()
    ensure_meal_tracking(track_date)
    conn = get_conn()
    rows = conn.execute(
        "SELECT meal_type, status, inquiry_count, last_inquiry_at, submitted_at FROM meal_tracking WHERE track_date=? ORDER BY meal_type",
        (track_date,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_meal_submitted(meal_type: str, track_date: Optional[str] = None):
    if not track_date:
        track_date = date.today().isoformat()
    ensure_meal_tracking(track_date)
    conn = get_conn()
    conn.execute(
        "UPDATE meal_tracking SET status='submitted', submitted_at=? WHERE track_date=? AND meal_type=?",
        (datetime.now().isoformat(), track_date, meal_type)
    )
    conn.commit()
    conn.close()


def mark_meal_inquired(meal_type: str, track_date: Optional[str] = None):
    if not track_date:
        track_date = date.today().isoformat()
    ensure_meal_tracking(track_date)
    conn = get_conn()
    conn.execute(
        """UPDATE meal_tracking SET inquiry_count = inquiry_count + 1,
           last_inquiry_at=? WHERE track_date=? AND meal_type=? AND status='pending'""",
        (datetime.now().isoformat(), track_date, meal_type)
    )
    conn.commit()
    conn.close()


def get_pending_meals(track_date: Optional[str] = None) -> list[str]:
    """获取当天还没有提交的餐次"""
    if not track_date:
        track_date = date.today().isoformat()
    ensure_meal_tracking(track_date)
    conn = get_conn()
    rows = conn.execute(
        "SELECT meal_type FROM meal_tracking WHERE track_date=? AND status='pending'",
        (track_date,)
    ).fetchall()
    conn.close()
    return [r["meal_type"] for r in rows]


# ── 异常预警 ──────────────────────────────────────────────

def add_alert(alert_type: str, message: str, severity: str = "info",
              alert_date: Optional[str] = None) -> int:
    if not alert_date:
        alert_date = date.today().isoformat()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO alerts (alert_date, alert_type, severity, message) VALUES (?,?,?,?)",
        (alert_date, alert_type, severity, message)
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_unacknowledged_alerts(days: int = 7) -> list[dict]:
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, alert_date, alert_type, severity, message FROM alerts WHERE acknowledged=0 AND alert_date >= ? ORDER BY created_at DESC",
        (since,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def acknowledge_alert(alert_id: int):
    conn = get_conn()
    conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()


# ── 异常检测查询 ──────────────────────────────────────────

def check_weight_anomaly(threshold_kg: float = 1.0) -> Optional[dict]:
    """检测最近两次体重变化是否异常"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT log_date, weight_kg FROM weight_logs ORDER BY log_date DESC LIMIT 2"
    ).fetchall()
    conn.close()
    if len(rows) < 2:
        return None
    diff = rows[0]["weight_kg"] - rows[1]["weight_kg"]
    if abs(diff) >= threshold_kg:
        direction = "增加" if diff > 0 else "减少"
        return {
            "type": "weight_fluctuation",
            "severity": "warning",
            "message": f"体重{direction}{abs(diff):.1f}kg（{rows[1]['log_date']} {rows[1]['weight_kg']}kg → {rows[0]['log_date']} {rows[0]['weight_kg']}kg）",
        }
    return None


def check_exercise_streak() -> Optional[dict]:
    """检测连续多少天没有运动记录"""
    conn = get_conn()
    row = conn.execute(
        "SELECT MAX(log_date) as last_date FROM exercise_logs"
    ).fetchone()
    conn.close()
    if not row or not row["last_date"]:
        return None
    last = date.fromisoformat(row["last_date"])
    gap_days = (date.today() - last).days
    if gap_days >= 3:
        return {
            "type": "exercise_absence",
            "severity": "warning" if gap_days >= 5 else "info",
            "message": f"已连续{gap_days}天未记录运动，上次运动是{row['last_date']}",
        }
    return None


def check_diet_completeness(days: int = 3) -> Optional[dict]:
    """检测最近几天饮食记录是否完整（每天至少2餐）"""
    conn = get_conn()
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT log_date, COUNT(*) as cnt FROM diet_logs WHERE log_date >= ? AND log_date < ? GROUP BY log_date",
        (since, date.today().isoformat())
    ).fetchall()
    conn.close()
    incomplete_days = []
    for r in rows:
        if r["cnt"] < 2:
            incomplete_days.append(r["log_date"])
    if incomplete_days:
        return {
            "type": "diet_incomplete",
            "severity": "info",
            "message": f"最近{days}天中有{len(incomplete_days)}天饮食记录不完整（每天不足2餐）：{', '.join(incomplete_days)}",
        }
    return None


def run_all_anomaly_checks() -> list[dict]:
    """运行所有异常检测，返回新发现的异常列表"""
    anomalies = []
    for check_fn in [check_weight_anomaly, check_exercise_streak, check_diet_completeness]:
        result = check_fn()
        if result:
            # 避免重复报警：检查今天是否已有同类型
            conn = get_conn()
            exists = conn.execute(
                "SELECT id FROM alerts WHERE alert_date=? AND alert_type=?",
                (date.today().isoformat(), result["type"])
            ).fetchone()
            conn.close()
            if not exists:
                add_alert(result["type"], result["message"], result["severity"])
                anomalies.append(result)
    return anomalies


# ── 月报 ──────────────────────────────────────────────────

def get_monthly_summary(year: int = 0, month: int = 0) -> dict:
    """获取指月汇总数据"""
    if not year:
        year = date.today().year
    if not month:
        month = date.today().month
    first_day = date(year, month, 1).isoformat()
    if month == 12:
        last_day = date(year + 1, 1, 1).isoformat()
    else:
        last_day = date(year, month + 1, 1).isoformat()

    conn = get_conn()
    diet_sum = conn.execute(
        "SELECT COALESCE(SUM(calories_est),0) as cal, COUNT(*) as meals, COUNT(DISTINCT log_date) as days FROM diet_logs WHERE log_date >= ? AND log_date < ?",
        (first_day, last_day)
    ).fetchone()
    exercise_sum = conn.execute(
        "SELECT COALESCE(SUM(calories_burned),0) as cal, COALESCE(SUM(duration_min),0) as min, COUNT(*) as sessions, COUNT(DISTINCT log_date) as days FROM exercise_logs WHERE log_date >= ? AND log_date < ?",
        (first_day, last_day)
    ).fetchone()
    weights = conn.execute(
        "SELECT log_date, weight_kg FROM weight_logs WHERE log_date >= ? AND log_date < ? ORDER BY log_date",
        (first_day, last_day)
    ).fetchall()
    conn.close()

    total_days = (date.fromisoformat(last_day) - date.fromisoformat(first_day)).days
    weight_list = [dict(r) for r in weights]

    return {
        "period": f"{year}-{month:02d}",
        "total_days": total_days,
        "diet_total_cal": diet_sum["cal"],
        "diet_avg_cal_per_day": round(diet_sum["cal"] / max(diet_sum["days"], 1)),
        "diet_meal_count": diet_sum["meals"],
        "diet_tracked_days": diet_sum["days"],
        "exercise_total_cal": exercise_sum["cal"],
        "exercise_total_min": exercise_sum["min"],
        "exercise_session_count": exercise_sum["sessions"],
        "exercise_tracked_days": exercise_sum["days"],
        "weight_trend": weight_list,
        "weight_change": round(weight_list[-1]["weight_kg"] - weight_list[0]["weight_kg"], 1) if len(weight_list) >= 2 else 0,
    }


# ── 综合上下文（供 AI 生成计划/复盘用）────────────────────

def get_full_context() -> dict:
    """获取用户完整上下文信息（画像 + 目标 + 最近数据），供 AI 生成计划使用"""
    profile = get_user_profile()
    goal = get_health_goal()
    weight = get_latest_weight()
    today_summary = get_daily_summary()
    weekly = get_weekly_summary()
    pending_meals = get_pending_meals()
    alerts = get_unacknowledged_alerts(days=3)
    rules = {r["rule_key"]: r["rule_value"] for r in get_all_time_rules()}

    return {
        "profile": profile,
        "goal": goal,
        "latest_weight": weight,
        "today": today_summary,
        "weekly": weekly,
        "pending_meals": pending_meals,
        "recent_alerts": alerts,
        "time_rules": rules,
        "holiday_mode": is_holiday_mode(),
    }


# 初始化数据库
init_db()
