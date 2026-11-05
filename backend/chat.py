import time
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

load_dotenv()  # reads your key from the .env file

client = genai.Client()

# We try the first model, and if Google is busy we try the second one
MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest"]

SYSTEM_PROMPT = (
    "You are a helpful assistant for people looking for homes in the UAE. "
    "Keep your answers short and clear."
)

config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)

history = []  # the whole conversation is saved here


def ask(question):
    history.append(types.Content(role="user", parts=[types.Part(text=question)]))

    for attempt in range(5):
        model = MODELS[attempt % 2]  # switches between the two models
        try:
            response = client.models.generate_content(
                model=model, contents=history, config=config
            )
            history.append(response.candidates[0].content)
            return response.text
        except errors.APIError as e:
            # 429 = too many requests, 500/503 = Google is busy
            if e.code in (429, 500, 503):
                wait = 3 * (attempt + 1)
                print(f"(Google is busy, trying again in {wait} seconds...)")
                time.sleep(wait)
            else:
                history.pop()
                raise  # a different error, so we show it

    history.pop()
    return "Sorry, Google is too busy right now. Please try again in a minute."


print("UAE Real Estate Assistant (type 'quit' to stop)\n")

while True:
    question = input("You: ")
    if question.strip().lower() == "quit":
        break
    print(f"\nAI: {ask(question)}\n")