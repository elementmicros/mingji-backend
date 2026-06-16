from fastapi import FastAPI
from pydantic import BaseModel
from lunar_python import Solar
from openai import OpenAI
from fastapi.responses import JSONResponse
import random

app = FastAPI(title="明己后端")

# DeepSeek API 配置
DEEPSEEK_API_KEY = "你的API-Key"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

class BirthInput(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    sex: int = 1
    city: str = ""
    gender: str = "男"
    trouble: str = ""

SYSTEM_PROMPT = """你是一个认识用户多年的老朋友，坐在夜市摊上跟他喝啤酒。你知道他是什么样的人，也看穿了他正在怎么骗自己。

铁律：
1. 所有分析必须指向用户自身。禁止把问题归因于他人。
2. 不共情、不讨好、不用任何称呼套近乎。
3. 不用任何命理术语，不用任何心理学专业名词。
4. 每棍必须指向他刚写的困扰，用生活场景说话。
5. 只输出三棍，每棍不超过两句话，之间空一行。
6. 不要编号，不要标题，不要任何解释。
7. 根据用户写的困扰，自动判断他的身份角色。如果是抱怨领导、老板，他是被管理者；如果是抱怨下属、团队，他是管理者。禁止直接说"你的领导"或"你的下属"，用生活场景暗示关系。
8. 精准度铁律：如果用户的困扰里没有提到具体的行业、身份、场景，你不准自己猜。必须在生成第一棍前，先用括号追问一句，等他说明白了再继续。

三棍的分量：
- 第一棍：轻拍肩膀。精确指向他刚写的困扰，让他觉得"你在说我"。
- 第二棍：加重力道。指出他一直回避的盲区，让他沉默几秒。
- 第三棍：敲在头顶。从另一个维度重新定义他的问题，让他发现自己一直在跟自己较劲，然后释然。

输出格式：只输出三句话，每句不超过两行。"""

def build_user_prompt(bazi_data: dict, user_input: dict) -> str:
    gender = user_input.get("gender", "男")
    city = user_input.get("city", "")
    trouble = user_input.get("trouble", "")
    day_gan = bazi_data["dayGan"]
    current_dayun = bazi_data["current_dayun"]
    wuxing = bazi_data["wuxing"]
    
    wuxing_str = "、".join([f"{k}{v}" for k, v in wuxing.items() if v > 0])
    
    return f"""他是一位{gender}，来自{city}。
他刚写下的困扰是：{trouble}
他的基础数据：{day_gan}日主，当前大运{current_dayun}，五行分布：{wuxing_str}。

请根据这些信息，用你作为老朋友的语气，给他三棍。只输出三句话。"""

@app.post("/api/bazi")
def get_bazi(data: BirthInput):
    solar = Solar.fromYmdHms(data.year, data.month, data.day, data.hour, 0, 0)
    lunar = solar.getLunar()
    bazi = lunar.getEightChar()
    
    wuxing_raw = bazi.getYearWuXing() + bazi.getMonthWuXing() + bazi.getDayWuXing() + bazi.getTimeWuXing()
    wuxing_count = {
        "金": wuxing_raw.count("金"),
        "木": wuxing_raw.count("木"),
        "水": wuxing_raw.count("水"),
        "火": wuxing_raw.count("火"),
        "土": wuxing_raw.count("土"),
    }
    
    yun = bazi.getYun(data.sex)
    daYunArr = yun.getDaYun()
    current_age = 2026 - data.year
    current_dayun = None
    for dy in daYunArr:
        if dy.getStartAge() <= current_age:
            current_dayun = dy.getGanZhi()
    
    bazi_data = {
        "bazi": bazi.toString(),
        "year": bazi.getYear(),
        "month": bazi.getMonth(),
        "day": bazi.getDay(),
        "time": bazi.getTime(),
        "dayGan": bazi.getDayGan(),
        "wuxing": wuxing_count,
        "dayun_start_age": yun.getStartYear(),
        "current_dayun": current_dayun,
        "dayun_list": [{"ganzhi": d.getGanZhi(), "age": d.getStartAge()} for d in daYunArr],
    }
    
    user_input = {
        "city": data.city,
        "gender": data.gender,
        "trouble": data.trouble,
    }
    
    user_prompt = build_user_prompt(bazi_data, user_input)
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
            max_tokens=600,
        )
        free_report = response.choices[0].message.content.strip()
    except Exception as e:
        free_report = f"AI生成失败：{str(e)}"
    
    return {
        "bazi_data": bazi_data,
        "free_report": free_report,
    }

