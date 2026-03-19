# 🦞 AI 个人助理

首届中关村北纬龙虾大赛参赛作品

## 功能模块

- **运动记录** — 记录运动类型/时长/强度，AI 计算热量消耗
- **饮食分析** — 描述一餐，AI 估算热量和营养成分，结合运动量给出建议
- **健康目标** — 设定目标体重和周期，AI 生成个性化计划
- **数据总览** — 热量收支图、运动分布图、体重趋势图

## 快速开始

```bash
cd /assistant
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Key
streamlit run app.py（streamlit run assistant/app_standalone.py --server.port 8501）
```

## 环境变量


| 变量              | 说明                                 |
| ----------------- | ------------------------------------ |
| `OPENAI_API_KEY`  | API Key                              |
| `OPENAI_BASE_URL` | API Base URL（支持 OpenAI 兼容接口） |
| `OPENAI_MODEL`    | 模型名称，默认`gpt-4o`               |

数据存储在本地 SQLite 文件 `assistant_data.db`，无需额外数据库。
