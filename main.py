import requests
import os

API_KEY = os.getenv("GROQ_API_KEY")

URL = "https://api.groq.com/openai/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

TOPICS = [
    "dark psychology trick",
    "mind blowing history mystery"
]

def generate_script(topic):
    prompt = f"""
    Create a viral YouTube Shorts dark physiology script.

    Topic: {topic}

    Rules:
    - Strong hook in first line
    - Max 1000 words
    storytelling video acript without timestamp or any else unnecessary texts, just give a oerfect script that start and end connected for loop playing
    - Loop ending
    - Add caption in all video that match my full acript measn whenever audiance seen this caltion they will understand the meaning and amin motive of that bideo
    """

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(URL, headers=HEADERS, json=data)
    result = response.json()

    try:
        return result["choices"][0]["message"]["content"]
    except:
        return str(result)


def save_script(text, index):
    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/script_{index}.txt", "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    for i, topic in enumerate(TOPICS, start=1):
        script = generate_script(topic)
        save_script(script, i)
