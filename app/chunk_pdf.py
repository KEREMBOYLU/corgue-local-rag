import argparse

from pdf_utils import chunk_text, read_pdf_text, select_pdf_path

def parse_args():
    parser = argparse.ArgumentParser(description="Inspect chunks generated from a selected PDF.")
    parser.add_argument("pdf", nargs="?", help="PDF yolu. Verilmezse interaktif olarak sorulur.")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        pdf_path = select_pdf_path(args.pdf)
    except ValueError as error:
        print(error)
        return

    text = read_pdf_text(pdf_path)
    chunks = chunk_text(text)

    print("The PDF was successfully split into chunks.")
    print(f"Toplam karakter: {len(text)}")
    print(f"Total chunk count: {len(chunks)}")

    print("\nFirst chunk:\n")
    print(chunks[0])

    print("\n" + "=" * 60)
    print("\nSecond chunk:\n")
    print(chunks[1] if len(chunks) > 1 else "There is no second chunk.")


if __name__ == "__main__":
    main()
