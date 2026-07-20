from foundry_local_sdk import Configuration, FoundryLocalManager


def main():
    alias = "qwen2.5-0.5b"

    print("Foundry Local başlatılıyor...")

    config = Configuration(app_name="local_rag_test")
    FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance

    print("Execution providers hazırlanıyor...")
    manager.download_and_register_eps()

    print("Model bilgisi alınıyor...")
    model = manager.catalog.get_model(alias)

    print("Model indiriliyor...")
    model.download()

    print("Model yükleniyor...")
    model.load()

    print("Client hazırlanıyor...")
    client = model.get_chat_client()

    print("\nAssistant cevabı:\n")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. "
                "Answer only using the provided context. "
                "If the answer is not in the context, say you don't know."
            )
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

    print("\n\nModel kapatılıyor...")
    model.unload()


if __name__ == "__main__":
    main()