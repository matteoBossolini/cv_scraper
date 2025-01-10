# main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import requests
import json
import os
from docx import Document
from typing import Optional, Dict
import asyncio
from datetime import datetime, timedelta

app = FastAPI()

# Dizionario per memorizzare i risultati temporaneamente
results_store: Dict[str, dict] = {}

async def scrape_cv(task_id: str, cv_url: str, report_url: str):
    try:
        r = requests.post(
            f"https://app.wordware.ai/api/released-app/{os.getenv('APP_ID')}/run",
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
            headers={"Authorization": f"Bearer {os.getenv('API_KEY')}"},
            stream=True
        )
        
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
        
        results_store[task_id] = {
            "status": "completed",
            "data": json.loads(output) if output else None,
            "timestamp": datetime.now()
        }
    except Exception as e:
        results_store[task_id] = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now()
        }

@app.get("/scrape-cv")
async def scrape_cv_endpoint(background_tasks: BackgroundTasks, cv_url: str, report_url: str):
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    results_store[task_id] = {
        "status": "processing",
        "timestamp": datetime.now()
    }
    
    background_tasks.add_task(scrape_cv, task_id, cv_url, report_url)
    
    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "Processing started. Check status at /status endpoint."
    }

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    # Pulizia risultati vecchi
    current_time = datetime.now()
    to_remove = []
    for tid, result in results_store.items():
        if current_time - result["timestamp"] > timedelta(hours=1):
            to_remove.append(tid)
    for tid in to_remove:
        results_store.pop(tid, None)
    
    result = results_store.get(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if result["status"] == "completed":
        data = result.copy()
        # Rimuovi il risultato dallo store dopo averlo restituito
        results_store.pop(task_id, None)
        return data
    
    return result

@app.post("/generate-resume")
async def generate_resume_endpoint(request: dict):
    try:
        from resume_generator import create_resume
        create_resume(request["data"])
        
        import base64
        with open('resume.docx', 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
        
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