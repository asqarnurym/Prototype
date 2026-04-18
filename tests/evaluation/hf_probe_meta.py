import os

from datasets import load_dataset
from dotenv import load_dotenv

load_dotenv()
hf_token = os.getenv("HF_TOKEN")

dataset = load_dataset("HuggingFaceFV/finevideo", split="train", streaming=True, token=hf_token)

row = next(iter(dataset))
meta = row["json"]
for k, v in meta.items():
    if k not in ["text_to_speech", "timecoded_text_to_speech", "youtube_description"]:
        print(f"{k}: {v}")
