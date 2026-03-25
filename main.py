import requests
import os
from datetime import datetime

API_KEY = os.getenv("HUGGINGFACE_API_KEY")
MODEL = "tiiuae/falcon-7b-instruct"

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

PROMPT_TEMPLATE = """
Generate a viral YouTube Shorts script.

Requirements:
- Hook in first line
- Max 120 words
- High retention storytelling
- Loop ending
- Include caption line

Topic: {topic}
"""

TOPICS = [
    "AI future shocking facts",
    "dark psychology trick",
    "mind blowing history mystery"
]


def generate_script(topic):
    prompt = PROMPT_TEMPLATE.format(topic=topic)

    response = requests.post(
        f"https://api-inference.huggingface.co/models/{MODEL}",
        headers=HEADERS,
        json={"inputs": prompt}
    )

    try:
        return response.json()[0]["generated_text"]
    except:
        return "Error generating script"


def save_script(text, index):
    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/script_{index}.txt", "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    print("Generating scripts...")

    for i, topic in enumerate(TOPICS, start=1):
        script = generate_script(topic)
        save_script(script, i)

    print("Done. Scripts saved in /outputs")
