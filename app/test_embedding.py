from foundry_local_sdk import Configuration, FoundryLocalManager


def main():
    alias = "qwen3-embedding-0.6b"

    print("Starting Foundry Local...")
    config = Configuration(app_name="embedding_test")
    FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance

    print("Preparing execution providers...")
    manager.download_and_register_eps()

    print("Getting the embedding model...")
    model = manager.catalog.get_model(alias)

    print("Model indiriliyor...")
    model.download()

    print("Loading model...")
    model.load()

    print("Preparing the embedding client...")
    embedding_client = model.get_embedding_client()

    print("Creating embedding...")

    text = "A data type defines a collection of data objects and operations."

    response = embedding_client.generate_embedding(text)
    embedding = response.data[0].embedding

    print("The embedding was created successfully.")
    print(f"Response tipi: {type(response)}")
    print(f"Embedding tipi: {type(embedding)}")
    print(f"Embedding boyutu: {len(embedding)}")
    print(f"First 10 values: {embedding[:10]}")

    print("Unloading model...")
    model.unload()


if __name__ == "__main__":
    main()
