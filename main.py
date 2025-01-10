# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import requests
import json
import os
from docx import Document
from typing import Optional

app = FastAPI()

class CVRequest(BaseModel):
    cv_url: str
    report_url: str
    app_id: str
    api_key: str

class ResumeRequest(BaseModel):
    data: dict

async def scrape_cv(cv_url: str, report_url: str, app_id: str, api_key: str):
    r = requests.post(
        f"https://app.wordware.ai/api/released-app/{app_id}/run",
        json={
            "inputs": {
                "CV": {
                    "type": "file",
                    "file_type": "application/pdf",
                    "file_url": cv_url,
                    "file_name": "CV"
                },
                "report": {
                    "type": "file",
                    "file_type": "application/pdf",
                    "file_url": report_url,
                    "file_name": "report"
                },
                "version": "^1.1"
            }
        },
        headers={"Authorization": f"Bearer {api_key}"},
        stream=True
    )
    
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail="Scraping failed")
    
    output = ""
    to_print = False
    for line in r.iter_lines():
        if line:
            content = json.loads(line.decode('utf-8'))
            value = content['value']
            if value['type'] == 'generation':
                if value["label"] == "data_with_index":
                    to_print = True
                else:
                    to_print = False
            elif value['type'] == "chunk" and to_print:
                output += value['value']
    
    return json.loads(output) if output else None

@app.post("/scrape-cv")
async def scrape_cv_endpoint(request: CVRequest):
    try:
        data = await scrape_cv(
            request.cv_url,
            request.report_url,
            request.app_id,
            request.api_key
        )
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-resume")
async def generate_resume_endpoint(request: ResumeRequest):
    try:
        from resume_generator import create_resume
        create_resume(request.data)
        
        # Read the generated file and return it as base64
        import base64
        with open('resume.docx', 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
        
        # Clean up
        if os.path.exists('resume.docx'):
            os.remove('resume.docx')
            
        return {
            "status": "success",
            "file": encoded,
            "filename": "resume.docx"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# requirements.txt
"""
fastapi==0.68.0
uvicorn==0.15.0
requests==2.31.0
python-docx==0.8.11
pydantic==1.8.2
python-multipart==0.0.5
"""

# Procfile
"""
web: python main.py
"""

# runtime.txt
"""
python-3.9.16
"""