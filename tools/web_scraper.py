from crewai_tools import ScrapeWebsiteTool
from crewai_tools import SerperDevTool
from dotenv import load_dotenv

load_dotenv()
# Initialize the tool for internet searching capabilities

webCrawler = SerperDevTool(
	n_results=1
)

def scrape_websites(url):
    webScraper = ScrapeWebsiteTool(url)
    content = webScraper.run() 
    return content


def search_invoice_regulations(sender_country: str,recipient_country:str):
    regulations = {
        'content': ''  # Initialize the content key as an empty list
    }
    links = []
    
    if sender_country == recipient_country:
        query = f"Invoice regulations in {sender_country}"
        results = webCrawler.run(search_query= query)
        print("RESULTO SHIYOU:  ",results)

        for item in results['organic']:
            sender_links.append(item['link'])
        for link in links:
            regulations['content']+=(scrape_websites(link))
    else:
            # Search for sender country regulations
        sender_query = f"Invoice regulations in {sender_country}"
        sender_results = webCrawler.run(search_query= sender_query)
        print("SEARCHO QUERYO   :",sender_query)
        print("RESULTO SHIYOU:  ",sender_results)
        sender_links = []
        for item in sender_results['organic']:
            sender_links.append(item['link'])

        for link in sender_links:
            regulations['content']+=(scrape_websites(link))

        print("REGULATIONS SHIYOU:  ",regulations['content'])
        # Search for recipient country regulations
        recipient_query = f"Invoice regulations in {recipient_country}"
        recipient_results = webCrawler.run(search_query= recipient_query)
        reciever_links = []
        for item in recipient_results['organic']:
            reciever_links.append(item['link'])
           
        for link in reciever_links:
            regulations['content']+=(scrape_websites(link))


      

    return regulations


