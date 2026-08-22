import os
import sys
import argparse
from dotenv import load_dotenv
from openai import OpenAI

from call_function import available_functions, call_function
from prompts import system_prompt


MAX_ITERATIONS = 20


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Chatbot")
    parser.add_argument("user_prompt", type=str, help="User prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    user_prompt = args.user_prompt

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    api_key = os.environ.get("OPENROUTER_API_KEY")

    if api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is not set")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=messages,
            tools=available_functions,
        )

        if response.usage is None:
            raise RuntimeError("Response usage metadata is missing")

        if args.verbose:
            print(f"User prompt: {user_prompt}")
            print(f"Prompt tokens: {response.usage.prompt_tokens}")
            print(f"Response tokens: {response.usage.completion_tokens}")

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            if not message.content:
                print(
                    "Agent produced an empty response without a final answer"
                )
                sys.exit(1)
            else:
                print("Final response:")
                print(message.content)
                return

        for tool_call in message.tool_calls:
            result_message = call_function(tool_call, verbose=args.verbose)

            if not result_message["content"]:
                raise RuntimeError(
                    f"Function call returned an empty result: "
                    f"{tool_call.function.name}"
                )

            if args.verbose:
                print(f"-> {result_message['content']}")

            messages.append(result_message)

    print(
        f"Agent did not produce a final response within "
        f"{MAX_ITERATIONS} iterations"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()