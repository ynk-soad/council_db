import os
import chardet

# 変換対象ディレクトリ
source_dir = "/Users/ynkhiru09/Downloads/s"

# すべての .txt ファイルを対象に変換
for file_name in os.listdir(source_dir):
    if file_name.endswith(".txt"):
        file_path = os.path.join(source_dir, file_name)
        
        # 1. 現在の文字コードを判定
        with open(file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"]

        # 2. 指定の文字コードで読み込み、utf-8 で上書き保存
        try:
            text = raw_data.decode(encoding, errors="ignore")  # デコードエラーを無視
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"{file_name} を UTF-8 に変換しました（元: {encoding}）")
        except Exception as e:
            print(f"{file_name} の変換に失敗: {e}")
