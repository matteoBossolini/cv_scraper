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
            "message": "Inizializzazione richiesta",
            "last_update": datetime.now()
        })

        # Configurazione della richiesta con timeout esteso
        session = requests.Session()
        session.timeout = 300  # 5 minuti timeout

        r = session.post(
            f"https://app.wordware.ai/api/released-app/{os.getenv('APP_ID', '8b98f436-09ae-4487-9d4f-11e48d1feebe')}/run",
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
            headers={"Authorization": f"Bearer {os.getenv('API_KEY', 'ww-C6tgfbIoZ61nF7FY8Amfv7zUcZthm8Zbuaj2vuvtXR7a9NAlK1fwXy')}"},
            stream=True
        )
        
        if r.status_code != 200:
            raise Exception(f"Wordware API error: {r.status_code}")
        
        results_store[task_id].update({
            "message": "Elaborazione risposta in corso",
            "last_update": datetime.now()
        })
        
        output = ""
        to_print = False
        chunk_count = 0
        last_update = datetime.now()

        for line in r.iter_lines():
            if line:
                try:
                    content = json.loads(line.decode('utf-8'))
                    value = content['value']
                    
                    # Aggiorna lo stato ogni 5 secondi
                    current_time = datetime.now()
                    if (current_time - last_update).seconds >= 5:
                        results_store[task_id].update({
                            "message": f"Processati {chunk_count} chunks...",
                            "last_update": current_time
                        })
                        last_update = current_time

                    if value['type'] == 'generation':
                        if value["label"] == "data_with_index":
                            to_print = True
                        else:
                            to_print = False
                    elif value['type'] == "chunk" and to_print:
                        output += value['value']
                        chunk_count += 1
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error processing chunk: {str(e)}")
                    continue

        if output:
            results_store[task_id].update({
                "status": "completed",
                "data": json.loads(output),
                "message": "Elaborazione completata",
                "last_update": datetime.now()
            })
        else:
            raise Exception("No output generated")

    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(error_message)
        results_store[task_id].update({
            "status": "error",
            "error": error_message,
            "last_update": datetime.now()
        })

@app.get("/scrape-cv")
async def scrape_cv_endpoint(cv_url: str, report_url: str):
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    results_store[task_id] = {
        "status": "initiated",
        "message": "Task creato",
        "timestamp": datetime.now(),
        "last_update": datetime.now()
    }
    
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, scrape_cv_task, task_id, cv_url, report_url)
    
    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "Processing started. Check status at /status endpoint."
    }

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    # Pulizia risultati molto vecchi (24 ore)
    current_time = datetime.now()
    to_remove = []
    for tid, result in results_store.items():
        if current_time - result["timestamp"] > timedelta(hours=24):
            to_remove.append(tid)
    for tid in to_remove:
        results_store.pop(tid, None)
    
    result = results_store.get(task_id)
    if not result:
        raise HTTPException(
            status_code=404, 
            detail={"error": "Task not found", "message": "The task might have expired or was never created"}
        )
    
    # Se il task è completato o in errore, mantienilo per altri 10 minuti
    if result["status"] in ["completed", "error"]:
        if current_time - result["last_update"] > timedelta(minutes=10):
            results_store.pop(task_id, None)
            raise HTTPException(
                status_code=404,
                detail={"error": "Task expired", "message": "The completed task has been cleared from memory"}
            )
    
    return result

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)