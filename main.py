from fastapi import FastAPI
from pydantic import BaseModel
from RadiologyClinicalAI import RadiologyClinicalAI

app = FastAPI()
ai = RadiologyClinicalAI()

class Report(BaseModel):
    report_text: str

@app.post("/analyze")
async def analyze(report: Report):
    return {"analysis": ai.generate_report(report.report_text)}
