"""
CrewAI agents for Invoice generation
"""
from crewai import Agent, Task, Crew, Process
from typing import Dict, Optional
import logging
import os
import traceback
import openai
import json
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tools.export import export_invoice_to_pdf  

logger = logging.getLogger(__name__)
# Define the Pydantic model for the blog
class Invoice(BaseModel):
    sender_info : list
    sender_country :str
    recipient_info : list
    recipient_country: str
    due_date : str
    transactions : list
    quantities : list
    unit_prices : list
    unit_totals : list
    total : str
    logo: str
    payment_instructions: str
    invoice_notes: str
    charges:str
    charges_value:float
    currency:str

    
class LegalAnalysis(BaseModel):
    analysis: str


class Invoice_Agents:
    """
    Invoice creator agent using CrewAI.
    """
    
    def __init__(self, invoice_text: str,legal_data:str):
        """
        Initialize the invoice processing agent.
        
        Args:
            invoice_text: String containing the invoice information
            openai_api_key: OpenAI API key for CrewAI agents
        """
        self.invoice_text = invoice_text  
        self.legal_data = legal_data
        # Test the OpenAI API ke
    def create_agents(self):
        """
        Create a single agent for parsing invoice data.
        
        Returns:
            The invoice parser agent and the legal advisor agent.
        """
        llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.7
        )
        
        invoice_parser = Agent(
            role="Invoice Parser",
            goal="Parse input text to extract invoice information and return it as a structured dictionary.",
            backstory="""You are an expert in parsing and understanding invoice data. 
            You can accurately identify and extract key information from unstructured text.""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )

        legal_advisor = Agent(
            role="Legal Advisor",
            goal="""Analyse input text and Identify key information that would determine legal requirements, 
            such as the addresses of both sender and recipient, the type of company and all transaction information 
            and return all legal information requirements that the invoice needs such as VAT number etc.""",
            backstory="""You are an expert in legal advice and understanding invoice data. 
            You can accurately identify key information from unstructured text and consult laws regarding an invoice with
            said data..""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )
        
        return invoice_parser,legal_advisor

    def create_task(self, invoice_parser,legal_advisor):
        """
        Create a task for the invoice parser agent.
        
        Args:
            invoice_parser: The invoice parser agent
            
        Returns:
            The parsing task.
        """
        invoice_text = self.invoice_text
        legal_data = self.legal_data
        
        # Create a parsing task for the AI to identify and extract invoice information
        parsing_task = Task(
            description=f"""
            Parse the following invoice text to extract key information:
            
            {invoice_text}
            
            Focus on identifying:
            1. Sender information 
            (Sender information is an array, The first element should be the Person / Company name, The following elements
             Are to be the address information, from smallest to biggest i.e. building(if applicable), street name, Town/ City etc. 
             As long as the address is split evenly between elements. do NOT include the country, this will be a seperate field.)

            2. Sender Country (the country of the sender, if none are provided put COUNTRY REQUIRED in this field insteady)
            3. Recipient information
             (Recipient information is an array, The first element should be the Person / Company name, The following elements
             Are to be the address information, from smallest to biggest i.e. building(if applicable), street name, Town/ City etc. 
             As long as the address is split evenly between elements. do NOT include the country, this will be a seperate field.)

            4. Recipient Country(The country of the recipient, if none are provided put COUNTRY REQUIRED in this field instead)
            5. Due date
            6. Transactions (these must be in singular tense e.g. (products -> product))
            7. quantities
            8. Unit prices (price per individual transaction unit)
            9. totals (the total price of each unique transaction unit)
            10. total (sum total of all transactions)
            11. Company logo (will be a filepath to an image for example logo: FILEPATH"
            12. Sender VAT (if applicable, if none, put "None")
            13. Recipient VAT (if applicable, if none, put "None")


            (Do NOT output currency as words for the transaction totals, instead use the appropriate symbols and include them in 
             unit prices, totals and the total)

            

            (Add capital letters to person names and address names)
            (Write All dates as [NUMBER](add a zero if single digits i.e., 01, 06, etc.)  [NAME OF MONTH] [COMMA] [YEAR NUMBER])
            
            Return the output as a structured dictionary with the keys:
            - sender_info (as a list)
            - sender_country
            - recipient_info (as a list)
            - recipient_country
            - due_date
            - transactions (as a list)
            - quantities (as a list)
            - unit_prices (as a list)
            - unit_totals (as a list)
            - total
            - logo (the provided filepath to the logo image, if none are present put "None" in this field instead)
            - sender_VAT
            - recipient_VAT
            
            
            IMPORTANT: The output must be a valid JSON dictionary. All list fields must be properly formatted as lists.

            IGNORE the legal field, that will be filled seperately, put NONE in it for now
            """,
            agent=invoice_parser,
            expected_output="Structured invoice data dictionary with fields for sender, recipient, due date, and transactions.",
            output_json=Invoice,
        )
        
        
        legal_task = Task(
            description=f"""
            Analyse the following invoice text::
            {invoice_text}

            Make a professional legal analysis on said invoice text, to ensure that it is legally compliant.
            Assess on how compliant the invoice information is to the following legal guidelines:
            {legal_data}

            Use the provided legal guidelines as a guide, but also do your own further research to ensure correctness.
        
            your analysis MUST revolve around THE NATURE OF THE TRANSACTIONS and the COUNTRIES of both SENDER and RECIPIENT.
            this is of utmost importance as the invoice must be legally compliant for BOTH COUNTRIES.

            AND, the nature of the transaction must also be carefully identified as certain invoice laws
            change depending on the transaction. for example, LOANS are EXEMPT from VAT under certain laws.

            NOTE the desceription of the transaction, some countries may require a detailed description while others may not.

            IGNORE the lack of INVOICE NUMBER, it will be automatically generated by a different agent.
            IGNORE the lack of an issue date, it will automatically be generated by a different agent

            Return ONLY the legal analysis as a string. Do not try to recreate the entire invoice data.
            Your response will be added to the 'legal' field of the existing invoice data.

            IMPORTANT: if ALL invoice transactions are exempt from things such as VAT, sales tax, SST, etc.
            then information MANDATORY for said things like a VAT number is NOT mandatory. 

            in that case, mention that the information IS MISSING, but not required.

            The output should be easy to understand and the user should be able to clearly read the analysis
            and intuitively be able to address the issues. Output should NEVER be vague.
            AVOID unsure statements such as "might,maybe etc" where possible.

            IF details are not provided and are NOT mandatory due to the nature of transactions,
            clearly state WHAT details are exempt.

            Output should also be concise, without sacrificing detail and information.
            Not too long but still informative and correct
            """,
            agent=legal_advisor,
            expected_output="A string containing the legal analysis",
            output_json=LegalAnalysis # Changed to False since we're just returning a string
        )
        
        return parsing_task,legal_task
    def run_analysis(self):
        """
        Run the invoice parsing using CrewAI.
        
        Returns:
            Dictionary with the parsed and structured invoice data
        """
        try:
            logger.info("Starting invoice processing")
            
            if not os.environ.get("OPENAI_API_KEY"):
                logger.error("OpenAI API key is not set")
                return {
                    "error": "OpenAI API key is not set. Please provide a valid OpenAI API key."
                }
            
            # Extract countries from the invoice data
            
            # Create both agents
            invoice_parser, legal_advisor = self.create_agents()
            
            # Create both tasks
            parsing_task, legal_task = self.create_task(invoice_parser, legal_advisor)
            
            # Create crew with both agents and tasks
            parse = Crew(
                agents=[invoice_parser],
                tasks=[parsing_task],
                verbose=True,
                process=Process.sequential
            )

            advise = Crew(
                agents=[legal_advisor],
                tasks=[legal_task],
                verbose=True,
                process=Process.sequential
            )
            
            # Run the crew and get results directly
            logger.info("Running CrewAI invoice processing")
            parsed_invoice = parse.kickoff()
            
            legal_analysis = advise.kickoff()

            logger.info("Invoice processing complete")
            logger.info(f"Result object: {parsed_invoice}")


            
            return parsed_invoice,legal_analysis
            
        except Exception as e:
            logger.error(f"Error in run_analysis: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "error": f"Error during analysis: {str(e)}"
            }