import requests
import os


url = "http://localhost:8000/process-boq"
files = {
    # "file": open(os.path.join("inputs", "BOQ functionality testing BOQ-1.xlsx"), "rb") # Done
    # "file": open(os.path.join("inputs", "Berger-Rishra-BOQ_PA System without Cable-For Animesh.xlsx"), "rb") # Done
    # "file": open(os.path.join("inputs", "1_SBL-Mohali-BOQ-Pipe & Other PUMP HOUSE-05-02-2025.xlsx"), "rb") # Done
    # "file": open(os.path.join("inputs", "BOQ-BPIL-FG WAREHOUSE-GODOWN-COLORANT (1).xlsx"), "rb") # Done
    # "file": open(os.path.join("inputs", "R4_ELECTRICAL OFFER  CITCO (2).xlsx"), "rb") # Not Done, a bit large
}
data = {
    "custom_instructions": "my name is arbaz and I live in india"
}
response = requests.post(url, files=files, data=data)
print(response.json())
