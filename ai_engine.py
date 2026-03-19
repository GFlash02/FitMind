"""
个人助理 - AI 分析引擎
封装所有 LLM 调用，供 Streamlit UI 和 CLI 共同使用。
使用 OpenClaw 的 VectorEngine AI 作为后端。
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from datetime import date

# 加载 .env（Streamlit 和 CLI 都会用到）
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "sk-placeholder"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.vectorengine.ai/v1"),
    )


def get_model() -> str:
    return os.getenv("OPENAI_MODEL", "claude-sonnet-4-6")


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
    """从 LLM 响应中提取 JSON，兼容非标准格式"""
    import re
    if not text:
        raise ValueError("Empty response from AI")
    # 提取代码块
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 修复无引号的 key：{key: value} -> {"key": value}
    fixed = re.sub(r'(?<=[{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    # 尝试提取第一个 {...} 块
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        block = m.group(0)
        fixed2 = re.sub(r'(?<=[{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', block)
        return json.loads(fixed2)
    raise ValueError(f"Cannot parse JSON from: {text[:200]}")


# ── AI 分析函数 ───────────────────────────────────────────

def analyze_exercise(exercise_type: str, duration_min: int,
                     intensity: str, weight_kg: float = 65.0) -> dict:
    """分析运动数据，估算消耗热量"""
    system_prompt = """你是运动健康专家。根据运动信息估算热量消耗，输出JSON：
{"calories_burned": 热量整数, "met_value": MET值, "tips": "简短运动建议（30字内）"}
只输出JSON。"""
    user_prompt = f"运动类型：{exercise_type}，时长：{duration_min}分钟，强度：{intensity}，体重：{weight_kg}kg"
    return parse_json_response(chat(system_prompt, user_prompt, temperature=0.2))


def analyze_diet(meal_type: str, description: str,
                 exercise_calories: int = 0) -> dict:
    """分析饮食数据，估算营养成分"""
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
    user_prompt = f"餐次：{meal_type}\n食物描述：{description}\n今日运动消耗：{exercise_calories}kcal"
    return parse_json_response(chat(system_prompt, user_prompt, temperature=0.3))


def analyze_schedule(natural_text: str) -> dict:
    """从自然语言中解析日程信息"""
    from datetime import date
    today = date.today().isoformat()
    system_prompt = f"""你是日程解析助手。今天是 {today}。
将自然语言解析为JSON：
{{"title":"日程标题","event_date":"YYYY-MM-DD","event_time":"HH:MM","location":"地点（无则空）","reminder":"提醒说明（无则空）"}}
只输出JSON。"""
    return parse_json_response(chat(system_prompt, natural_text, temperature=0.1))


def decompose_task(goal: str, deadline: str, daily_hours: int = 4) -> dict:
    """将目标分解为子任务"""
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
    return parse_json_response(chat(system_prompt, user_prompt, temperature=0.3))


def generate_health_plan(height_cm: float, current_weight: float,
                         target_weight: float, age: int, gender: str,
                         weeks_target: int, activity_level: str) -> str:
    """生成个性化健康计划"""
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
    user_prompt = (
        f"身高：{height_cm}cm，当前体重：{current_weight}kg，目标体重：{target_weight}kg\n"
        f"BMI：{bmi:.1f}，年龄：{age}岁，性别：{gender}\n"
        f"目标：{weeks_target}周内{direction}{abs(weight_diff):.1f}kg\n"
        f"活动水平：{activity_level}"
    )
    return chat(system_prompt, user_prompt, temperature=0.5)


def generate_daily_advice(summary: dict) -> str:
    """根据当日综合数据生成建议"""
    system_prompt = """你是个人健康管理顾问。根据用户今天的数据给出简明建议。
