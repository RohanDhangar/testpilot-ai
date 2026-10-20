from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from app.services.requirement_analysis import requirement_analysis
from app.services.code_generation import code_genration

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  
        "http://127.0.0.1:5173",  
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET","POST"],
    allow_headers=["Content-Type"],
)

# class inputRequest(BaseModel):
#     prompt: str

class GenerateTestRequest(BaseModel):
    url: HttpUrl
    requirement: str


@app.get("/")
def read_root():
    return {"message": "Hello, this is my first FastAPI response"}

@app.post("/response")
def create_response(data: GenerateTestRequest):
    return {
        "status": "success",
        "data": data
    }

@app.post("/generate-test")
async def generate_test(data: GenerateTestRequest):
    if not data.requirement.strip():
        return {
            "status": "error",
            "message": "Testing requirement cannot be empty.",
        }

    try:
        analysis_result = await requirement_analysis(data.requirement.strip())

        if not isinstance(analysis_result, dict) or analysis_result.get("status") != "success":
            return {
                "status": "error",
                "stage": "requirement_analysis",
                "message": "Requirement analysis failed.",
                "details": analysis_result,
            }

        generation_result = await code_genration(str(data.url), analysis_result)

        if not isinstance(generation_result, dict) or generation_result.get("status") != "success":
            return {
                "status": "error",
                "stage": "code_generation",
                "message": "Code generation or syntax validation failed.",
                "details": generation_result,
            }

        return {
            "status": "success",
            "url": str(data.url),
            "requirement": data.requirement.strip(),
            "test_plan": generation_result.get("test_plan"),
            "generated_code": generation_result.get("generated"),
            "validation": generation_result.get("validation")
        }
    except Exception:
        import logging
        logging.exception("Unexpected failure in /generate-test")
        return {
            "status": "error",
            "message": "An unexpected error occurred while generating the test.",
        }