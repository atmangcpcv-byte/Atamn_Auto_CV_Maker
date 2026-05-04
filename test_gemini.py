import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from google.genai import types

load_dotenv()

class EmpSkillRating(BaseModel):
    skill_name: str
    rating: float

class EmpSummary(BaseModel):
    emp_id: int
    work_summary: str
    skills: list[EmpSkillRating]

class AIResult(BaseModel):
    project_tech_stack: list[str]
    employee_summaries: list[EmpSummary]

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="Project description: Created a web app in Python using Django and PostgreSQL. Employees: 1 (Backend Dev). Give tech stack and work summary",
        config=types.GenerateContentConfig(
             response_mime_type="application/json",
             response_schema=AIResult,
        ),
    )
    print("SUCCESS")
    print(response.text)
except Exception as e:
    print("ERROR:", e)
