import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

llm = init_chat_model(os.environ["LLM_MODEL"], model_provider=os.environ["LLM_PROVIDER"])
reply = llm.invoke("Reply with exactly: Foreman is online.")
print(reply.text)