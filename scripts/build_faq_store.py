from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Upload the Pathwise FAQ to a new OpenAI vector store (run once, by hand)

load_dotenv()

FAQ_FILE = Path("knowledge/pathwise_faq.md")

client = OpenAI()

store = client.vector_stores.create(name="pathwise-faq")

with FAQ_FILE.open("rb") as f:
    client.vector_stores.files.upload_and_poll(vector_store_id=store.id, file=f)

print("Vector store created:", store.id)
print("Add this line to your .env file:")
print(f"PATHWISE_FAQ_VECTOR_STORE_ID={store.id}")