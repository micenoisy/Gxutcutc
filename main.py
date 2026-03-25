import requests
import os
import time

API_KEY = os.getenv("HUGGINGFACE_API_KEY")
MODEL = "google/flan-t5-large"

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

    for _ in range(3):
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{MODEL}",
            headers=HEADERS,
            json={"inputs": prompt}
        )

        try:
            data = response.json()

            if isinstance(data, dict) and "error" in data:
                time.sleep(10)
                continue

            return data[0]["generated_text"]

        except:
            return "FAILED"

    return "FAILED"


def save_script(text, index):
    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/script_{index}.txt", "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    for i, topic in enumerate(TOPICS, start=1):
        script = generate_script(topic)
        save_script(script, i)
