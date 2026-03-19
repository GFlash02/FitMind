"""
🦞 AI 个人健康管理助理 — 独立运行版
与 OpenClaw CLI 共享同一数据库（assistant_data.db）。

启动方式:
  c:/python314/python.exe -m streamlit run app_standalone.py --server.port 8502

功能: 任务分解 | 日程管理 | 运动记录 | 饮食分析 | 健康目标 | 数据总览 | 个人画像 | 预警中心
"""

import os
import sys
from datetime import datetime, date

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dotenv import load_dotenv

# 加载 .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# 导入共享模块
sys.path.insert(0, os.path.dirname(__file__))
import core
import ai_engine

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="🦞 AI 个人健康管理助理",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 侧边栏 ───────────────────────────────────────────────
with st.sidebar:
    st.title("🦞 个人助理")
    st.caption("健康管理 · OpenClaw 集成")
    st.divider()

    # 状态速览
    today_intake = core.get_today_diet_calories()
    today_burned = core.get_today_exercise_calories()
    weight = core.get_latest_weight()
    holiday = core.is_holiday_mode()

    st.metric("今日净摄入", f"{today_intake - today_burned} kcal")
    if weight:
        st.metric("最新体重", f"{weight['weight_kg']} kg")
    if holiday:
        st.warning("🌴 假期模式已开启")

    # 快速操作
    st.divider()
    pending = core.get_pending_meals()
    if pending:
        st.info(f"📋 待记录餐次：{'、'.join(pending)}")

    alerts = core.get_unacknowledged_alerts(days=3)
    if alerts:
        st.error(f"⚠️ {len(alerts)} 条未确认预警")

    st.divider()
    with st.expander("⚙️ API 配置", expanded=False):
        api_key = st.text_input("API Key", value=os.getenv("OPENAI_API_KEY", ""), type="password")
        base_url = st.text_input("Base URL", value=os.getenv("OPENAI_BASE_URL", "https://api.vectorengine.ai/v1"))
        model_name = st.text_input("模型", value=os.getenv("OPENAI_MODEL", "claude-sonnet-4-6"))
        if st.button("应用配置"):
            os.environ["OPENAI_API_KEY"] = api_key
            os.environ["OPENAI_BASE_URL"] = base_url
            os.environ["OPENAI_MODEL"] = model_name
            st.success("✅ 已更新")

# ── 主界面 ────────────────────────────────────────────────
st.title("🦞 AI 个人健康管理助理")

selected = st.radio(
    "功能选择",
    ["📊 数据总览", "🍱 饮食分析", "💪 运动记录", "🎯 健康目标",
     "📅 日程管理", "📋 任务分解", "👤 个人画像", "⚠️ 预警中心"],
    horizontal=True,
    label_visibility="collapsed",
)

