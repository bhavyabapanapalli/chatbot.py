
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv(override=True)

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Gemini API key not found. Check your .env file.")

# Initialize Gemini client
client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(
        timeout=120000
    )
)

# Chatbot response function
def get_response(question):

    for attempt in range(1, 3):

        try:
            print("\nAI is thinking...", flush=True)

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are a helpful AI assistant. "
                        "Give accurate, clear and simple answers. "
                        "Use examples whenever necessary."
                    ),
                    temperature=0.7,
                    max_output_tokens=1000
                )
            )

            if response.text:
                return response.text

            return "Sorry, no response was generated."

        except Exception as error:

            error_message = str(error)

            print(f"\nAttempt {attempt} failed: {error_message}")

            # Retry once for temporary server errors
            if attempt == 1 and (
                "504" in error_message
                or "503" in error_message
                or "429" in error_message
            ):
                print("Retrying in 3 seconds...")
                time.sleep(3)
                continue

            return "Unable to get a response. Please try again later."

    return "Request failed."


# Main chatbot application
def main():

    print("\n===================================")
    print("          GEMINI AI CHATBOT")
    print("===================================")
    print("Ask me anything!")
    print("Type 'exit' to stop.")
    print("-----------------------------------")

    while True:

        try:
            question = input("\nYou: ").strip()

            if question.lower() == "exit":
                print("\nChatbot: Goodbye!")
                break

            if not question:
                print("Please enter a question.")
                continue

            answer = get_response(question)

            print("\nChatbot:", answer)

        except KeyboardInterrupt:
            print("\n\nChatbot: Program stopped.")
            break

        except Exception as error:
            print("\nUnexpected Error:", error)


if __name__ == "__main__":
    main()
