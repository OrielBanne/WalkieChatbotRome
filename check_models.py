from openai import OpenAI

client = OpenAI()
models = client.models.list()

print("Available models for your API key:")
print("=" * 60)

all_models = sorted([m.id for m in models.data])

# Separate by type
gpt_models = [m for m in all_models if 'gpt' in m.lower()]
embedding_models = [m for m in all_models if 'embedding' in m.lower()]
other_models = [m for m in all_models if m not in gpt_models and m not in embedding_models]

print("\nGPT Models:")
for m in gpt_models:
    print(f"  ✓ {m}")

print("\nEmbedding Models:")
if embedding_models:
    for m in embedding_models:
        print(f"  ✓ {m}")
else:
    print("  ❌ No embedding models available")

print("\nOther Models:")
for m in other_models:
    print(f"  - {m}")

print("\n" + "=" * 60)
print(f"Total models: {len(all_models)}")
