import re
import csv
import time
from datetime import datetime
from pathlib import Path

import agent

SLEEP_SECONDS = 12  # the free tier allows only a few questions per minute

# Each test says:
#   tools:    tools the agent MUST use
#   no_tools: True means the agent must NOT use any tool
#   all_of:   words that must ALL be in the answer
#   any_of:   at least ONE of these words must be in the answer
TESTS = [
    # --- Rules questions (should use search_knowledge) ---
    {"name": "Security deposit", "question": "How much security deposit should I pay in Dubai?",
     "tools": ["search_knowledge"], "all_of": ["5%", "10%"]},
    {"name": "Ejari", "question": "Do I need to register my rental contract in Dubai?",
     "tools": ["search_knowledge"], "all_of": ["ejari"]},
    {"name": "Rent notice days", "question": "How many days notice must a landlord give to change the rent in Dubai?",
     "tools": ["search_knowledge"], "all_of": ["90"]},
    {"name": "Rent increase cap", "question": "My rent is 25% below the market average in Dubai. What is the maximum increase allowed?",
     "tools": ["search_knowledge"], "all_of": ["10%"]},
    {"name": "Disputes", "question": "Who handles rental disputes in Dubai?",
     "tools": ["search_knowledge"], "all_of": ["rental dispute"]},
    {"name": "Changing locks", "question": "Can my landlord change the locks to make me leave?",
     "tools": ["search_knowledge"],
     "any_of": ["not allowed", "illegal", "cannot", "can't", "not permitted", "prohibited"]},

    # --- Honesty: the agent must not make things up ---
    {"name": "Unknown: Sharjah rules", "question": "What are the rent rules in Sharjah?",
     "tools": ["search_knowledge"],
     "any_of": ["don't have", "do not have", "not included", "no verified", "cannot", "can't", "unable", "not available"]},
    {"name": "Unknown: Fujairah villa", "question": "Find me a villa for rent in Fujairah",
     "tools": ["search_listings"],
     "any_of": ["no listings", "no results", "couldn't find", "could not find", "didn't find",
                "did not find", "don't have", "do not have", "not find", "no matching", "nothing"]},

    # --- Listing searches (should use search_listings) ---
    {"name": "Sharjah 2BR rent", "question": "Find a 2-bedroom apartment for rent in Sharjah",
     "tools": ["search_listings"], "any_of": ["sharjah"]},
    {"name": "Dubai studio metro", "question": "Cheapest furnished studio for rent in Dubai near the metro",
     "tools": ["search_listings"]},
    {"name": "Abu Dhabi sale", "question": "Show me 1-bedroom apartments for sale in Abu Dhabi under 1,500,000 AED",
     "tools": ["search_listings"]},
    {"name": "Compare", "question": "Compare listings 1 and 2",
     "tools": ["compare_listings"]},

    # --- Needs two tools ---
    {"name": "Listing + deposit", "question": "Find a furnished 1-bedroom for rent in Dubai and tell me what deposit I should expect",
     "tools": ["search_listings", "search_knowledge"], "all_of": ["10%"]},

    # --- No tools needed ---
    {"name": "Data is sample", "question": "Is the data in this assistant real?",
     "any_of": ["sample", "not real", "learning", "fake", "example"]},
    {"name": "Greeting", "question": "Hi! What can you help me with?",
     "no_tools": True, "any_of": ["listing", "rent", "propert"]},

    # --- Harder tests ---
    {"name": "Off-topic request", "question": "Write me a poem about cats",
     "no_tools": True,
     "any_of": ["real estate", "propert", "rent", "can't", "cannot", "only", "unable"]},
    {"name": "Deposit math", "question": "If I rent a 1-bedroom for 70,000 AED a year, how much is the standard security deposit if it is unfurnished?",
     "any_of": ["3,500", "3500"]},
    {"name": "Unknown: Ajman law", "question": "Is it legal for a landlord in Ajman to keep my full deposit?",
     "tools": ["search_knowledge"],
     "any_of": ["don't have", "do not have", "not included", "no verified", "cannot", "can't", "unable", "not available"]},
    {"name": "Listing that does not exist", "question": "Show me the details of listing 999",
     "tools": ["compare_listings"],
     "any_of": ["not found", "no listing", "couldn't", "could not", "doesn't exist",
                "does not exist", "no results", "not exist", "unable", "no details"]},
    {"name": "Many filters", "question": "Find an unfurnished 2-bedroom for rent in Sharjah under 60,000 AED with parking",
     "tools": ["search_listings"]},
    {"name": "Dubai Marina 3BR", "question": "What is the rent for a 3-bedroom in Dubai Marina?",
     "tools": ["search_listings"]},
    {"name": "Urdu question", "question": "دبئی میں سیکیورٹی ڈپازٹ کتنا ہوتا ہے؟",
     "tools": ["search_knowledge"], "any_of": ["5%", "10%"]},
]


def find_invented_ids(question, answer):
    """Listing IDs the AI mentioned that no tool returned.
    Numbers that appear in the user's own question are ignored."""
    mentioned = {
        int(n) for n in re.findall(r"\bID\s*[:#]?\s*(\d+)", answer, flags=re.IGNORECASE)
    }
    from_question = {int(n) for n in re.findall(r"\d+", question)}
    returned = set()
    for result in agent.last_results:
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and "id" in item:
                    returned.add(item["id"])
    return mentioned - returned - from_question


def run_test(test):
    agent.reset()
    answer = agent.ask(test["question"])
    used = list(agent.last_tools)
    text = answer.lower()
    problems = []

    for tool in test.get("tools", []):
        if tool not in used:
            problems.append(f"did not use {tool}")
    if test.get("no_tools") and used:
        problems.append(f"used tools it did not need: {used}")
    for word in test.get("all_of", []):
        if word.lower() not in text:
            problems.append(f"answer is missing '{word}'")
    any_of = test.get("any_of")
    if any_of and not any(w.lower() in text for w in any_of):
        problems.append(f"answer has none of {any_of}")

    invented = find_invented_ids(test["question"], answer)
    if invented:
        problems.append(f"mentioned listing IDs that no tool returned: {sorted(invented)}")

    return problems, used, answer


def main():
    passed = 0
    skipped = 0
    total = len(TESTS)

    for i, test in enumerate(TESTS, start=1):
        if i > 1:
            time.sleep(SLEEP_SECONDS)
        print(f"\n[{i}/{total}] {test['name']}: {test['question']}")

        try:
            problems, used, answer = run_test(test)
        except agent.GoogleBusyError:
            skipped += 1
            print("  SKIPPED - Google was too busy (this is not a mistake in the agent)")
            continue
        except Exception as e:
            problems, used, answer = [f"crashed: {e}"], [], ""

        if problems:
            print(f"  FAIL - {'; '.join(problems)}")
            print(f"  Tools used: {used}")
            print(f"  Answer: {answer[:300]}")
        else:
            passed += 1
            print(f"  PASS  (tools: {used})")

    counted = total - skipped
    if counted == 0:
        print("\nNo test could run because Google was too busy. Try again later.")
        return

    print(f"\n==== SCORE: {passed}/{counted} ({round(100 * passed / counted)}%) ====")
    if skipped:
        print(f"({skipped} tests were skipped because Google was too busy. Run again later for a full score.)")

    # Save every run, so we can see the score improve over time
    history_file = Path(__file__).parent / "eval_history.csv"
    new_file = not history_file.exists()
    with open(history_file, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["date", "passed", "counted", "skipped"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), passed, counted, skipped])


if __name__ == "__main__":
    main()