# 支付验证相关
valid_codes = {}  # {"code": False/True}

class GenerateCodeInput(BaseModel):
    pass

@app.post("/api/generate_code")
def generate_code(data: GenerateCodeInput):
    code = str(random.randint(100000, 999999))
    valid_codes[code] = False
    return {"code": code}

class VerifyInput(BaseModel):
    code: str

@app.post("/api/verify_payment")
def verify_payment(data: VerifyInput):
    code = data.code
    if code in valid_codes and not valid_codes[code]:
        valid_codes[code] = True
        return {"status": "success", "message": "验证成功"}
    elif code in valid_codes and valid_codes[code]:
        return {"status": "fail", "message": "验证码已被使用"}
    else:
        return {"status": "fail", "message": "验证码无效"}

# 深度报告接口
class DeepReportInput(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    sex: int = 1
    city: str = ""
    gender: str = "男"
    trouble: str = ""

def build_deep_prompt(bazi_data: dict, user_input: dict) -> str:
    gender = user_input.get("gender", "男")
    city = user_input.get("city", "")
    trouble = user_input.get("trouble", "")
    day_gan = bazi_data["dayGan"]
    current_dayun = bazi_data["current_dayun"]
    wuxing = bazi_data["wuxing"]
    wuxing_str = "、".join([f"{k}{v}" for k, v in wuxing.items() if v > 0])
    
    return f"""他是一位{gender}，来自{city}。
他写下的困扰是：{trouble}
基础数据：{day_gan}日主，当前大运{current_dayun}，五行分布：{wuxing_str}。

请生成一份深度报告，分四个部分：

第一部分【共鸣】：描述他这一路走来的不容易。用他的城市、他的行业背景，说出他可能经历过的具体场景。让他觉得"你懂我"。不评价，只描述。

第二部分【盲区】：指出他一直在回避的盲区。不是批判，是让他看见自己在怎么骗自己。全部指向他自己，不归因他人。

第三部分【转机】：从另一个维度重新定义他的困扰。这个角度是他自己从来没想过的。让他发现原来问题不是问题本身，是看问题的方式出了问题。

第四部分【行动】：给他一个可执行的具体建议。结合他的场景，给出他能马上做的小动作。

铁律：不用命理术语，不用心理学名词，不讨好，不共情，不归因他人。每部分用【】标注标题。"""

@app.post("/api/deep_report")
def get_deep_report(data: DeepReportInput):
    solar = Solar.fromYmdHms(data.year, data.month, data.day, data.hour, 0, 0)
    lunar = solar.getLunar()
    bazi = lunar.getEightChar()
    
    wuxing_raw = bazi.getYearWuXing() + bazi.getMonthWuXing() + bazi.getDayWuXing() + bazi.getTimeWuXing()
    wuxing_count = {
        "金": wuxing_raw.count("金"), "木": wuxing_raw.count("木"),
        "水": wuxing_raw.count("水"), "火": wuxing_raw.count("火"), "土": wuxing_raw.count("土"),
    }
    
    yun = bazi.getYun(data.sex)
    daYunArr = yun.getDaYun()
    current_age = 2026 - data.year
    current_dayun = None
    for dy in daYunArr:
        if dy.getStartAge() <= current_age:
            current_dayun = dy.getGanZhi()
    
    bazi_data = {
        "bazi": bazi.toString(), "dayGan": bazi.getDayGan(),
        "wuxing": wuxing_count, "current_dayun": current_dayun,
    }
    
    user_input = {"city": data.city, "gender": data.gender, "trouble": data.trouble}
    user_prompt = build_deep_prompt(bazi_data, user_input)
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个认识用户多年的老朋友。说真话，不讨好，不用术语。"},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
            max_tokens=1500,
        )
        deep_report = response.choices[0].message.content.strip()
    except Exception as e:
        deep_report = f"报告生成失败：{str(e)}"
    
    return {"deep_report": deep_report}

@app.get("/")
def root():
    return {"message": "明己后端运行中"}