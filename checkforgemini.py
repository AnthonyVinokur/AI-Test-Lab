from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="models/gemini-3.6-flash",
    contents="Say hello."
)

print(response.text)
# import os
# from dotenv import load_dotenv
# from google import genai
#
# load_dotenv()
#
# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
#
# for model in client.models.list():
#     print(model.name)
