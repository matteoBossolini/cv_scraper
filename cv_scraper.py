import requests
import json

cv_url = "https://raw.githubusercontent.com/matteoBossolini/cv_scraper/5f3ade33fd280725d068b0e63d85a5503b7adac0/CV.pdf"
report_url = "https://raw.githubusercontent.com/matteoBossolini/cv_scraper/5f3ade33fd280725d068b0e63d85a5503b7adac0/report.pdf"

def main():
    app_id = "8b98f436-09ae-4487-9d4f-11e48d1feebe"
    api_key = "ww-C6tgfbIoZ61nF7FY8Amfv7zUcZthm8Zbuaj2vuvtXR7a9NAlK1fwXy"

    # Execute the prompt
    r = requests.post(f"https://app.wordware.ai/api/released-app/{app_id}/run",
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

    # Ensure the request was successful
    if r.status_code != 200:
        print("Request failed with status code", r.status_code)
        print(json.dumps(r.json(), indent=4))
    else:
        to_print = False
        cv_scraped = False
        report_scraped = False
        output = ""
        for line in r.iter_lines():
            if line:
                content = json.loads(line.decode('utf-8'))
                value = content['value']
                # We can print values as they're generated
                if value['type'] == 'generation':
                    if value['state'] != "start" and value['label'] == "scraped_cv":
                        #print("\nNEW GENERATION -", value['label'])
                        print("cv_scraped")
                        cv_scraped = True
                    elif value['state'] != "start" and value['label'] == "report":
                        #print("\nEND GENERATION -", value['label'])
                        print("report scraped\n")
                        report_scraped = True
                    elif value["label"] == "data_with_index":
                        to_print = True
                    else:
                        to_print = False
                elif value['type'] == "chunk":
                    if to_print:
                        print(value['value'], end="")
                        output += value['value']
        with open('data.json', 'a') as f:
            f.write(output)

if __name__ == '__main__':
    main()
