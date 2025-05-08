"""
CrewAI agents for Invoice generation
"""
from crewai import Agent, Task, Crew, Process
import logging
import os
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from logging_config import get_logger 

logger = logging.getLogger(__name__)
# Define the Pydantic model for the blog
class Invoice(BaseModel):
    invoice_info: str
    sender_name: str
    sender_address: list
    sender_contact:str
    sender_country: str
    sender_tax_num: str
    recipient_name: str
    recipient_address: list
    recipient_contact: str
    recipient_country: str
    recipient_tax_num: str
    due_date: str
    transactions: list
    quantities: list
    unit_prices: list  # Changed to float
    unit_totals: list  # Changed to float
    total: float  # Changed to float
    logo: str
    payment_instructions: str
    invoice_notes: str
    extra_charges: list
    charges_amounts: list
    taxes: list
    tax_values: list
    currency:str

class LegalAnalysis(BaseModel):
    analysis: str


class Invoice_Agents:
    """
    Invoice creator agent using CrewAI.
    """
    
    def __init__(self, invoice_text: str = None,legal_data:str = None,logger = None):
        self.verbose = True
        self.logger = logger or get_logger(__name__)
        self.invoice_text = invoice_text  
        self.legal_data = legal_data
        self.logger.info("Invoice Crew initialized")
        # Test the OpenAI API ke
    def create_agents(self):
        """
        Create a single agent for parsing invoice data.
        
        Returns:
            The invoice parser agent and the legal advisor agent.
        """
        self.logger.info("Creating invoice crew with agents")
        llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.7
        )
        
        invoice_parser = Agent(
            role="Invoice Parser",
            goal="Parse input text to extract invoice information and return it as a structured dictionary.",
            backstory="""You are an expert in parsing and understanding invoice data. 
            You can accurately identify and extract key information from unstructured text.""",
            verbose=self.verbose,
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
            verbose=self.verbose,
            allow_delegation=False,
            llm=llm
        )
        self.logger.info("Created parser and legal analysis agents")
        return invoice_parser,legal_advisor

    def create_task(self, invoice_parser,legal_advisor):
        """
        Create a task for the invoice parser agent.
        
        Args:
            invoice_parser: The invoice parser agent
            
        Returns:
            The parsing task.
        """
        self.logger.info("Creating invoice crew tasks")
        invoice_text = self.invoice_text
        legal_data = self.legal_data
        
        # Create a parsing task for the AI to identify and extract invoice information
        parsing_task = Task(
            description=f"""
            Parse the following invoice text to extract key information:
            
            {invoice_text}
            
            Focus on identifying:
            1. Sender Name
            2. Sender address (as a list,Seperate the different sections as seperate elements in the list, like street name, building name etc)
            3. Sender contact (email address or phone number etc)
            4. Sender Country
            5. Sender tax number
            6. Recipient Name
            7. Recipient address (as a list,Seperate the different sections as seperate elements in the list, like street name, building name etc)
            8. Recipient contact (email address or phone number etc)
            9. Recipient Country
            10. Recipient tax number
            11. Due date (convert to NUM MONTH YEAR e.g. 01 June 2019)
            12. Transactions (as a list)
            13. Quantities (as a list), if none are provided for an item, assume the quanity is 1
            14. Unit prices (as a list)
            15. Unit totals (as a list)
            16. Total amount
            17. Logo filepath or URL
            18. Payment instructions
            19. Invoice notes
            20. Extra charges (just the charges, not the amounts or taxes, have each unique charge be its own element, if its a percentage charge, add the percentage in brackets beside it. e.g., Late Fee(10%))
            21. Charge amounts (just the raw values, if the amout is that of a percentage (if declared as a percentage),add it as a decimal percent and add an appropriate % symbol. e.g. Late Fee 5% -> 0.05%
                And if the charge is negative i.e. a discount, add the value as a negative. e.g. Early discount -$20 -> -20. if none are provided, assume it is 0)
            22. Taxes (provided tax such as VAT, Sales Tax, Goods and services Tax ETC)  if its a percentage charge, add the percentage in brackets beside it. e.g., VAT(10%)
            23. Tax values (write these as decimal tax values e.g. 12% -> 0.12) NO PERCENTAGE SYMBOLS. if none are provided, assume it is 0
            24. Currency (Write as 3 or 4 Letter abbreviation. e.g. USD)


            IMPORTANT:
            1. All list fields must be Python lists, not strings
            2. The total must be a float number
            3. All fields must be present, even if empty
            4. Do not include any additional fields
            5. Do not return a JSON string, return a Python dictionary
            6. For missing information, use empty lists [] for list fields, empty string "" for string fields, and 0.0 for the total
            7. Do not include any comments or explanations in the output
            8. The output must be a valid Python dictionary that can be directly used to create an Invoice object

           
            """,
            agent=invoice_parser,
            expected_output="A Python dictionary matching the Invoice model structure",
            output_json=Invoice
        )
    
        legal_task = Task(
            description=f"""
            Analyse the following invoice text::
            {invoice_text} 

            Make a professional legal analysis on said invoice text, to ensure that it is legally compliant.
            Assess on how compliant the invoice information is to the following legal guidelines:
            {legal_data}

            Use the provided legal guidelines as a guide, but also do your own further research to ensure correctness.

            TAKE INTO ACCOUNT any relevant information under "Transaction notes:"

            If any fields have nothing or are listed as "string", treat them as if there is NO INFORMATION in the field.
        
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
        self.logger.info("Created parser and legal analysis tasks")
        self.logger.info("Crew setup completed")
        return parsing_task,legal_task
    def run_analysis(self):
        """
        Run the invoice parsing using CrewAI.
        
        Returns:
            Dictionary with the parsed and structured invoice data
        """
        logger.info("Starting invoice processing")
            
        if not os.environ.get("OPENAI_API_KEY"):
            logger.error("OpenAI API key is not set")
            return {
                "error": "OpenAI API key is not set. Please provide a valid OpenAI API key."
            }
            
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

        # Convert the output to match the Invoice model
        try:

            
            # Create an Invoice instance to validate the data
            """
            invoice_data = Invoice(
                sender_info=parsed_invoice.get("sender_info", []),
                sender_country=parsed_invoice.get("sender_country", "COUNTRY REQUIRED"),
                recipient_info=parsed_invoice.get("recipient_info", []),
                recipient_country=parsed_invoice.get("recipient_country", "COUNTRY REQUIRED"),
                due_date=parsed_invoice.get("due_date", ""),
                transactions=parsed_invoice.get("transactions", []),
                quantities=parsed_invoice.get("quantities", []),
                unit_prices=parsed_invoice.get("unit_prices", []),
                unit_totals=parsed_invoice.get("unit_totals", []),
                total=parsed_invoice.get("total", 0.0),
                logo=parsed_invoice.get("logo", "None")
            )
            """
            # Convert back to dictionary for return
            

        except Exception as e:
            logger.error(f"Error processing invoice data: {str(e)}")
            return {
                "error": f"Error processing invoice data: {str(e)}"
            }

        logger.info(f"Parsed invoice as dictionary: {parsed_invoice}")

        legal_analysis = advise.kickoff()

        logger.info("Invoice processing complete")
        logger.info(f"Result object: {parsed_invoice}")

        return parsed_invoice, legal_analysis