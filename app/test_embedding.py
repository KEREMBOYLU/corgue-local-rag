from foundry_local_sdk import Configuration, FoundryLocalManager


def main():
    alias = "qwen3-embedding-0.6b"

    print("Foundry Local başlatılıyor...")
    config = Configuration(app_name="embedding_test")
    FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance

    print("Execution providers hazırlanıyor...")
    manager.download_and_register_eps()

    print("Embedding modeli alınıyor...")
    model = manager.catalog.get_model(alias)

    print("Model indiriliyor...")
    model.download()

    print("Model yükleniyor...")
    model.load()

    print("Embedding client hazırlanıyor...")
    embedding_client = model.get_embedding_client()

    print("Embedding üretiliyor...")

    text = "A data type defines a collection of data objects and operations."

    response = embedding_client.generate_embedding(text)
    embedding = response.data[0].embedding

    print("Embedding başarıyla üretildi.")
    print(f"Response tipi: {type(response)}")
    print(f"Embedding tipi: {type(embedding)}")
    print(f"Embedding boyutu: {len(embedding)}")
    print(f"İlk 10 değer: {embedding[:10]}")

    print("Model kapatılıyor...")
    model.unload()


if __name__ == "__main__":
    main()