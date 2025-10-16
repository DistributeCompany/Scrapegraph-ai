from scrapegraph_py import Client
from scrapegraph_py.logger import sgai_logger

sgai_logger.set_logging(level="INFO")

# Initialize the client
sgai_client = Client(api_key="sgai-93f3c7ce-1ef5-452c-9c68-ff54e1a25cec")
# SmartScraper request
response = sgai_client.smartscraper(
    website_url="https://people.utwente.nl/o.a.l.eikenbroek?tab=research",
    user_prompt="Extract all publications and their information"
)

# Print the response
print(f"Request ID: {response['request_id']}")
print(f"Result: {response['result']}")
if response.get('reference_urls'):
    print(f"Reference URLs: {response['reference_urls']}")

import json
json_object = json.dumps(response['result'], indent=4)

with open("oskar_publications.json", "w") as outfile:
    outfile.write(json_object)

sgai_client.close()