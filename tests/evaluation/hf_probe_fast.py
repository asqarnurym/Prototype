import os
import time

from datasets import load_dataset
from dotenv import load_dotenv

load_dotenv()
hf_token = os.getenv("HF_TOKEN")

start = time.time()
print("Loading dataset in streaming mode, selecting ONLY 'json' column...")
dataset = load_dataset("HuggingFaceFV/finevideo", split="train", streaming=True, token=hf_token)
dataset = dataset.select_columns(["json"])

count = 0
for item in dataset:
    # Just iterate through 50 rows to see if it's fast
    meta = item["json"]
    count += 1
    if count >= 50:
        break

print(f"Iterated {count} rows in {time.time() - start:.2f} seconds.")
