import os

from datasets import load_dataset
from dotenv import load_dotenv

load_dotenv()
hf_token = os.getenv("HF_TOKEN")

print("Loading dataset in streaming mode...")
dataset = load_dataset("HuggingFaceFV/finevideo", split="train", streaming=True, token=hf_token)

print("Fetching first row...")
first_row = next(iter(dataset))
print("Keys:", list(first_row.keys()))
for k, v in first_row.items():
    if isinstance(v, str) and len(v) > 100:
        print(f"{k}: {v[:100]}...")
    else:
        print(f"{k}: {v}")
