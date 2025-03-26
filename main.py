"""
CrewAI Invoice generator Agent
"""
import os
import logging
import uuid
import uvicorn
import traceback
from typing import Dict,List, Optional
from agents.agents import Invoice_Agents
from tools.export import export_invoice_to_pdf  
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime, timezone


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
    text: str

class ProvideInputRequest(BaseModel):
    job_id: str

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
    jobs[job_id] = {
        "status": "awaiting payment",  # Could also be 'awaiting payment', 'running', etc.
        "payment_id": payment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_data": request_body.text,
        "result": None
    }
      # Here you invoke your crew
    
    invoice_info = {"text": request_body.text}
    crew = Invoice_Agents(invoice_info)
    result = crew.run_analysis()

    InvoicePDF = export_invoice_to_pdf(result)


    # Store result as if we immediately completed it (placeholder)
    jobs[job_id]["status"] = "completed"
    jobs[job_id]["result"] = InvoicePDF

    return {
        "status": "success",
        "job_id": job_id,
        "payment_id": payment_id
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

    return {"status": "success"}

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

    invoice_text = str(input("Enter invoice information:\n"))

    if not invoice_text.strip():
        print("Invoice data is required.")
        return
        
    
    try:
        # Create invoice processing agents
        agents = Invoice_Agents(invoice_text)
        
        # Run analysis
        results = agents.run_analysis()
        

        
            

        # Check for errors
        print("Here is your Invoice PDF: {export_path}")
        if "error" in results:
            print(f"Error processing invoice: {results['error']}")
        else:
            print("Invoice processed successfully!")
            
            # Export to PDF
            export_path = export_invoice_to_pdf(results)
            print(f"Invoice exported to PDF: {export_path}")
    
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