要求：
1. 先给出一句话总评
2. 如果有不足（如运动少、热量超标），给出具体改善建议
3. 如果表现好，给予肯定鼓励
4. 最后给一条明天的提醒
语气温暖专业，总字数不超过200字。"""

    user_prompt = json.dumps(summary, ensure_ascii=False, indent=2)
    return chat(system_prompt, user_prompt, temperature=0.6)


def smart_parse_feishu_message(message: str) -> dict:
    """
    智能解析用户通过飞书发来的自然语言消息，
    判断意图并提取结构化数据。

    返回:
    {
      "intent": "record_exercise|record_diet|record_weight|add_schedule|query_summary|query_weekly|set_goal|update_profile|set_rules|general_chat",
      "data": { ... 对应的结构化数据 ... },
      "reply_hint": "建议的回复方向"
    }
    """
    today = date.today().isoformat()

    system_prompt = f"""你是智能个人助理的消息解析器。今天是 {today}。
用户会用自然语言发来各种消息，你需要判断用户意图并提取结构化数据。

可能的意图（intent）及对应的 data 结构：

1. "record_exercise" — 记录运动
   data: {{"exercise_type": "跑步", "duration_min": 30, "intensity": "中", "notes": "备注", "log_date": "{today}"}}

2. "record_diet" — 记录饮食
   data: {{"meal_type": "午餐", "description": "食物描述", "log_date": "{today}"}}

3. "record_weight" — 记录体重
   data: {{"weight_kg": 65.0, "log_date": "{today}"}}

4. "add_schedule" — 添加日程
   data: {{"title": "日程标题", "event_date": "YYYY-MM-DD", "event_time": "HH:MM", "location": "", "reminder": ""}}

5. "query_summary" — 查询今日/某日数据
   data: {{"target_date": "{today}"}}

6. "query_weekly" — 查询周报
   data: {{}}

7. "set_goal" — 设定健康目标
   data: {{"current_weight": 70, "target_weight": 65, "height_cm": 170, "age": 25, "gender": "男", "weeks_target": 12, "activity_level": "轻度活跃"}}

8. "update_profile" — 更新个人画像
   data: {{"height_cm": 175, "body_fat_pct": 20, "dietary_restrictions": "低糖", "food_allergies": "海鲜", "exercise_restrictions": "膝盖不好", "vitamin_deficiencies": "维D"}}

9. "set_rules" — 修改时间规则/假期模式
   data: {{"rule_key": "holiday_mode", "rule_value": "on"}}

10. "meal_reply" — 回复餐食问询（当系统主动询问用户吃了什么时）
    data: {{"meal_type": "午餐", "description": "食物描述", "log_date": "{today}"}}

11. "exercise_reply" — 回复运动问询
    data: {{"exercise_type": "跑步", "duration_min": 30, "intensity": "中", "log_date": "{today}"}}
    如果用户说没运动: data: {{"skipped": true, "reason": "太累了"}}

12. "general_chat" — 一般闲聊或无法归类
    data: {{"message": "原始消息"}}

输出严格的 JSON，包含 intent, data, reply_hint 三个字段。
reply_hint 是给助理的简短提示，说明应该如何回复用户。
只输出JSON。"""

    return parse_json_response(chat(system_prompt, message, temperature=0.2))


# ── 新增：每日计划生成 ────────────────────────────────────

def generate_daily_plan(context: dict) -> str:
    """根据用户画像和目标，生成今日饮食+运动计划"""
    system_prompt = """你是专业的健康管理顾问。根据用户的个人信息、健康目标和最近数据，
生成一份今天的饮食和运动计划。

输出格式：
🌅 早安问候（一句话）

🍽️ 今日饮食计划：
  早餐：具体推荐（含预估热量）
  午餐：具体推荐（含预估热量）
  晚餐：具体推荐（含预估热量）
  加餐建议：如有需要

🏃 今日运动计划：
  推荐运动及时长

📝 今日注意事项：
  1-2条个性化提醒

