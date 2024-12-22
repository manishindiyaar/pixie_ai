import os
from typing import List
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Document, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.nvidia import NVIDIA
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.core.llms import ChatMessage
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# LLM = NVIDIA(
#     base_url=os.getenv("NVIDIA_BASE_URL"),
#     api_key=os.getenv("NVIDIA_API_KEY"),
#     model="meta/llama3-8b-instruct"
# )

LLM = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    model="gpt-35-turbo-16k",
    api_version="2024-05-01-preview",
    deployment_name="gpt-4"
)


DATA_FILE = "data/me.txt"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return file.read()
    return ""

def save_data(content):
    with open(DATA_FILE, "a") as file:
        file.write(content + "\n")

def knowledge_agent():
    def knowledge_retriever(query):
        data = load_data()
        documents = [Document(text=data)]

        Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
        Settings.llm = LLM

        index = VectorStoreIndex.from_documents(documents)
        query_engine = index.as_query_engine()
        response = query_engine.query(query)
        
        return response.response

    return knowledge_retriever

def orchestrator_agent(user_input, history=[]):
    system_prompt = """
    You are an AI agent's brain. Your goal is to analyze the best next action based on user input & past chat history.
    You should output one of the following categories only, nothing else:
    
    - can_be_answered: user's input doesn't include any question that requires external knowledge retrieval.
    - knowledge_retrieval: the user's input requires additional knowledge outside of this chat history.
    - additional_useful_data: the user's input requires additional data to be saved in the data directory so that it can be used in the future.
    """
    messages = [
        ChatMessage(role="system", content=system_prompt),
    ] + history + [
        ChatMessage(role="user", content=f"NEW USER INPUT: {user_input}")
    ]
    resp = LLM.chat(messages)
    decision = resp.message.content.strip()
    logging.info(f"Orchestrator decision: {decision}")
    return decision

def answer(user_input, history=[]):
    messages = history + [ChatMessage(role="user", content=f"New user Input:{user_input}")]
    resp = LLM.chat(messages)
    return resp.message.content

def learn(user_input):
    new_info = f"Learned: {user_input}"
    save_data(new_info)
    return f"I've learned: {user_input}"

def draft_message(user_input: str, history: List[dict] = []) -> str:
    chat_history = [ChatMessage(role="user" if msg['user'] != 'AI' else "assistant", content=msg['text']) for msg in history]
    
    orchestration_response = orchestrator_agent(user_input, history=chat_history)
    logging.info(f"Orchestrator response: {orchestration_response}")
    
    if orchestration_response == "knowledge_retrieval":
        logging.info("Performing knowledge retrieval")
        agent = knowledge_agent()
        response = str(agent(user_input))

    elif orchestration_response == "additional_useful_data":
        logging.info("Learning new information")
        response = learn(user_input)

    elif orchestration_response == "can_be_answered":
        logging.info("Answering based on existing knowledge")
        response = answer(user_input, history=chat_history)
    
    else:
        logging.warning(f"Unexpected orchestrator response: {orchestration_response}")
        response = "I'm not sure how to respond to that. Can you please rephrase your question?"
    
    logging.info(f"Generated response: {response[:50]}...")  # Log first 50 characters of response
    return response



# Test the draft_message function
def test_draft_message():
    print("Starting tests for draft_message function...")

    # Test case 1: Simple question (can_be_answered)
    input1 = "What is your name?"
    print(f"\nTest 1 - Simple question: '{input1}'")
    response1 = draft_message(input1)
    print(f"Response: {response1}")

    # Test case 2: Knowledge retrieval question
    input2 = "What do you know about Bladex AI?"
    print(f"\nTest 2 - Knowledge retrieval: '{input2}'")
    response2 = draft_message(input2)
    print(f"Response: {response2}")

    # Test case 3: Learning new information
    input3 = "Remember that my favorite color is blue"
    print(f"\nTest 3 - Learning new info: '{input3}'")
    response3 = draft_message(input3)
    print(f"Response: {response3}")

    # Test case 4: Follow-up question (with history)
    input4 = "What did I just tell you about my favorite color?"
    history = [
        {"user": "Human", "text": input3},
        {"user": "AI", "text": response3}
    ]
    print(f"\nTest 4 - Follow-up question: '{input4}'")
    response4 = draft_message(input4, history)
    print(f"Response: {response4}")

    # Test case 5: Unclear input
    input5 = "asdfghjkl"
    print(f"\nTest 5 - Unclear input: '{input5}'")
    response5 = draft_message(input5)
    print(f"Response: {response5}")

    print("\nTests completed.")

if __name__ == "__main__":
    test_draft_message()