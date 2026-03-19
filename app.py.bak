"""
AI 个人助理 - 首届中关村北纬龙虾大赛参赛作品
功能：任务分解、日程管理、健康管理（运动记录、饮食分析、目标设定、数据可视化）
"""

import os
import json
import sqlite3
from datetime import datetime, date
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

load_dotenv()

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="🦞 AI 个人助理",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 数据库初始化 ──────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "assistant_data.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 日程表
    c.execute("""CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        event_date TEXT NOT NULL,
        event_time TEXT,
        location TEXT,
        reminder TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # 运动记录表
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
    # 饮食记录表
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
    # 体重记录表
    c.execute("""CREATE TABLE IF NOT EXISTS weight_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        weight_kg REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # 健康目标表
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
    conn.commit()
    conn.close()

init_db()

def get_conn():
    return sqlite3.connect(DB_PATH)

# ── OpenAI 客户端 ─────────────────────────────────────────
@st.cache_resource
def get_client():
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "sk-placeholder"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )

def get_model():
    return os.getenv("OPENAI_MODEL", "gpt-4o")

def chat(system: str, user: str, temperature: float = 0.7) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()

def parse_json_response(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())

# ── 侧边栏 ────────────────────────────────────────────────
with st.sidebar:
    st.title("🦞 AI 个人助理")
    st.caption("首届中关村北纬龙虾大赛")
    st.divider()

    with st.expander("⚙️ API 配置", expanded=False):
        api_key = st.text_input("API Key", value=os.getenv("OPENAI_API_KEY", ""), type="password")
        base_url = st.text_input("Base URL", value=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
        model_name = st.text_input("模型", value=os.getenv("OPENAI_MODEL", "gpt-4o"))
        if st.button("应用配置"):
            os.environ["OPENAI_API_KEY"] = api_key
            os.environ["OPENAI_BASE_URL"] = base_url
            os.environ["OPENAI_MODEL"] = model_name
            st.cache_resource.clear()
            st.success("✅ 配置已更新")

    st.divider()
    selected = st.radio("功能导航", [
        "📋 任务分解",
        "📅 日程管理",
        "💪 运动记录",
        "🍱 饮食分析",
        "🎯 健康目标",
        "📊 数据总览",
    ], label_visibility="collapsed")

st.title(selected)

# ════════════════════════════════════════════════════════
# 功能1：任务分解
# ════════════════════════════════════════════════════════
if selected == "📋 任务分解":
    st.markdown("输入目标或项目描述，AI 自动分解为可执行子任务，给出优先级和时间估算。")

    goal = st.text_area("🎯 输入你的目标", placeholder="例如：下周要完成毕业论文第三章，包括文献综述和实验设计部分...", height=120)
    col1, col2 = st.columns(2)
    with col1:
        deadline = st.date_input("截止日期", value=datetime.today())
    with col2:
        daily_hours = st.slider("每天可用工时（小时）", 1, 12, 4)

    if st.button("🚀 开始分解任务", type="primary", disabled=not goal):
        with st.spinner("AI 正在分析并分解任务..."):
            system_prompt = """你是专业的项目管理顾问。将目标分解为5-10个具体可执行的子任务。
输出严格的JSON格式：
{
  "summary": "任务总结（一句话）",
  "total_hours": 总预计小时数,
  "tasks": [
    {"id": 1, "title": "子任务标题", "description": "具体描述", "priority": "高/中/低", "hours": 预计小时数, "order": 建议执行顺序}
  ],
  "tips": ["执行建议1", "执行建议2"]
}"""
            user_prompt = f"目标：{goal}\n截止日期：{deadline}\n每天可用工时：{daily_hours}小时"
            try:
                result = parse_json_response(chat(system_prompt, user_prompt, temperature=0.3))
                st.success(f"✅ {result['summary']}")
                st.info(f"📊 预计总耗时：**{result['total_hours']} 小时**")

                priority_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}
                df = pd.DataFrame(result["tasks"])
                df["优先级"] = df["priority"].map(lambda x: f"{priority_icon.get(x,'⚪')} {x}")
                df["预计耗时"] = df["hours"].map(lambda x: f"{x}h")
                st.dataframe(
                    df[["order","title","description","优先级","预计耗时"]].rename(
                        columns={"order":"顺序","title":"任务","description":"描述"}),
                    use_container_width=True, hide_index=True,
                )
                if result.get("tips"):
                    st.markdown("**💡 执行建议**")
                    for tip in result["tips"]:
                        st.markdown(f"- {tip}")

                md = f"# 任务分解：{goal[:30]}\n\n截止：{deadline} | 每日工时：{daily_hours}h | 总预计：{result['total_hours']}h\n\n"
                for t in result["tasks"]:
                    md += f"### {t['order']}. {t['title']} [{t['priority']}优先级 · {t['hours']}h]\n{t['description']}\n\n"
                st.download_button("📥 导出 Markdown", md, file_name="tasks.md", mime="text/markdown")
            except Exception as e:
                st.error(f"解析失败，请重试。错误：{e}")

