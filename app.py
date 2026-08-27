from foundry_local_sdk import Configuration, FoundryLocalManager
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "app"))
from settings import get_system_prompt


def main():
    alias = "qwen2.5-0.5b"

    print("Starting Foundry Local...")

    config = Configuration(app_name="local_rag_test")
    FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance

    print("Preparing execution providers...")
    manager.download_and_register_eps()

    print("Reading model information...")
    model = manager.catalog.get_model(alias)

    print("Downloading model...")
    model.download()

    print("Loading model...")
    model.load()

    print("Preparing client...")
    client = model.get_chat_client()

    print("\nAssistant response:\n")

    messages = [
        {
            "role": "system",
            "content": get_system_prompt()
        },
        {
            "role": "user",
            "content": (
                "Context: RAG stands for Retrieval-Augmented Generation. "
                "It is a technique where relevant information is retrieved from documents "
                "and added to the model prompt before generating an answer.\n\n"
                "Question: What does RAG stand for?"
            )
        }
    ]

    for chunk in client.complete_streaming_chat(messages):
        if not chunk.choices:
            continue

        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)

    print("\n\nUnloading model...")
    model.unload()


if __name__ == "__main__":
    main()