# ════════════════════════════════════════════════════════
# 数据总览
# ════════════════════════════════════════════════════════
if selected == "📊 数据总览":
    st.subheader(f"📊 今日概览 — {date.today().isoformat()}")

    summary = core.get_daily_summary()
    goal = core.get_health_goal()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("摄入热量", f"{summary['diet']['total_calories']} kcal")
    c2.metric("运动消耗", f"{summary['exercise']['total_calories_burned']} kcal")
    c3.metric("净摄入", f"{summary['calorie_balance']} kcal")
    if goal:
        w = core.get_latest_weight()
        if w:
            c4.metric("距目标体重", f"{abs(w['weight_kg'] - goal['target_weight']):.1f} kg")

    # 餐次跟踪
    st.divider()
    tracking = core.get_meal_tracking()
    mcols = st.columns(3)
    for i, t in enumerate(tracking):
        icon = "✅" if t["status"] == "submitted" else "⏳"
        mcols[i % 3].markdown(f"{icon} **{t['meal_type']}** — {'已记录' if t['status'] == 'submitted' else '待记录'}")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        conn = core.get_conn()
        rows = conn.execute("""
            SELECT d.log_date, SUM(d.calories_est) as intake, COALESCE(e.burned,0) as burned
            FROM diet_logs d
            LEFT JOIN (SELECT log_date, SUM(calories_burned) as burned FROM exercise_logs GROUP BY log_date) e
            ON d.log_date = e.log_date
            WHERE d.log_date >= date('now','-7 days')
            GROUP BY d.log_date ORDER BY d.log_date
        """).fetchall()
        conn.close()
        if rows:
            df = pd.DataFrame(rows, columns=["日期", "摄入(kcal)", "消耗(kcal)"])
            fig = go.Figure()
            fig.add_trace(go.Bar(name="摄入", x=df["日期"], y=df["摄入(kcal)"], marker_color="#ff7675"))
            fig.add_trace(go.Bar(name="运动消耗", x=df["日期"], y=df["消耗(kcal)"], marker_color="#74b9ff"))
            fig.update_layout(title="近7天热量收支", barmode="group", height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无近7天饮食数据")

    with col2:
        conn = core.get_conn()
        erows = conn.execute("""
            SELECT exercise_type, COUNT(*) as cnt, SUM(duration_min) as total_min
            FROM exercise_logs WHERE log_date >= date('now','-30 days')
            GROUP BY exercise_type ORDER BY cnt DESC
        """).fetchall()
        conn.close()
        if erows:
            edf = pd.DataFrame(erows, columns=["运动类型", "次数", "总时长(min)"])
            fig2 = px.pie(edf, values="次数", names="运动类型", title="近30天运动分布", hole=0.4)
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("暂无运动数据")

    # 体重趋势
    wdata = core.list_weights(days=30)
    if len(wdata) >= 2:
        wdf = pd.DataFrame(wdata)
        fig3 = px.line(wdf, x="log_date", y="weight_kg", markers=True, title="体重趋势",
                       labels={"log_date": "日期", "weight_kg": "体重(kg)"},
                       color_discrete_sequence=["#a29bfe"])
        if goal:
            fig3.add_hline(y=goal["target_weight"], line_dash="dash", line_color="green",
                           annotation_text=f"目标 {goal['target_weight']}kg")
        st.plotly_chart(fig3, use_container_width=True)

    # AI 每日建议
    st.divider()
    if st.button("🤖 获取 AI 今日建议"):
        with st.spinner("AI 正在分析你的数据..."):
            advice = ai_engine.generate_daily_advice(summary)
            st.info(advice)

# ════════════════════════════════════════════════════════
# 饮食分析
# ════════════════════════════════════════════════════════
elif selected == "🍱 饮食分析":
    tab_log, tab_history = st.tabs(["📝 记录饮食", "📋 历史记录"])

    with tab_log:
        col1, col2 = st.columns(2)
        with col1:
            meal_type = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
        with col2:
            log_date = st.date_input("日期", value=date.today(), key="diet_date")

        description = st.text_area(
            "描述这餐吃了什么",
            placeholder="米饭一碗（约200g），红烧肉3块，炒青菜一份，紫菜蛋花汤一碗",
            height=100,
        )

        today_exercise = core.get_today_exercise_calories(log_date.isoformat())
        if today_exercise > 0:
            st.info(f"💪 今日已记录运动消耗：{today_exercise} kcal")

        if st.button("🔍 AI 分析饮食", type="primary", disabled=not description):
            with st.spinner("AI 正在分析营养成分..."):
                try:
                    result = ai_engine.analyze_diet(meal_type, description, today_exercise)
                    core.add_diet(
                        meal_type=meal_type, description=description,
                        calories_est=result.get("calories", 0),
                        protein_g=result.get("protein_g", 0),
                        carbs_g=result.get("carbs_g", 0),
                        fat_g=result.get("fat_g", 0),
                        ai_advice=result.get("advice", ""),
                        log_date=log_date.isoformat(),
                    )
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("热量", f"{result['calories']} kcal")
                    c2.metric("蛋白质", f"{result['protein_g']} g")
                    c3.metric("碳水", f"{result['carbs_g']} g")
                    c4.metric("脂肪", f"{result['fat_g']} g")
                    eval_icon = {"优": "🟢", "良": "🟡", "一般": "🟠", "较差": "🔴"}.get(result.get("evaluation", ""), "⚪")
                    st.markdown(f"**营养评价：** {eval_icon} {result.get('evaluation', '')}")
                    st.info(f"💡 {result.get('advice', '')}")
                    today_total = core.get_today_diet_calories(log_date.isoformat())
                    st.markdown(f"**今日累计：** 摄入 {today_total} kcal — 运动 {today_exercise} kcal = 净 {today_total - today_exercise} kcal")
                except Exception as e:
                    st.error(f"分析失败：{e}")

    with tab_history:
        diets = core.list_diets(days=30)
        if not diets:
            st.info("还没有饮食记录～")
        else:
            rows = [(d["log_date"], d["meal_type"], d["description"], d["calories_est"],
                     d["protein_g"], d["carbs_g"], d["fat_g"]) for d in diets]
            df = pd.DataFrame(rows, columns=["日期", "餐次", "描述", "热量", "蛋白质", "碳水", "脂肪"])
            st.dataframe(df, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════
# 运动记录
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
            w = core.get_latest_weight()
            default_weight = w["weight_kg"] if w else 65.0
            weight_for_calc = st.number_input("体重（kg）", min_value=30.0, max_value=200.0,
                                              value=default_weight, step=0.5)
        notes = st.text_input("备注（可选）", placeholder="今天跑了5公里")

        if st.button("💾 保存并计算热量", type="primary"):
            with st.spinner("AI 正在计算热量消耗..."):
                try:
                    result = ai_engine.analyze_exercise(exercise_type, duration_min, intensity, weight_for_calc)
                    calories = result["calories_burned"]
                    core.add_exercise(exercise_type=exercise_type, duration_min=duration_min,
                                      intensity=intensity, calories_burned=calories, notes=notes)
                    st.success(f"✅ 已记录！预计消耗 **{calories} kcal**")
                    st.info(f"💡 {result.get('tips', '')}")
                except Exception as e:
                    st.error(f"计算失败：{e}")

    with tab_history:
        exercises = core.list_exercises(days=30)
        if not exercises:
            st.info("还没有运动记录～")
        else:
            rows = [(e["log_date"], e["exercise_type"], e["duration_min"], e["intensity"],
                     e["calories_burned"], e["notes"]) for e in exercises]
            df = pd.DataFrame(rows, columns=["日期", "类型", "时长(min)", "强度", "热量(kcal)", "备注"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("运动次数", f"{len(df)} 次")
            c2.metric("总时长", f"{df['时长(min)'].sum()} min")
            c3.metric("总消耗", f"{df['热量(kcal)'].sum()} kcal")

# ════════════════════════════════════════════════════════
# 健康目标
# ════════════════════════════════════════════════════════
elif selected == "🎯 健康目标":
    st.subheader("🎯 健康目标设定")
    goal_row = core.get_health_goal()

    with st.form("goal_form"):
        col1, col2 = st.columns(2)
        with col1:
            current_weight = st.number_input("当前体重 (kg)", 30.0, 200.0,
                                             float(goal_row["current_weight"]) if goal_row else 70.0, 0.5)
            target_weight = st.number_input("目标体重 (kg)", 30.0, 200.0,
                                            float(goal_row["target_weight"]) if goal_row else 65.0, 0.5)
            height_cm = st.number_input("身高 (cm)", 100.0, 220.0,
                                        float(goal_row["height_cm"]) if goal_row else 170.0, 0.5)
        with col2:
            age = st.number_input("年龄", 10, 100, int(goal_row["age"]) if goal_row else 25)
            gender = st.selectbox("性别", ["男", "女"],
                                  index=0 if (not goal_row or goal_row["gender"] == "男") else 1)
            weeks_target = st.number_input("目标周期（周）", 1, 52,
                                           int(goal_row["weeks_target"]) if goal_row else 12)
            activity_levels = ["久坐（几乎不运动）", "轻度活跃（每周1-3次）",
                               "中度活跃（每周3-5次）", "高度活跃（每周6-7次）"]
            cur_idx = 1
            if goal_row and goal_row["activity_level"] in activity_levels:
                cur_idx = activity_levels.index(goal_row["activity_level"])
            activity_level = st.selectbox("活动水平", activity_levels, index=cur_idx)
        submitted = st.form_submit_button("💾 保存目标并获取计划", type="primary")

    if submitted:
        core.set_health_goal(current_weight, target_weight, height_cm, age, gender, weeks_target, activity_level)
        core.add_weight(current_weight)
        with st.spinner("AI 正在制定个性化计划..."):
            bmi = current_weight / ((height_cm / 100) ** 2)
            weight_diff = current_weight - target_weight
            direction = "减重" if weight_diff > 0 else "增重"
            plan = ai_engine.generate_health_plan(height_cm, current_weight, target_weight,
                                                   age, gender, weeks_target, activity_level)
        c1, c2, c3 = st.columns(3)
        c1.metric("BMI", f"{bmi:.1f}")
        c2.metric(f"目标{direction}", f"{abs(weight_diff):.1f} kg")
        c3.metric("周期", f"{weeks_target} 周")
        st.info(plan)

    # 体重趋势
    wdata = core.list_weights(days=60)
    if len(wdata) >= 2:
        st.divider()
        wdf = pd.DataFrame(wdata)
        fig = px.line(wdf, x="log_date", y="weight_kg", markers=True, title="体重趋势",
                      labels={"log_date": "日期", "weight_kg": "体重(kg)"},
                      color_discrete_sequence=["#667eea"])
        if goal_row:
            fig.add_hline(y=goal_row["target_weight"], line_dash="dash", line_color="green",
                          annotation_text=f"目标 {goal_row['target_weight']}kg")
        st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════
# 日程管理
# ════════════════════════════════════════════════════════
elif selected == "📅 日程管理":
    tab_add, tab_view = st.tabs(["➕ 添加日程", "📋 查看日程"])

    with tab_add:
        natural_input = st.text_area("用自然语言描述日程",
                                     placeholder="下周三下午3点在图书馆和导师开组会", height=100)
        if st.button("🤖 AI 解析并添加", type="primary", disabled=not natural_input):
            with st.spinner("AI 正在解析日程..."):
                try:
                    parsed = ai_engine.analyze_schedule(natural_input)
                    core.add_schedule(
                        title=parsed.get("title", ""),
                        event_date=parsed.get("event_date", date.today().isoformat()),
                        event_time=parsed.get("event_time", ""),
                        location=parsed.get("location", ""),
                        reminder=parsed.get("reminder", ""),
                    )
                    st.success(f"✅ 已添加：**{parsed['title']}** — {parsed['event_date']} {parsed.get('event_time', '')}")
                except Exception as e:
                    st.error(f"解析失败：{e}")

    with tab_view:
        schedules = core.list_schedules()
        if not schedules:
            st.info("暂无日程")
        else:
            rows = [(s["id"], s["title"], s["event_date"], s["event_time"],
                     s["location"], s["reminder"]) for s in schedules]
            df = pd.DataFrame(rows, columns=["ID", "标题", "日期", "时间", "地点", "提醒"])
            today_str = date.today().isoformat()

            def highlight(row):
                if row["日期"] == today_str:
                    return ["background-color: #fff3cd"] * len(row)
                elif row["日期"] < today_str:
                    return ["color: #aaa"] * len(row)
                return [""] * len(row)

            st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True, hide_index=True)
            del_id = st.number_input("删除日程 ID", min_value=1, step=1, value=1)
            if st.button("🗑️ 删除"):
                core.delete_schedule(int(del_id))
                st.rerun()

# ════════════════════════════════════════════════════════
# 任务分解
# ════════════════════════════════════════════════════════
elif selected == "📋 任务分解":
    st.subheader("📋 AI 任务分解")
    goal = st.text_area("🎯 输入你的目标", placeholder="例如：下周要完成毕业论文第三章...", height=120)
    col1, col2 = st.columns(2)
    with col1:
        deadline = st.date_input("截止日期", value=datetime.today())
    with col2:
        daily_hours = st.slider("每天可用工时（小时）", 1, 12, 4)

    if st.button("🚀 开始分解任务", type="primary", disabled=not goal):
        with st.spinner("AI 正在分析并分解任务..."):
            try:
                result = ai_engine.decompose_task(goal, str(deadline), daily_hours)
                st.success(f"✅ {result['summary']}")
                st.info(f"📊 预计总耗时：**{result['total_hours']} 小时**")
                priority_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}
                df = pd.DataFrame(result["tasks"])
                df["优先级"] = df["priority"].map(lambda x: f"{priority_icon.get(x, '⚪')} {x}")
                df["预计耗时"] = df["hours"].map(lambda x: f"{x}h")
                st.dataframe(
                    df[["order", "title", "description", "优先级", "预计耗时"]].rename(
                        columns={"order": "顺序", "title": "任务", "description": "描述"}),
                    use_container_width=True, hide_index=True,
                )
                if result.get("tips"):
                    st.markdown("**💡 执行建议**")
                    for tip in result["tips"]:
                        st.markdown(f"- {tip}")
            except Exception as e:
                st.error(f"解析失败：{e}")

# ════════════════════════════════════════════════════════
# 个人画像
# ════════════════════════════════════════════════════════
elif selected == "👤 个人画像":
    st.subheader("👤 个人画像管理")
    st.markdown("配置你的个人信息，让 AI 计划和建议更个性化。")

    profile = core.get_user_profile()

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            _h = float(profile["height_cm"]) if profile and profile["height_cm"] else 170.0
            height_cm = st.number_input("身高 (cm)", 100.0, 220.0,
                                        max(100.0, min(220.0, _h)), 0.5)
            _bf = float(profile["body_fat_pct"]) if profile and profile["body_fat_pct"] else 0.0
            body_fat_pct = st.number_input("体脂率 (%)", 0.0, 60.0, max(0.0, min(60.0, _bf)), 0.5)
            dietary_restrictions = st.text_input("饮食偏好/限制",
                                                 value=profile["dietary_restrictions"] if profile else "",
                                                 placeholder="如：低糖低盐、素食、清真...")
        with col2:
            food_allergies = st.text_input("食物过敏",
                                           value=profile["food_allergies"] if profile else "",
                                           placeholder="如：海鲜、花生、牛奶...")
            exercise_restrictions = st.text_input("运动禁忌",
                                                  value=profile["exercise_restrictions"] if profile else "",
                                                  placeholder="如：膝盖不好不能跑步...")
            vitamin_deficiencies = st.text_input("维生素/营养素缺乏",
                                                 value=profile["vitamin_deficiencies"] if profile else "",
                                                 placeholder="如：维生素D偏低、缺铁...")
        submitted = st.form_submit_button("💾 保存画像", type="primary")

    if submitted:
        core.set_user_profile(
            height_cm=height_cm, body_fat_pct=body_fat_pct,
            dietary_restrictions=dietary_restrictions, food_allergies=food_allergies,
            exercise_restrictions=exercise_restrictions, vitamin_deficiencies=vitamin_deficiencies,
        )
        st.success("✅ 个人画像已保存！")

    # 当前画像展示
    if profile:
        st.divider()
        st.markdown("**当前画像**")
        items = {
            "身高": f"{profile['height_cm']} cm",
            "体脂率": f"{profile['body_fat_pct']}%" if profile["body_fat_pct"] else "未设置",
            "饮食限制": profile["dietary_restrictions"] or "无",
            "食物过敏": profile["food_allergies"] or "无",
            "运动禁忌": profile["exercise_restrictions"] or "无",
            "营养素缺乏": profile["vitamin_deficiencies"] or "无",
        }
        for k, v in items.items():
            st.markdown(f"- **{k}**：{v}")

    # 时间规则
    st.divider()
    st.subheader("⏰ 时间规则配置")
    rules = core.get_all_time_rules()
    for r in rules:
        col1, col2 = st.columns([3, 1])
        col1.markdown(f"**{r['description']}** (`{r['rule_key']}`)")
        new_val = col2.text_input(r["rule_key"], value=r["rule_value"], key=f"rule_{r['rule_key']}",
                                  label_visibility="collapsed")
        if new_val != r["rule_value"]:
            core.set_time_rule(r["rule_key"], new_val)
            st.rerun()

# ════════════════════════════════════════════════════════
# 预警中心
# ════════════════════════════════════════════════════════
elif selected == "⚠️ 预警中心":
    st.subheader("⚠️ 预警中心")

    # 手动运行检测
    if st.button("🔍 运行异常检测"):
        anomalies = core.run_all_anomaly_checks()
        if anomalies:
            for a in anomalies:
                icon = "🔴" if a["severity"] == "warning" else "🟡"
                st.warning(f"{icon} {a['message']}")
        else:
            st.success("✅ 一切正常，未发现异常")

    st.divider()
    alerts = core.get_unacknowledged_alerts(days=30)
    if not alerts:
        st.info("暂无未确认的预警")
    else:
        for a in alerts:
            icon = "🔴" if a["severity"] == "warning" else "🟡"
            col1, col2 = st.columns([5, 1])
            col1.markdown(f"{icon} **{a['alert_date']}** — {a['message']}")
            if col2.button("确认", key=f"ack_{a['id']}"):
                core.acknowledge_alert(a["id"])
                st.rerun()

    # 假期模式开关
    st.divider()
    holiday = core.is_holiday_mode()
    st.markdown(f"**假期模式**：{'🌴 已开启' if holiday else '关闭'}")
    if holiday:
        if st.button("关闭假期模式"):
            core.set_time_rule("holiday_mode", "off")
            st.rerun()
    else:
        if st.button("🌴 开启假期模式"):
            core.set_time_rule("holiday_mode", "on")
            st.rerun()
