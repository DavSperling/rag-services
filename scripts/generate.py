import os 
from dotenv import load_dotenv
import anthropic
from scripts.search import search

# Initialisation
load_dotenv()
client = anthropic.Anthropic()

def build_prompt(question, chunks):
    instruction = """
Answer the user's question using strictly the provided context passages. 
Do not incorporate any outside knowledge or assumptions. 
If the necessary information is not present in the passages, explicitly state that you cannot answer based on the given context.
"""
    list_of_chunks = []

    for i, (content, source, page, sim) in enumerate(chunks, start=1):
        chunk_text = f"[{i}] {source}, page {page}\n{content}"
        list_of_chunks.append(chunk_text)

    context = "\n\n".join(list_of_chunks)

    return f"{instruction.strip()}\n\n{context}\n\nQuestion: {question}"


def generate(prompt):
    message = {
        "role": "user", 
        "content": prompt 
    }
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[message]
    )
    
    return response.content[0].text


if __name__ == "__main__":
    question = "What is the VAT rate in France?"
    
    chunks = search(question)
    
    prompt = build_prompt(question, chunks)
    print("--- PROMPT ---")
    print(prompt)
    
    print("\n--- RÉPONSE CLAUDE ---")
    answer = generate(prompt)
    print(answer)