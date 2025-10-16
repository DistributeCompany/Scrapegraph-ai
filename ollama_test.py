from ollama import chat

stream = chat(
    model='gemma3:latest',
    messages=[{'role': 'user', 'content': """"
               
               Given the following text. How confident are you that this is related to Transport & Logistics? Give a Yes or No answer whether I should include it in a 'Transport and Logistics' repository.
               
               Supply chains consist largely of the transport of freight, often using different modalities such as water, rail, air, and road. Freight needs to be transported between the different modalities within the supply chain: from container terminals to distribution centres, or from airports to warehouses. We define short-haul intermodal transportation - transport between modalities as barge, truck, train, or plane, or between terminals and distribution centres, warehouses, or logistic services providers - as hub-to-hub transportation. This research investigates how hub-to-hub logistics can be automated, to reduce daily costs and to make more efficient use of available transport. An approach to enhance the efficiency of hub-to-hub transport is the implementation of Connected Automated Transport (CAT). CAT means transportation solutions for passengers or freight utilizing automation and connectivity.
               
               """}],
    stream=True,
)

for chunk in stream:
  print(chunk['message']['content'], end='', flush=True)