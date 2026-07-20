from foundry_local_sdk import Configuration, FoundryLocalManager


def main():
    config = Configuration(app_name="inspect_foundry")
    FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance

    print("Manager methods:")
    print([name for name in dir(manager) if not name.startswith("_")])

    print("\nCatalog methods:")
    print([name for name in dir(manager.catalog) if not name.startswith("_")])

    print("\nTrying chat model...")
    chat_model = manager.catalog.get_model("qwen2.5-0.5b")

    print("\nChat model methods:")
    print([name for name in dir(chat_model) if not name.startswith("_")])


if __name__ == "__main__":
    main()