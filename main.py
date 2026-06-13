from fastapi import FastAPI
from pydantic import BaseModel
from lunar_python import Solar
from prompt import build_prompt, SYSTEM_PROMPT

app = FastAPI(title="明己后端")

class BirthInput(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    sex: int = 1
    city: str = ""
    gender: str = "男"
    trouble: str = ""

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
    
    prompt = build_prompt(bazi_data, user_input)
    
    gender_text = data.gender
    city_text = data.city
    trouble_text = data.trouble[:10]
    
    report = "老" + gender_text + "，你在" + city_text + "这么多年，是不是一直觉得自己能扛？\n\n"
    report += "你跟我说" + trouble_text + "，但你有没有想过，你怕的从来不是那个领导，是你自己心里那关过不去。你一辈子都在用让别人舒服来换安全感，领导说个不字你就觉得天要塌了。可你真塌过吗？\n\n"
    report += "你嘴上说压力大，其实你最怕的是失控。一旦事情没按你预想的走，你就开始焦虑。但你从来不说，你就闷着，闷到晚上睡不着，闷到胸口发闷。你以为你在忍，其实你是在躲，躲那个你不敢直视的事实：你不是不能扛，是不敢承认自己也会累。\n\n"
    report += "今年是你该松一松的时候了。不是放弃工作，是别再拿别人的评价当尺子量自己。你那个新尝试，别管它现在多不起眼，继续做。它不是你逃避工作压力的借口，是你给自己留的一条后路。想好怎么走，咱后面细聊。"
    
    return {
        "bazi_data": bazi_data,
        "free_report": report,
    }

@app.get("/")
def root():
    return {"message": "明己后端运行中"}