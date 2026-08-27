import argparse

from pdf_utils import read_pdf_text, select_pdf_path


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect text extracted from a selected PDF.")
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

    print("The PDF was read successfully.")
    print(f"Toplam karakter: {len(text)}")
    print("\nFirst 1,500 characters:\n")
    print(text[:1500])


if __name__ == "__main__":
    main()
