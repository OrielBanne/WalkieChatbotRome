from openai import OpenAI

client = OpenAI()

try:
    r = client.embeddings.create(
        model="text-embedding-3-small",
        input="hello world"
    )
    print("SUCCESS")
    print("Embedding length:", len(r.data[0].embedding))
except Exception as e:
    print("ERROR:")
    print(e)
