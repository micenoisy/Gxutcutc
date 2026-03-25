import requests
import os

API_KEY = os.getenv("GROQ_API_KEY")

URL = "https://api.groq.com/openai/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

TOPICS = [
    "AI future shocking facts",
    "dark psychology trick",
    "mind blowing history mystery"
]

def generate_script(topic):
    prompt = f"""
    Create a viral YouTube Shorts script.

    Topic: {topic}

    Rules:
    - Strong hook in first line
    - Max 100 words
    - Loop ending
    - Add caption at end
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
