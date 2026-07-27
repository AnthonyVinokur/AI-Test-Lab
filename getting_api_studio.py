
# from dotenv import load_dotenv
#
# import os
# from google import genai
# load_dotenv()
#
# client = genai.Client(
#     api_key=os.getenv("GEMINI_API_KEY"),
# )
#
# tools = [
#     {
#         'type': 'google_search',
#     },
# ]
#
# generation_config = {
#     'temperature': 1,
#     'max_output_tokens': 65536,
#     'top_p': 0.95,
#     'thinking_level': 'high',
# }
#
# interaction = client.interactions.create(
#     model='models/gemini-3-flash-preview',
#     input='',
#     tools=tools,
#     generation_config=generation_config,
# )
#
# print(interaction.steps[-1])

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY was not loaded.")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say hello."
)

print(response.text)

# import anthropic
#
# client = anthropic.Anthropic(api_key="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")
#
# message = client.messages.create(
#     model="claude-sonnet-4-6",
#     max_tokens=1024,
#     messages=[{"role": "user", "content": "Hello, world"}],
# )
# print(message.content)