import os
import fitz  # PyMuPDF

# PDFファイルが保存されているディレクトリ
input_dir = "//Users/ynkhiru09/Library/CloudStorage/OneDrive-KansaiUniversity/四国/徳島県/mima"
# テキストファイルの出力先
output_dir = "/Users/ynkhiru09/Library/CloudStorage/OneDrive-KansaiUniversity/四国/徳島県/mima"
os.makedirs(output_dir, exist_ok=True)

# PDFファイルをすべて処理
for filename in os.listdir(input_dir):
    if filename.lower().endswith(".pdf"):
        pdf_path = os.path.join(input_dir, filename)
        txt_filename = filename.replace(".pdf", ".txt")
        txt_path = os.path.join(output_dir, txt_filename)

        try:
            doc = fitz.open(pdf_path)
            all_text = ""
            for page in doc:
                all_text += page.get_text()
            doc.close()

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(all_text)
            print(f"✅ 変換完了: {txt_filename}")
        except Exception as e:
            print(f"⚠ 変換失敗: {filename} → {e}")
