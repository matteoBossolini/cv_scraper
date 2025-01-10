# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import requests
import json
import os
from docx import Document
from typing import Optional, Dict
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=3)
results_store: Dict[str, dict] = {}

def scrape_cv_task(task_id: str, cv_url: str, report_url: str):
    try:
        # Aggiorna lo stato a running
        results_store[task_id].update({
            "status": "running",
            "progress": "Inizializzazione richiesta",
            "last_update": datetime.now()
        })

        # Timeout lungo per la richiesta a Wordware (4 minuti)
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
            stream=True,
            timeout=240  # 4 minuti
        )
        
        results_store[task_id].update({
            "progress": "Elaborazione risposta",
            "last_update": datetime.now()
        })
        
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
                
                # Aggiorna lo stato ogni 10 secondi
                if (datetime.now() - results_store[task_id]["last_update"]).seconds >= 10:
                    results_store[task_id].update({
                        "progress": "Elaborazione in corso...",
                        "last_update": datetime.now()
                    })
        
        # Salva il risultato finale
        results_store[task_id].update({
            "status": "completed",
            "data": json.loads(output) if output else None,
            "progress": "Completato",
            "last_update": datetime.now()
        })
    except Exception as e:
        results_store[task_id].update({
            "status": "error",
            "error": str(e),
            "last_update": datetime.now()
        })

@app.get("/scrape-cv")
async def scrape_cv_endpoint(cv_url: str, report_url: str):
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    # Inizializza il task nello store
    results_store[task_id] = {
        "status": "initiated",
        "progress": "Task creato",
        "timestamp": datetime.now(),
        "last_update": datetime.now()
    }
    
    # Avvia il task in background
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, scrape_cv_task, task_id, cv_url, report_url)
    
    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "Processing started. Check status at /status endpoint."
    }

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    # Pulizia risultati vecchi (mantieni per 2 ore)
    current_time = datetime.now()
    to_remove = [tid for tid, result in results_store.items() 
                if current_time - result["timestamp"] > timedelta(hours=2)]
    for tid in to_remove:
        results_store.pop(tid, None)
    
    result = results_store.get(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
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