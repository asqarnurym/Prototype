import json
import os

from datasets import load_dataset
from dotenv import load_dotenv

load_dotenv()
hf_token = os.getenv("HF_TOKEN")

print("Loading dataset in streaming mode...")
dataset = load_dataset("HuggingFaceFV/finevideo", split="train", streaming=True, token=hf_token)

first_row = next(iter(dataset))
print("Keys:", list(first_row.keys()))
print("Type of 'mp4':", type(first_row["mp4"]))
if isinstance(first_row["mp4"], dict):
    print("Keys of 'mp4':", list(first_row["mp4"].keys()))
    print("Path in 'mp4':", first_row["mp4"].get("path"))

print("Type of 'json':", type(first_row["json"]))
if isinstance(first_row["json"], dict):
    print("Keys of 'json':", list(first_row["json"].keys()))
    meta = first_row["json"]
elif isinstance(first_row["json"], str):
    meta = json.loads(first_row["json"])
    print("Keys of parsed 'json':", list(meta.keys()))

print("Metadata keys:", list(meta.keys()))
print("Language:", meta.get("language"))
print("Duration:", meta.get("duration"))
print("Categories:", meta.get("category"))
