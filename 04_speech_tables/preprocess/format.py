import os
import re
import chardet

# === 設定 ===
BASE_DIR = "/Users/ynkhiru09/Downloads/osaka"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

def preprocess_text_for_regex(text):
    text = text.replace('：', ':')             # 全角コロンを半角
    text = text.replace('◯', '○')             # 丸記号を統一
    text = text.replace('）', ')')             # 全角括弧を半角
    text = re.sub(r'[◆◎]', '○', text)         # マーカーをすべて「○」に統一 ←★追加
    text = re.sub(r'([○])\s*', r'\1', text)    # マーカー後の空白を除去
    text = re.sub(r'\n+', '\n', text)          # 連続改行を1つに
    return text


# === ファイルの文字コード検出関数 ===
def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']

# === 実行 ===
for file_name in os.listdir(BASE_DIR):
    if file_name.endswith(".txt"):
        file_path = os.path.join(BASE_DIR, file_name)
        processed_path = os.path.join(PROCESSED_DIR, file_name)
        try:
            enc = detect_encoding(file_path)
            with open(file_path, "r", encoding=enc) as f:
                original = f.read()
            processed = preprocess_text_for_regex(original)
            with open(processed_path, "w", encoding="utf-8") as f:
                f.write(processed)
            print(f"{file_name} → processed/{file_name}")
        except Exception as e:
            print(f"Error processing {file_name}: {e}")
