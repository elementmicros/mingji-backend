import json
import random
import requests
from lunar_python import Solar

DEEPSEEK_API_KEY = "sk-e125963ed071491595f42ced43588ca5"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

SYSTEM_PROMPT = """你是一个认识用户多年的老朋友，坐在夜市摊上跟他喝啤酒。你知道他是什么样的人，也看穿了他正在怎么骗自己。

铁律：
1. 所有分析必须指向用户自身。禁止把问题归因于他人。
2. 不共情、不讨好、不用任何称呼套近乎。
3. 不用任何命理术语，不用任何心理学专业名词。
4. 每棍必须指向他刚写的困扰，用生活场景说话。
5. 只输出三棍，每棍不超过两句话，之间空一行。
6. 不要编号，不要标题，不要任何解释。
7. 根据用户写的困扰，自动判断他的身份角色。
8. 如果用户的困扰里没有提到具体的行业、身份、场景，必须先追问一句。

三棍分量：轻拍、加重、敲顶。只输出三句话。"""

def build_user_prompt(bazi_data, user_input):
    gender = user_input.get("gender", "男")
    city = user_input.get("city", "")
    trouble = user_input.get("trouble", "")
    day_gan = bazi_data["dayGan"]
    current_dayun = bazi_data["current_dayun"]
    wuxing = bazi_data["wuxing"]
    wuxing_str = "、".join([f"{k}{v}" for k, v in wuxing.items() if v > 0])
    
    return f"""他是一位{gender}，来自{city}。
他刚写下的困扰是：{trouble}
基础数据：{day_gan}日主，当前大运{current_dayun}，五行分布：{wuxing_str}。
请用老朋友的语气，给他三棍。只输出三句话。"""

def safe_str(s):
    if s is None:
        return ""
    if isinstance(s, bytes):
        return s.decode('utf-8', errors='ignore')
    return str(s)

def call_deepseek(messages, max_tokens=600):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.9,
        "max_tokens": max_tokens,
        "stream": False
    }
    resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    result = resp.json()
    return safe_str(result['choices'][0]['message']['content'].strip())

valid_codes = {}

def handle_bazi(data):
    solar = Solar.fromYmdHms(data['year'], data['month'], data['day'], data['hour'], 0, 0)
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
    
    yun = bazi.getYun(data.get('sex', 1))
    daYunArr = yun.getDaYun()
    current_age = 2026 - data['year']
    current_dayun = None
    for dy in daYunArr:
        if dy.getStartAge() <= current_age:
            current_dayun = dy.getGanZhi()
    
    bazi_data = {
        "bazi": safe_str(bazi.toString()),
        "year": safe_str(bazi.getYear()),
        "month": safe_str(bazi.getMonth()),
        "day": safe_str(bazi.getDay()),
        "time": safe_str(bazi.getTime()),
        "dayGan": safe_str(bazi.getDayGan()),
        "wuxing": wuxing_count,
        "dayun_start_age": yun.getStartYear(),
        "current_dayun": safe_str(current_dayun) if current_dayun else None,
        "dayun_list": [{"ganzhi": safe_str(d.getGanZhi()), "age": d.getStartAge()} for d in daYunArr],
    }
    
    user_input = {"city": data.get("city", ""), "gender": data.get("gender", "男"), "trouble": data.get("trouble", "")}
    user_prompt = build_user_prompt(bazi_data, user_input)
    
    try:
        free_report = call_deepseek([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
    except Exception as e:
        free_report = "AI generation failed: " + str(e)
    
    return {"bazi_data": bazi_data, "free_report": free_report}

def handle_generate_code():
    code = str(random.randint(100000, 999999))
    valid_codes[code] = False
    return {"code": code}

def handle_verify_payment(data):
    code = data.get("code", "")
    if code in valid_codes and not valid_codes[code]:
        valid_codes[code] = True
        return {"status": "success"}
    elif code in valid_codes and valid_codes[code]:
        return {"status": "code already used"}
    else:
        return {"status": "invalid code"}

def handle_deep_report(data):
    solar = Solar.fromYmdHms(data['year'], data['month'], data['day'], data['hour'], 0, 0)
    lunar = solar.getLunar()
    bazi = lunar.getEightChar()
    
    wuxing_raw = bazi.getYearWuXing() + bazi.getMonthWuXing() + bazi.getDayWuXing() + bazi.getTimeWuXing()
    wuxing_count = {
        "金": wuxing_raw.count("金"), "木": wuxing_raw.count("木"),
        "水": wuxing_raw.count("水"), "火": wuxing_raw.count("火"), "土": wuxing_raw.count("土"),
    }
    
    yun = bazi.getYun(data.get('sex', 1))
    current_age = 2026 - data['year']
    current_dayun = None
    for dy in yun.getDaYun():
        if dy.getStartAge() <= current_age:
            current_dayun = dy.getGanZhi()
    
    bazi_data = {
        "bazi": safe_str(bazi.toString()),
        "dayGan": safe_str(bazi.getDayGan()),
        "wuxing": wuxing_count,
        "current_dayun": safe_str(current_dayun) if current_dayun else None,
    }
    
    user_input = {"city": data.get("city", ""), "gender": data.get("gender", "男"), "trouble": data.get("trouble", "")}
    user_prompt = build_deep_prompt(bazi_data, user_input)
    
    try:
        deep_report = call_deepseek([
            {"role": "system", "content": "你是一个认识用户多年的老朋友。说真话，不讨好，不用术语。"},
            {"role": "user", "content": user_prompt},
        ], max_tokens=1500)
    except Exception as e:
        deep_report = "Deep report generation failed: " + str(e)
    
    return {"deep_report": deep_report}

def build_deep_prompt(bazi_data, user_input):
    gender = user_input.get("gender", "男")
    city = user_input.get("city", "")
    trouble = user_input.get("trouble", "")
    day_gan = bazi_data["dayGan"]
    current_dayun = bazi_data["current_dayun"]
    wuxing = bazi_data["wuxing"]
    wuxing_str = "、".join([f"{k}{v}" for k, v in wuxing.items() if v > 0])
    
    return f"""他是一位{gender}，来自{city}。
困扰：{trouble}
数据：{day_gan}日主，大运{current_dayun}，五行{wuxing_str}。

请生成深度报告，分四个部分：
【共鸣】描述他这一路走来的不容易，用城市、行业背景，具体场景。不评价，只描述。
【盲区】指出他一直在回避的盲区，让他看见自己在怎么骗自己。全部指向他自己。
【转机】从另一个维度重新定义他的困扰，让他发现看问题的方式出了问题。
【行动】给他一个可执行的具体建议，结合他的场景。

铁律：不用术语，不讨好，不共情，不归因他人。每部分用【】标注标题。"""

# ──────────────── 阿里云 FC 入口 ────────────────

def handler(environ, start_response):
    path = environ['PATH_INFO']
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0
    request_body = environ['wsgi.input'].read(request_body_size)
    data = json.loads(request_body.decode('utf-8')) if request_body else {}
    
    if path == '/':
        result = {"message": "明己后端运行中"}
    elif path == '/api/bazi':
        result = handle_bazi(data)
    elif path == '/api/generate_code':
        result = handle_generate_code()
    elif path == '/api/verify_payment':
        result = handle_verify_payment(data)
    elif path == '/api/deep_report':
        result = handle_deep_report(data)
    else:
        result = {"error": "Not found"}
    
    response_body = json.dumps(result, ensure_ascii=False).encode('utf-8')
    status = '200 OK'
    response_headers = [
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)
    return [response_body]