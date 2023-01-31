# example of code for deploying a langchain agent with replit 
# https://replit.com/@llamalabs/langchain-agent this will be template public link on replit once ready for launch 
# https://langchain-agent.llamalabs.repl.co/ this is the public link to the agent once deployed


import re
import json
import os


from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from flask import Flask, request, Response


app = Flask(__name__)

QUERIES = {
  "queries": ["What is a good name for a company that builds cookies?",
  "What is a good name for a company that builds books?"]
}

# set OpenAI API key in secrets tab on replit 
# OPENAI_API_KEY = 'your_key'
my_secret = os.environ['OPENAI_API_KEY']

llm = OpenAI(temperature=0.9)

# construct an LLMChain which takes user input, formats it with a PromptTemplate,
# and then passes the formatted response to an LLM
prompt = PromptTemplate(
    input_variables=["product"],
    template="What is a good name for a company that builds {product}?",
)
chain = LLMChain(llm=llm, prompt=prompt)


def get_chain_response(product: str):
  response = chain.run(product)
  print(f"AI-generated name: {response.strip()}")
  return response


@app.route('/', methods=['GET', 'POST'])
def index():
  if request.method == "GET":
    return Response(json.dumps(QUERIES), mimetype='application/json')
  elif request.method == "POST":
    obj = request.json
    #this extracts a product from the message text if it is written between square brackets 
    #example: "What should I call a company that makes[product]"
    product = re.search(r'\[(.*?)\]', obj["message"]["text"])[0]  
  response = get_chain_response(product)
  return {"message": {"text": f"{response.strip()}"}}



app.run(host='0.0.0.0', port=81)