# ════════════════════════════════════════════════════════
# 功能2：日程管理
# ════════════════════════════════════════════════════════
elif selected == "📅 日程管理":
    tab_add, tab_view = st.tabs(["➕ 添加日程", "📋 查看日程"])

    with tab_add:
        natural_input = st.text_area("用自然语言描述日程", placeholder="下周三下午3点在图书馆和导师开组会，记得提前半小时提醒我", height=100)
        if st.button("🤖 AI解析并添加", type="primary", disabled=not natural_input):
            with st.spinner("AI 正在解析日程..."):
                system_prompt = f"""你是日程解析助手。今天是 {date.today().isoformat()}。
将自然语言解析为JSON：
{{"title":"日程标题","event_date":"YYYY-MM-DD","event_time":"HH:MM","location":"地点（无则空）","reminder":"提醒说明（无则空）"}}
只输出JSON。"""
                try:
                    parsed = parse_json_response(chat(system_prompt, natural_input, temperature=0.1))
                    conn = get_conn()
                    conn.execute(
                        "INSERT INTO schedules (title, event_date, event_time, location, reminder) VALUES (?,?,?,?,?)",
                        (parsed["title"], parsed["event_date"], parsed.get("event_time",""), parsed.get("location",""), parsed.get("reminder",""))
                    )
                    conn.commit(); conn.close()
                    st.success(f"✅ 已添加：**{parsed['title']}** — {parsed['event_date']} {parsed.get('event_time','')}")
                    if parsed.get("location"): st.info(f"📍 {parsed['location']}")
                    if parsed.get("reminder"): st.info(f"⏰ {parsed['reminder']}")
                except Exception as e:
                    st.error(f"解析失败：{e}")

    with tab_view:
        conn = get_conn()
        rows = conn.execute("SELECT id, title, event_date, event_time, location, reminder FROM schedules ORDER BY event_date, event_time").fetchall()
        conn.close()
        if not rows:
            st.info("暂无日程")
        else:
            df = pd.DataFrame(rows, columns=["ID","标题","日期","时间","地点","提醒"])
            today_str = date.today().isoformat()
            def highlight(row):
                if row["日期"] == today_str: return ["background-color: #fff3cd"] * len(row)
                elif row["日期"] < today_str: return ["color: #aaa"] * len(row)
                return [""] * len(row)
            st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True, hide_index=True)
            del_id = st.number_input("删除日程 ID", min_value=1, step=1, value=1)
            if st.button("🗑️ 删除"):
                conn = get_conn()
                conn.execute("DELETE FROM schedules WHERE id=?", (del_id,))
                conn.commit(); conn.close()
                st.rerun()

