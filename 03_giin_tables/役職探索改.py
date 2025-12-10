import os
import re

# **ベースディレクトリの指定**
BASE_DIR = "C:/Users/kyo/Kansai University/NATORI,Ryota - ゼミ/R7ゼミデータ/九州全市議事録/福岡県/itoshima"
MINUTES_DIR = BASE_DIR  # 議事録ファイルがあるディレクトリ

# **検索対象の語句を定義**
NAME = ["議長の選挙", "議長選挙","監査委員の選任","副議長選挙","副議長の選挙"]

# **議事録フォルダ内の全 .txt ファイルを取得**
minutes_files = [f for f in os.listdir(MINUTES_DIR) if f.endswith(".txt")]

# **議事録ファイルを 2011年から古い順にソート**
def extract_year(filename):
    match = re.search(r"(\d{4})", filename)  # ファイル名から西暦 (4桁) を抽出
    return int(match.group(1)) if match else 9999  # 年がない場合は後ろに回す

sorted_minutes_files = sorted(minutes_files, key=extract_year)  # 古い順にソート

# **検索処理**
def search_keywords_in_minutes():
    pattern = "|".join(re.escape(word) for word in NAME)  # ワードリストを正規表現パターンに変換

    for file in sorted_minutes_files:
        file_path = os.path.join(MINUTES_DIR, file)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        cleaned_content = re.sub(r"\s+", "", content)  # スペースや改行を除去

        matches = list(re.finditer(pattern, cleaned_content))  # ワードにマッチ

        if matches:
            print(f"{file}:")
            for match in matches:
                print(f"  - {match.group()} at position {match.start()}")
            print()

# **実行**
search_keywords_in_minutes()
