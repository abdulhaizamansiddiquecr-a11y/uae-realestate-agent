import time
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

from tools import search_listings, compare_listings
from rag import search_knowledge

load_dotenv()
client = genai.Client()

MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest"]

SYSTEM_PROMPT = """You are a helpful UAE real estate assistant.
Rules:
- You only help with UAE real estate: finding homes, comparing listings, and renting or buying questions. If the user asks for anything else (poems, coding, general chat), politely say you can only help with UAE real estate and suggest what you can do. Greetings and questions about what you can do are fine.
- Use search_listings and compare_listings for properties. Never invent listings, prices or details.
- Use search_knowledge for questions about renting rules, contracts, deposits, or checklists.
- When you use search_knowledge, say which source file your answer came from.
- If search_knowledge does not contain the answer (for example rules for Sharjah, Ajman or Abu Dhabi), say clearly that you do not have verified information. Do not guess.
- Mention the listing ID in your answers so the user can refer to it.
- Rent prices are in AED per year. Sale prices are total AED.
- The listings are sample data for a learning project, not real properties.
- Keep answers short and clear."""

config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[search_listings, compare_listings, search_knowledge],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)

TOOL_FUNCTIONS = {
    "search_listings": search_listings,
    "compare_listings": compare_listings,
    "search_knowledge": search_knowledge,
}

history = []
last_tools = []    # which tools were used for the last question
last_results = []  # what those tools returned


class GoogleBusyError(RuntimeError):
    """Raised when Google stays too busy after all retries."""


def reset():
    """Forget the conversation. The tests use this before each question."""
    history.clear()
    last_tools.clear()
    last_results.clear()


def call_model():
    """Calls Gemini, and retries if Google is busy."""
    for attempt in range(8):
        model = MODELS[attempt % 2]
        try:
            return client.models.generate_content(
                model=model, contents=history, config=config
            )
        except errors.APIError as e:
            if e.code in (429, 500, 503):
                wait = 5 * (attempt + 1)
                print(f"(Google is busy, trying again in {wait} seconds...)")
                time.sleep(wait)
            else:
                raise
    raise GoogleBusyError("Google is too busy right now. Try again in a minute.")


def ask(question):
    last_tools.clear()
    last_results.clear()
    history.append(types.Content(role="user", parts=[types.Part(text=question)]))
    response = call_model()

    while response.function_calls:
        history.append(response.candidates[0].content)

        result_parts = []
        for call in response.function_calls:
            args = dict(call.args)
            print(f"   [TOOL] {call.name}({args})")
            last_tools.append(call.name)

            try:
                result = TOOL_FUNCTIONS[call.name](**args)
            except Exception as e:
                result = {"error": str(e)}

            last_results.append(result)  # we save what the tool returned

            result_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={"result": result}
                )
            )

        history.append(types.Content(role="user", parts=result_parts))
        response = call_model()

    history.append(response.candidates[0].content)
    return response.text


# This part only runs when you start this file directly, not when evals import it
if __name__ == "__main__":
    print("UAE Real Estate Agent (type 'quit' to stop)\n")
    while True:
        question = input("You: ")
        if question.strip().lower() == "quit":
            break
        print(f"\nAI: {ask(question)}\n")