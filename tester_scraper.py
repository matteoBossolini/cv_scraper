import requests
import json
import time
from datetime import datetime

def test_scrape_cv():
    # URL dell'API Heroku
    base_url = "https://cvagent-f426ea5e541a.herokuapp.com"
    
    # URL dei documenti
    cv_url = "https://raw.githubusercontent.com/matteoBossolini/cv_scraper/5f3ade33fd280725d068b0e63d85a5503b7adac0/CV.pdf"
    report_url = "https://raw.githubusercontent.com/matteoBossolini/cv_scraper/5f3ade33fd280725d068b0e63d85a5503b7adac0/report.pdf"
    
    try:
        print(f"{datetime.now()} - Avvio processo di scraping...")
        response = requests.get(f"{base_url}/scrape-cv?cv_url={cv_url}&report_url={report_url}")
        
        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data["task_id"]
            print(f"{datetime.now()} - Task avviato con ID: {task_id}")
            
            # Attendi 2 secondi prima di iniziare il polling
            print(f"{datetime.now()} - Attendo l'inizializzazione del task...")
            time.sleep(2)
            
            # Poll dello stato
            start_time = time.time()
            max_wait_time = 600  # 10 minuti
            polling_interval = 60  # 1 minuto tra i controlli
            
            while True:
                elapsed_time = time.time() - start_time
                if elapsed_time > max_wait_time:
                    print(f"\n{datetime.now()} - Timeout raggiunto dopo {int(elapsed_time)} secondi")
                    break
                
                print(f"\n{datetime.now()} - Controllo stato... (minuti trascorsi: {int(elapsed_time/60)})")
                
                try:
                    status_response = requests.get(f"{base_url}/status/{task_id}")
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        current_status = status_data.get("status", "")
                        message = status_data.get("message", "")
                        
                        print(f"Stato: {current_status}")
                        print(f"Messaggio: {message}")
                        
                        if current_status == "completed":
                            print(f"\n{datetime.now()} - Processo completato!")
                            print("\nRisultato:")
                            print(json.dumps(status_data, indent=2))
                            
                            with open('api_test_result.json', 'w') as f:
                                json.dump(status_data, f, indent=2)
                            print("\nRisultato salvato in 'api_test_result.json'")
                            return True
                            
                        elif current_status == "error":
                            print(f"\n{datetime.now()} - Errore durante l'elaborazione: {status_data.get('error')}")
                            return False
                            
                    elif status_response.status_code == 404:
                        print(f"Task non trovato o scaduto. Dettagli: {status_response.json()}")
                        if elapsed_time < 300:  # Se sono passati meno di 5 minuti, continua
                            print("Continuo a controllare...")
                            time.sleep(polling_interval)
                            continue
                        return False
                    else:
                        print(f"Errore imprevisto: {status_response.status_code}")
                        print(status_response.text)
                        if elapsed_time < 300:  # Se sono passati meno di 5 minuti, continua
                            print("Continuo a controllare...")
                            time.sleep(polling_interval)
                            continue
                        return False
                        
                except Exception as e:
                    print(f"Errore durante il controllo dello stato: {str(e)}")
                    if elapsed_time < 300:  # Se sono passati meno di 5 minuti, continua
                        print("Continuo a controllare...")
                        time.sleep(polling_interval)
                        continue
                    return False
                    
                time.sleep(polling_interval)
                
            return False
        else:
            print(f"\n{datetime.now()} - Errore nell'avvio del processo: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\n{datetime.now()} - Errore durante l'esecuzione: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_scrape_cv()
    if not success:
        print("\nIl processo non è stato completato con successo")