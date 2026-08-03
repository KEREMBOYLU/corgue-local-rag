import argparse

from pdf_utils import chunk_text, read_pdf_text, select_pdf_path

def parse_args():
    parser = argparse.ArgumentParser(description="Seçilen PDF'in chunk'larını kontrol eder.")
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

    print("PDF başarıyla chunk'lara bölündü.")
    print(f"Toplam karakter: {len(text)}")
    print(f"Toplam chunk sayısı: {len(chunks)}")

    print("\nİlk chunk:\n")
    print(chunks[0])

    print("\n" + "=" * 60)
    print("\nİkinci chunk:\n")
    print(chunks[1] if len(chunks) > 1 else "İkinci chunk yok.")


if __name__ == "__main__":
    main()
