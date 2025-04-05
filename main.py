"""
CrewAI Invoice generator Agent
"""
import os
import logging
import uuid
import uvicorn
import traceback
from typing import Dict,List, Optional
from agents.invoice_analyst import Invoice_Agents
from tools.export import export_invoice_to_pdf  
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime, timezone
from tools.web_scraper import search_invoice_regulations
from agents.data_cleaner import Cleaning_Agents

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Retrieve OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI
app = FastAPI()

# ─────────────────────────────────────────────────────────────────────────────
# Temporary in-memory job store (DO NOT USE IN PRODUCTION)
# ─────────────────────────────────────────────────────────────────────────────
jobs = {}

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class KeyValuePair(BaseModel):
    key: str
    value: str

class StartJobRequest(BaseModel):
    # Per MIP-003, input_data should be defined under input_schema endpoint
    sender: str
    sender_address: str
    sender_country: str
    sender_contact: str
    recipient: str
    recipient_address: str
    recipient_contact: str
    recipient_country: str
    due_date: str
    transactions:str
    logo: str
    


class ProvideInputRequest(BaseModel):
    job_id: str
    text: str

# ─────────────────────────────────────────────────────────────────────────────
# 1) Start Job (MIP-003: /start_job)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/start_job")
async def start_job(request_body: StartJobRequest):
    """
    Initiates a job with specific input data.
    Fulfills MIP-003 /start_job endpoint.
    """
    if not OPENAI_API_KEY:
        return {"status": "error", "message": "Missing OpenAI API Key. Check your .env file."}

    # Generate unique job & payment IDs
    job_id = str(uuid.uuid4())
    payment_id = str(uuid.uuid4())  # Placeholder, in production track real payment

    # For demonstration: set job status to 'awaiting payment'
    invoice_info = f"""
    Sender: {request_body.sender}
    Sender Address: {request_body.sender_address}
    Sender Contact: {request_body.sender_contact}
    Sender Contact: {request_body.sender_country}
    
    Recipient: {request_body.recipient}
    Recipient Address: {request_body.recipient_address}
    Recipient Country: {request_body.recipient_country}
    Recipient Contact: {request_body.recipient_contact}
    
    Due Date: {request_body.due_date}
    
    Transactions: {request_body.transactions}
    
    Logo: {request_body.logo}
    """
    
    jobs[job_id] = {
        "status": "awaiting payment",
        "payment_id": payment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_data": invoice_info,
        "result": None
    }

      # Here you invoke your crew
      
   
    if invoice_info.strip() == "Complete":
        jobs[job_id]["status"] = "completed"
        return {
            "status": "success",
            "job_id": job_id
        }
    
    
    legal_info = search_invoice_regulations(request_body.sender_country,request_body.recipient_country)

    cleaning_crew = Cleaning_Agents(legal_info['content'])

    legal_info = cleaning_crew.clean_Data()
    
    invoice_crew = Invoice_Agents(invoice_info,legal_info)
    
    result,legal = invoice_crew.run_analysis()

    InvoicePDF = export_invoice_to_pdf(result)
    
    # Store the generated PDF
    jobs[job_id]["result"] = InvoicePDF
    jobs[job_id]["status"] = "awaiting input"

    # Check if user wants to continue or complete
    return {
        "status": "awaiting input",
        "job_id": job_id,
        "current_pdf": InvoicePDF,
        "Invoice Analysis": legal['analysis']
    }

# ─────────────────────────────────────────────────────────────────────────────
# 2) Check Job Status (MIP-003: /status)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/status")
async def check_status(job_id: str = Query(..., description="Job ID to check status")):
    """
    Retrieves the current status of a specific job.
    Fulfills MIP-003 /status endpoint.
    """
    if job_id not in jobs:
        # Return 404 in a real system; here, just return a JSON error
        return {"error": "Job not found"}

    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "result": job["result"]  # Optional in MIP-003, included if available
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3) Provide Input (MIP-003: /provide_input)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/provide_input")
async def provide_input(request_body: ProvideInputRequest):
    """
    Allows users to send additional input if a job is in an 'awaiting input' status.
    Fulfills MIP-003 /provide_input endpoint.
    
    In this example we do not require any additional input, so it always returns success.
    """
    job_id = request_body.job_id

    if job_id not in jobs:
        return {"status": "error", "message": "Job not found"}

    job = jobs[job_id]

    if job["status"] != "awaiting input":
        return {"status": "error", "message": "Job is not awaiting input"}
    
    if request_body.text.strip() == "Complete":
        job["status"] = "completed"
        return {
            "status": "success",
            "job_id": job_id,
            "final_pdf": job["result"]
        }
    
   

    crew = Invoice_Agents(request_body.text)
    result = crew.run_analysis()

    InvoicePDF = export_invoice_to_pdf(result)
    
    # 5. Update job with new result
    job["result"] = InvoicePDF
    job["status"] = "awaiting input"

    return {
        "status": "awaiting input",
        "job_id": job_id,
        "current_pdf": InvoicePDF
    }

   
   

# ─────────────────────────────────────────────────────────────────────────────
# 4) Check Server Availability (MIP-003: /availability)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/availability")
async def check_availability():
    """
    Checks if the server is operational.
    Fulfills MIP-003 /availability endpoint.
    """
    # Simple placeholder. In a real system, you might run
    # diagnostic checks or return server load info.
    return {
        "status": "available",
        "message": "The server is running smoothly."
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5) Retrieve Input Schema (MIP-003: /input_schema)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/input_schema")
async def input_schema():
    """
    Returns the expected input schema for the /start_job endpoint.
    Fulfills MIP-003 /input_schema endpoint.
    """
    # Example response defining the accepted key-value pairs
    schema_example = {
        "input_data": [
            {"key": "text", "value": "string"}
        ]
    }
    return schema_example

# ─────────────────────────────────────────────────────────────────────────────
# Main logic if called as a script
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY is missing. Please check your .env file.")
        return
    """
    invoice_text = str(input("Enter invoice information:\n"))

    if not invoice_text.strip():
        print("Invoice data is required.")
        return
        
    """
    try:
        text = tool.run()
        print(text)

        # Create invoice processing agents
        """
        agents = Invoice_Agents(invoice_text)
        
        # Run analysis
        results = agents.run_analysis()

        print(results['legal'])
        
        # Check for errors
        print("Here is your Invoice PDF: {export_path}")
        if "error" in results:
            print(f"Error processing invoice: {results['error']}")
        else:
            print("Invoice processed successfully!")
            
            # Export to PDF
            export_path = export_invoice_to_pdf(results)
            print(f"Invoice exported to PDF: {export_path}")
    """
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        print(f"Error processing invoice: {error_msg}")
        print("Error details:")
        print(stack_trace)
        logger.error(f"Error processing invoice: {e}", exc_info=True)
        

if __name__ == "__main__":
    import sys

    # If 'api' argument is passed, start the FastAPI server
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        print("Starting FastAPI server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        main()
