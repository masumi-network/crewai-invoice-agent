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
from litellm.exceptions import RateLimitError  # Import the RateLimitError

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
    sender_tax_number:str
    recipient: str
    recipient_address: str
    recipient_country: str
    recipient_contact: str
    recipient_tax_number:str
    due_date: str
    transactions:str
    logo: str
    payment_instructions:str
    invoice_notes:str
    extra_charges: str
    taxes: str
    transaction_notes:str
    currency:str
    


class ProvideInputRequest(BaseModel):
    job_id: str
    sender: str
    sender_address: str
    sender_country: str
    sender_contact: str
    sender_tax_number:str
    recipient: str
    recipient_address: str
    recipient_country: str
    recipient_contact: str
    recipient_tax_number:str
    due_date: str
    transactions:str
    logo: str
    payment_instructions:str
    invoice_notes:str
    extra_charges: str
    taxes: str
    transaction_notes:str
    currency:str

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

    invoice_dictionary = {
        "sender": str(request_body.sender),
        "sender_address": str(request_body.sender_address),
        "sender_country": str(request_body.sender_country),
        "sender_contact": str(request_body.sender_contact),
        "sender_tax_number": str(request_body.sender_tax_number),
        "recipient": str(request_body.recipient),
        "recipient_address": str(request_body.recipient_address),
        "recipient_country": str(request_body.recipient_country),
        "recipient_contact": str(request_body.recipient_contact),
        "recipient_tax_number": str(request_body.recipient_tax_number),
        "due_date": str(request_body.due_date),
        "transactions": str(request_body.transactions),
        "logo": str(request_body.logo),
        "payment_instructions": str(request_body.payment_instructions),
        "invoice_notes": str(request_body.invoice_notes),
        "extra_charges": str(request_body.extra_charges),
        "taxes": str(request_body.taxes),
        "transaction_notes": str(request_body.transaction_notes),
        "currency": str(request_body.currency)
    }



    # For demonstration: set job status to 'awaiting payment'
    invoice_info = f"""
    Sender: {invoice_dictionary["sender"]}
    Sender Address: {invoice_dictionary["sender_address"]}
    Sender Country: {invoice_dictionary["sender_country"]}
    Sender Contact: {invoice_dictionary["sender_contact"]}
    Sender tax number: {invoice_dictionary["sender_tax_number"]}
    
    Recipient: {invoice_dictionary["recipient"]}
    Recipient Address: {invoice_dictionary["recipient_address"]}
    Recipient Country: {invoice_dictionary["recipient_country"]}
    Recipient Contact: {invoice_dictionary["recipient_contact"]}
    Recpient tax number: {invoice_dictionary["recipient_tax_number"]}
 
    Due Date: {invoice_dictionary["due_date"]}
    
    Transactions: {invoice_dictionary["transactions"]}
    
    Logo: {invoice_dictionary["logo"]}
    Payment Instructions: {invoice_dictionary["payment_instructions"]}
    Invoice Notes: {invoice_dictionary["invoice_notes"]}

    Extra Charges: {invoice_dictionary["extra_charges"]}

    Taxes: {invoice_dictionary["taxes"]}

    Transaction_notes: {invoice_dictionary["transaction_notes"]}

    Currency: {invoice_dictionary["currency"]}

    """
    
    jobs[job_id] = {
        "status": "awaiting payment",
        "payment_id": payment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
        "invoice_info": invoice_dictionary,
        "legal_analysis": None
    }

    # Here you invoke your crew
    
    legal_info = search_invoice_regulations(request_body.sender_country, request_body.recipient_country)
    cleaning_crew = Cleaning_Agents(legal_info['content'])
    legal_info = cleaning_crew.clean_Data()
        
    invoice_crew = Invoice_Agents(invoice_info, legal_info)
        
        # Attempt to run analysis and unpack results
    result,analysis = invoice_crew.run_analysis()

    # Initialize extra_info in the result
     # Initialize an empty list for extra information

    InvoicePDF = export_invoice_to_pdf(result)
    
    # Store the generated PDF
    jobs[job_id]["result"] = InvoicePDF
    jobs[job_id]["status"] = "success"
    jobs[job_id]["legal_analysis"] = legal_info
    
    
    return {
        "status": "success",
        "job_id": job_id,
        "current_pdf": InvoicePDF,
        "Invoice Analysis": analysis
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
    Allows users to send additional input.
    Fulfills MIP-003 /provide_input endpoint.
    
    In this example we can add any additional info to the invoice, or fill in any required information.
    """
    job_id = request_body.job_id

    if job_id not in jobs:
        return {"status": "error", "message": "Job not found"}

    job = jobs[job_id]

    
    # Append new information to the Additional Info field

        # Update the invoice_info with the new additional info


    input_data = request_body.model_dump()

    # Iterate over the input data and update the invoice_dictionary
    for key, value in input_data.items():
        if value not in [None, "string"]:  # Check if value is not None and not "string"
            job["invoice_info"][key] = value
        """    
        job_id: str
        sender: str
        sender_address: str
        sender_country: str
        sender_contact: str
        sender_tax_number:str
        recipient: str
        recipient_address: str
        recipient_country: str
        recipient_contact: str
        recipient_tax_number:str
        due_date: str
        transactions:str
        logo: str
        payment_instructions:str
        invoice_notes:str
        extra_charges: str
        taxes: str
        transaction_notes:str
        currency:str
        """
        # Update the Invoice_Agents crew with the modified invoice_info
    invoice_info = f"""
    Sender: {job["invoice_info"]["sender"]}
    Sender Address: {job["invoice_info"]["sender_address"]}
    Sender Country: {job["invoice_info"]["sender_country"]}
    Sender Contact: {job["invoice_info"]["sender_contact"]}
    Sender tax number: {job["invoice_info"]["sender_tax_number"]}
    
    Recipient: {job["invoice_info"]["recipient"]}
    Recipient Address: {job["invoice_info"]["recipient_address"]}
    Recipient Country: {job["invoice_info"]["recipient_country"]}
    Recipient Contact: {job["invoice_info"]["recipient_contact"]}
    Recpient tax number: {job["invoice_info"]["recipient_tax_number"]}

    Due Date: {job["invoice_info"]["due_date"]}
    
    Transactions: {job["invoice_info"]["transactions"]}
        
    Logo: {job["invoice_info"]["logo"]}
    Payment Instructions: {job["invoice_info"]["payment_instructions"]}
    Invoice Notes: {job["invoice_info"]["invoice_notes"]}

    Extra Charges: {job["invoice_info"]["extra_charges"]}

    Taxes: {job["invoice_info"]["taxes"]}

    Transaction_notes: {job["invoice_info"]["transaction_notes"]}

    Currency: {job["invoice_info"]["currency"]}

    """
    invoice_crew = Invoice_Agents(invoice_info, job["legal_analysis"])

    result, legal = invoice_crew.run_analysis()  # Re-run analysis with updated info



    
    InvoicePDF = export_invoice_to_pdf(result)
    
    #Update job with new result
    job["result"] = InvoicePDF
    job["status"] = "Success"


    return {
        "status": "awaiting input",
        "job_id": job_id,
        "current_pdf": InvoicePDF,
        "legal_analysis":legal
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
        sample_invoice = {
    "sender_info": [
        "Franz Shih.",
        "198 New Seskin Court", 
        "Whitestown Way"
    ],
    "sender_country": "Ireland",
    "recipient_info": [
        "utxo AG",
        "Döttingerstrasse 21",
        "CH5303 Würenlingen"
    ],
    "recipient_country": "Switzerland",
    "due_date": "02/05/25",
    "transactions": [
        "Customer service",
        "NMKR agent",
        "Masumi Payment"
    ],
    "quantities": [
        "1""""""",  # Assuming each transaction is for one unit
        "2",
        "1"
    ],
    "unit_prices": [
        "30.00",
        "40.00",
        "25.00"
    ],
    "unit_totals": [
        "30.00",
        "40.00",
        "25.00"
    ],
    "total": "95.00",  # Total of all transactions
    "logo": "C:/Users/hungl/Downloads/logo.png",
    "reciever_VAT": "CH VAT CHE494.509.135 MWST",
    "payment_notes":"IBAN: CH30 0857 3102 5022 0181 4"
      # Placeholder for legal analysis
}

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
            """   
            # Export to PDF
        export_path = export_invoice_to_pdf(sample_invoice)
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