# ════════════════════════════════════════════════════════
# 功能3：运动记录
# ════════════════════════════════════════════════════════
elif selected == "💪 运动记录":
    tab_log, tab_history = st.tabs(["📝 记录运动", "📋 历史记录"])

    with tab_log:
        col1, col2 = st.columns(2)
        with col1:
            exercise_type = st.selectbox("运动类型", [
                "跑步", "快走", "骑行", "游泳", "跳绳",
                "力量训练", "瑜伽", "HIIT", "篮球", "其他"
            ])
            duration_min = st.number_input("时长（分钟）", min_value=1, max_value=300, value=30)
        with col2:
            intensity = st.select_slider("运动强度", options=["低", "中", "高"])
            weight_for_calc = st.number_input("体重（kg，用于热量计算）", min_value=30.0, max_value=200.0, value=65.0, step=0.5)
        notes = st.text_input("备注（可选）", placeholder="今天跑了5公里，感觉不错")

        if st.button("💾 保存并计算热量", type="primary"):
            with st.spinner("AI 正在计算热量消耗..."):
                system_prompt = """你是运动健康专家。根据运动信息估算热量消耗，输出JSON：
{"calories_burned": 热量整数, "met_value": MET值, "tips": "简短运动建议（30字内）"}
只输出JSON。"""
                user_prompt = f"运动类型：{exercise_type}，时长：{duration_min}分钟，强度：{intensity}，体重：{weight_for_calc}kg"
                try:
                    result = parse_json_response(chat(system_prompt, user_prompt, temperature=0.2))
                    calories = result["calories_burned"]
                    conn = get_conn()
                    conn.execute(
                        "INSERT INTO exercise_logs (log_date, exercise_type, duration_min, intensity, calories_burned, notes) VALUES (?,?,?,?,?,?)",
                        (date.today().isoformat(), exercise_type, duration_min, intensity, calories, notes)
                    )
                    conn.commit(); conn.close()
                    st.success(f"✅ 已记录！预计消耗 **{calories} 千卡**")
                    st.info(f"💡 {result.get('tips','')}")
                except Exception as e:
                    st.error(f"计算失败：{e}")

    with tab_history:
        conn = get_conn()
        rows = conn.execute(
            "SELECT log_date, exercise_type, duration_min, intensity, calories_burned, notes FROM exercise_logs ORDER BY log_date DESC LIMIT 30"
        ).fetchall()
        conn.close()
        if not rows:
            st.info("还没有运动记录，去记录第一次运动吧～")
        else:
            df = pd.DataFrame(rows, columns=["日期","运动类型","时长(min)","强度","热量(kcal)","备注"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            total_cal = df["热量(kcal)"].sum()
            total_min = df["时长(min)"].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("累计运动次数", f"{len(df)} 次")
            c2.metric("累计时长", f"{total_min} 分钟")
            c3.metric("累计消耗热量", f"{total_cal} kcal")

# ════════════════════════════════════════════════════════
# 功能4：饮食分析
# ════════════════════════════════════════════════════════
elif selected == "🍱 饮食分析":
    tab_log, tab_history = st.tabs(["📝 记录饮食", "📋 历史记录"])

    with tab_log:
        col1, col2 = st.columns(2)
        with col1:
            meal_type = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
        with col2:
            log_date = st.date_input("日期", value=date.today())

        description = st.text_area(
            "描述这餐吃了什么",
            placeholder="米饭一碗（约200g），红烧肉3块，炒青菜一份，紫菜蛋花汤一碗",
            height=100,
        )

        # 获取今日运动消耗（用于给出更精准建议）
        conn = get_conn()
        today_exercise = conn.execute(
            "SELECT SUM(calories_burned) FROM exercise_logs WHERE log_date=?",
            (log_date.isoformat(),)
        ).fetchone()[0] or 0
        conn.close()

        if today_exercise > 0:
            st.info(f"💪 今日已记录运动消耗：{today_exercise} kcal")

        if st.button("🔍 AI分析饮食", type="primary", disabled=not description):
            with st.spinner("AI 正在分析营养成分..."):
                system_prompt = """你是专业营养师。分析用户描述的一餐，估算营养成分，输出JSON：
{
  "calories": 热量整数(kcal),
  "protein_g": 蛋白质克数,
  "carbs_g": 碳水克数,
  "fat_g": 脂肪克数,
  "evaluation": "营养评价（优/良/一般/较差）",
  "advice": "针对性饮食建议（50字内）"
}
只输出JSON。"""
                user_prompt = f"餐次：{meal_type}\n食物描述：{description}\n今日运动消耗：{today_exercise}kcal"
                try:
                    result = parse_json_response(chat(system_prompt, user_prompt, temperature=0.3))
                    conn = get_conn()
                    conn.execute(
                        "INSERT INTO diet_logs (log_date, meal_type, description, calories_est, protein_g, carbs_g, fat_g, ai_advice) VALUES (?,?,?,?,?,?,?,?)",
                        (log_date.isoformat(), meal_type, description,
                         result["calories"], result["protein_g"], result["carbs_g"], result["fat_g"], result["advice"])
                    )
                    conn.commit(); conn.close()

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("热量", f"{result['calories']} kcal")
                    c2.metric("蛋白质", f"{result['protein_g']} g")
                    c3.metric("碳水", f"{result['carbs_g']} g")
                    c4.metric("脂肪", f"{result['fat_g']} g")

                    eval_icon = {"优":"🟢","良":"🟡","一般":"🟠","较差":"🔴"}.get(result["evaluation"],"⚪")
                    st.markdown(f"**营养评价：** {eval_icon} {result['evaluation']}")
                    st.info(f"💡 {result['advice']}")

                    # 热量收支对比
                    if today_exercise > 0:
                        conn = get_conn()
                        today_intake = conn.execute(
                            "SELECT SUM(calories_est) FROM diet_logs WHERE log_date=?",
                            (log_date.isoformat(),)
                        ).fetchone()[0] or 0
                        conn.close()
                        balance = today_intake - today_exercise
                        st.markdown(f"**今日热量收支：** 摄入 {today_intake} kcal — 运动消耗 {today_exercise} kcal = **净摄入 {balance} kcal**")
                except Exception as e:
                    st.error(f"分析失败：{e}")

    with tab_history:
        conn = get_conn()
        rows = conn.execute(
            "SELECT log_date, meal_type, description, calories_est, protein_g, carbs_g, fat_g FROM diet_logs ORDER BY log_date DESC, meal_type LIMIT 30"
        ).fetchall()
        conn.close()
        if not rows:
            st.info("还没有饮食记录～")
        else:
            df = pd.DataFrame(rows, columns=["日期","餐次","描述","热量(kcal)","蛋白质(g)","碳水(g)","脂肪(g)"])
            st.dataframe(df, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════
# 功能5：健康目标
# ════════════════════════════════════════════════════════
elif selected == "🎯 健康目标":
    st.markdown("设定减脂/增肌目标，AI 根据你的数据动态给出个性化计划。")

    conn = get_conn()
    goal_row = conn.execute("SELECT * FROM health_goals ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    with st.form("goal_form"):
        col1, col2 = st.columns(2)
        with col1:
            current_weight = st.number_input("当前体重 (kg)", 30.0, 200.0, float(goal_row[1]) if goal_row else 70.0, 0.5)
            target_weight = st.number_input("目标体重 (kg)", 30.0, 200.0, float(goal_row[2]) if goal_row else 65.0, 0.5)
            height_cm = st.number_input("身高 (cm)", 100.0, 220.0, float(goal_row[3]) if goal_row else 170.0, 0.5)
        with col2:
            age = st.number_input("年龄", 10, 100, int(goal_row[4]) if goal_row else 25)
            gender = st.selectbox("性别", ["男", "女"], index=0 if (not goal_row or goal_row[5] == "男") else 1)
            weeks_target = st.number_input("目标周期（周）", 1, 52, int(goal_row[6]) if goal_row else 12)
            activity_level = st.selectbox("日常活动水平", ["久坐（几乎不运动）","轻度活跃（每周1-3次）","中度活跃（每周3-5次）","高度活跃（每周6-7次）"],
                                          index=["久坐（几乎不运动）","轻度活跃（每周1-3次）","中度活跃（每周3-5次）","高度活跃（每周6-7次）"].index(goal_row[7]) if goal_row and goal_row[7] else 1)
        submitted = st.form_submit_button("💾 保存目标并获取计划", type="primary")

    if submitted:
        conn = get_conn()
        conn.execute(
            "INSERT INTO health_goals (current_weight, target_weight, height_cm, age, gender, weeks_target, activity_level, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (current_weight, target_weight, height_cm, age, gender, weeks_target, activity_level, datetime.now().isoformat())
        )
        conn.execute("INSERT INTO weight_logs (log_date, weight_kg) VALUES (?,?)", (date.today().isoformat(), current_weight))
        conn.commit(); conn.close()

        with st.spinner("AI 正在制定个性化计划..."):
            bmi = current_weight / ((height_cm / 100) ** 2)
            weight_diff = current_weight - target_weight
            direction = "减重" if weight_diff > 0 else "增重"

            system_prompt = """你是专业健身营养顾问。根据用户数据制定个性化健康计划，包括：
1. 每日推荐热量摄入（TDEE计算）
2. 三大营养素分配建议
3. 每周运动计划（具体到运动类型和时长）
4. 饮食原则（3-5条）
5. 注意事项
语言简洁专业，总字数不超过400字。"""
            user_prompt = f"身高：{height_cm}cm，当前体重：{current_weight}kg，目标体重：{target_weight}kg\nBMI：{bmi:.1f}，年龄：{age}岁，性别：{gender}\n目标：{weeks_target}周内{direction}{abs(weight_diff):.1f}kg\n活动水平：{activity_level}"
            plan = chat(system_prompt, user_prompt, temperature=0.5)

        c1, c2, c3 = st.columns(3)
        c1.metric("BMI", f"{bmi:.1f}")
        c2.metric(f"目标{direction}", f"{abs(weight_diff):.1f} kg")
        c3.metric("周期", f"{weeks_target} 周")
        st.markdown("**📋 AI 个性化计划：**")
        st.info(plan)

    conn = get_conn()
    wrows = conn.execute("SELECT log_date, weight_kg FROM weight_logs ORDER BY log_date").fetchall()
    conn.close()
    if len(wrows) >= 2:
        st.divider()
        st.markdown("**📈 体重趋势**")
        wdf = pd.DataFrame(wrows, columns=["日期","体重(kg)"])
        fig = px.line(wdf, x="日期", y="体重(kg)", markers=True, color_discrete_sequence=["#667eea"])
        if goal_row:
            fig.add_hline(y=goal_row[2], line_dash="dash", line_color="green", annotation_text=f"目标 {goal_row[2]}kg")
        st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════
# 功能6：数据总览
# ════════════════════════════════════════════════════════
elif selected == "📊 数据总览":
    st.markdown(f"今日：{date.today().isoformat()}")
    conn = get_conn()

    today_str = date.today().isoformat()
    intake = conn.execute("SELECT SUM(calories_est) FROM diet_logs WHERE log_date=?", (today_str,)).fetchone()[0] or 0
    burned = conn.execute("SELECT SUM(calories_burned) FROM exercise_logs WHERE log_date=?", (today_str,)).fetchone()[0] or 0
    goal_row = conn.execute("SELECT target_weight, current_weight FROM health_goals ORDER BY id DESC LIMIT 1").fetchone()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("今日摄入", f"{intake} kcal")
    c2.metric("今日运动消耗", f"{burned} kcal")
    c3.metric("净摄入", f"{intake - burned} kcal")
    if goal_row:
        c4.metric("距目标体重", f"{abs(goal_row[1] - goal_row[0]):.1f} kg")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        rows = conn.execute("""
            SELECT d.log_date, SUM(d.calories_est) as intake, COALESCE(e.burned,0) as burned
            FROM diet_logs d
            LEFT JOIN (SELECT log_date, SUM(calories_burned) as burned FROM exercise_logs GROUP BY log_date) e
            ON d.log_date = e.log_date
            WHERE d.log_date >= date('now','-7 days')
            GROUP BY d.log_date ORDER BY d.log_date
        """).fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["日期","摄入(kcal)","消耗(kcal)"])
            fig = go.Figure()
            fig.add_trace(go.Bar(name="摄入", x=df["日期"], y=df["摄入(kcal)"], marker_color="#ff7675"))
            fig.add_trace(go.Bar(name="运动消耗", x=df["日期"], y=df["消耗(kcal)"], marker_color="#74b9ff"))
            fig.update_layout(title="近7天热量收支", barmode="group", height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无近7天饮食数据")

    with col2:
        erows = conn.execute("""
            SELECT exercise_type, COUNT(*) as cnt, SUM(duration_min) as total_min
            FROM exercise_logs
            WHERE log_date >= date('now','-30 days')
            GROUP BY exercise_type ORDER BY cnt DESC
        """).fetchall()
        if erows:
            edf = pd.DataFrame(erows, columns=["运动类型","次数","总时长(min)"])
            fig2 = px.pie(edf, values="次数", names="运动类型", title="近30天运动分布", hole=0.4)
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("暂无近30天运动数据")

    wrows = conn.execute("SELECT log_date, weight_kg FROM weight_logs ORDER BY log_date DESC LIMIT 30").fetchall()
    conn.close()
    if len(wrows) >= 2:
        wdf = pd.DataFrame(wrows, columns=["日期","体重(kg)"]).sort_values("日期")
        fig3 = px.line(wdf, x="日期", y="体重(kg)", markers=True, title="体重趋势", color_discrete_sequence=["#a29bfe"])
        st.plotly_chart(fig3, use_container_width=True)
