import os
import json
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types
from sqlalchemy.orm import Session

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Import your new database setup
from database import SessionLocal, UserRecord, ReportRecord, init_db

if not os.getenv("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY is not set in the backend .env file")

client = genai.Client()
app = FastAPI(title="CosmicTea API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TeaRequest(BaseModel):
    name: str
    dob: str
    time: str
    location: str
    gender: str


class TeaResponse(BaseModel):
    sun_sign: str
    career_tea: str
    love_gossip: str
    karmic_roast: str


@app.on_event("startup")
async def startup_event():
    try:
        init_db()
    except Exception as exc:
        print(f"Database startup warning: {exc}")


# Dependency to get the database session per request
def get_db():
    if SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured. Set DATABASE_URL or SUPABASE_DATABASE_URL in the backend .env file.",
        )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/spill-tea", response_model=TeaResponse)
async def generate_destiny(request: TeaRequest, db: Session = Depends(get_db)):
    try:
        # 1. Save the incoming React form data to the 'users' table
        new_user = UserRecord(
            name=request.name,
            dob=request.dob,
            time=request.time,
            location=request.location,
            gender=request.gender,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)  # Retrieves the newly generated user ID

        # 2. Call Gemini
        prompt = f"""
        You are CosmicTea, a sassy, highly perceptive astrologer.
        The user's name is {request.name}, born on {request.dob} at {request.time} in {request.location}. Gender: {request.gender}.

        Generate their destiny report. Be blunt, slightly humorous, and highly dramatic.
        You MUST output ONLY valid JSON matching this exact structure. Do not include markdown tags.
        {{
            "sun_sign": "Their exact astrological sun sign based on their DOB",
            "career_tea": "A sassy, specific prediction about their career",
            "love_gossip": "Blunt relationship advice based on their chart",
            "karmic_roast": "Playfully calling out their toxic traits"
        }}
        """

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        tea_data = json.loads(response.text)

        # 3. Save the generated Gemini data to the 'reports' table, linked to the user
        new_report = ReportRecord(
            user_id=new_user.id,
            sun_sign=tea_data["sun_sign"],
            career_tea=tea_data["career_tea"],
            love_gossip=tea_data["love_gossip"],
            karmic_roast=tea_data["karmic_roast"],
        )
        db.add(new_report)
        db.commit()

        # 4. Return the data to React
        return TeaResponse(**tea_data)

    except Exception as e:
        db.rollback()  # Undo any database changes if Gemini fails
        print(f"Error generating cosmic data: {e}")
        raise HTTPException(status_code=500, detail="The cosmos are currently unavailable.")