要求：
- 考虑用户的饮食偏好、过敏信息、运动禁忌
- 热量目标要符合减重/增肌计划
- 语言温暖简洁，总字数300字以内
- 如果是假期模式，计划可以更轻松"""

    user_prompt = json.dumps(context, ensure_ascii=False, indent=2)
    return chat(system_prompt, user_prompt, temperature=0.6)


def generate_meal_inquiry(meal_type: str, context: dict, inquiry_count: int = 0) -> str:
    """生成主动问询消息，根据问询次数调整语气"""
    if inquiry_count == 0:
        tone = "友好轻松地询问"
    elif inquiry_count == 1:
        tone = "温柔地提醒一下"
    else:
        tone = "不再追问，只做简短关心"

    system_prompt = f"""你是用户的健康管理小助手。现在需要{tone}用户的{meal_type}情况。

规则：
- 第1次（inquiry_count=0）：友好地问用户吃了什么，可以提供建议
- 第2次（inquiry_count=1）：简短温柔提醒
- 第3次+（inquiry_count>=2）：简短关心一句即可，不要施压

注意：
- 如有今日饮食计划，可以巧妙提及
- 语气温暖、非说教式
- 总字数不超过50字
- 用emoji增加亲切感"""

    user_prompt = f"meal_type: {meal_type}\ninquiry_count: {inquiry_count}\ncontext: {json.dumps(context, ensure_ascii=False)}"
    return chat(system_prompt, user_prompt, temperature=0.7)


def generate_exercise_inquiry(context: dict) -> str:
    """生成晚间运动问询消息"""
    system_prompt = """你是用户的健康管理助手。现在是晚上，需要询问用户今天的运动情况。

规则：
- 先看今天是否已有运动记录，如果有则改为鼓励
- 如果没有运动记录，温和地问一下
- 不要施压，理解用户可能忙碌
- 总字数不超过50字
- 用emoji"""

    user_prompt = json.dumps(context, ensure_ascii=False)
    return chat(system_prompt, user_prompt, temperature=0.7)


def generate_daily_review(context: dict) -> str:
    """生成每日复盘总结"""
    system_prompt = """你是健康管理顾问。根据用户今天的完整数据生成日复盘。

格式：
📊 今日复盘 (日期)

🍽️ 饮食：摄入总热量 / 目标热量
  三大营养素比例点评
  
🏃 运动：消耗热量 / 运动时长
  运动表现点评

⚖️ 热量收支：净摄入 = 摄入 - 消耗
  
✅ 做得好的：1-2点
📌 明天注意：1-2点

总字数200字以内，数据为主观点为辅，温暖但专业。"""

    user_prompt = json.dumps(context, ensure_ascii=False, indent=2)
    return chat(system_prompt, user_prompt, temperature=0.5)


def generate_weekly_review(weekly_data: dict, context: dict) -> str:
    """生成周复盘"""
    system_prompt = """你是健康管理顾问。根据用户本周数据生成周度复盘。

格式：
📈 本周复盘 (起止日期)

🍽️ 饮食总结：日均热量、记录完整度、营养均衡度
🏃 运动总结：运动天数、总时长、总消耗
⚖️ 体重变化：如有数据
🏆 本周亮点：1-2个做得好的
📌 下周建议：1-2个改进方向

比起日复盘更宏观，关注趋势和模式。300字以内。"""

    combined = {"weekly_stats": weekly_data, "context": context}
    user_prompt = json.dumps(combined, ensure_ascii=False, indent=2)
    return chat(system_prompt, user_prompt, temperature=0.5)


def generate_monthly_review(monthly_data: dict, context: dict) -> str:
    """生成月度复盘"""
    system_prompt = """你是健康管理顾问。根据用户本月数据生成月度复盘。

格式：
📅 月度复盘 (YYYY年MM月)

📊 数据概览：
  饮食：日均热量、记录天数/总天数、总餐数
  运动：运动天数、总时长、总消耗
  体重：月初→月末变化

🏆 本月成就：2-3个亮点
📌 下月目标：2-3个改进方向
💡 长期建议：基于趋势的一条核心建议

关注长期趋势和习惯养成。400字以内。"""

    combined = {"monthly_stats": monthly_data, "context": context}
    user_prompt = json.dumps(combined, ensure_ascii=False, indent=2)
    return chat(system_prompt, user_prompt, temperature=0.5)
