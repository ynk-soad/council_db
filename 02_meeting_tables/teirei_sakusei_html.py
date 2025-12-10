import os
import re
import unicodedata
import json
import pandas as pd
from bs4 import BeautifulSoup
from collections import defaultdict

def normalize_text(text):
    """全角→半角に変換し、余計なスペースを除去する"""
    return unicodedata.normalize('NFKC', text).strip()

def extract_text_from_html(file_path):
    """HTML ファイルから本文を抽出"""
    with open(file_path, 'r', encoding='cp932', errors='ignore') as file:
        soup = BeautifulSoup(file, "html.parser")
        return soup.get_text()

def extract_teireikai_data(folder_path, jis_code_json_path):
    """
    定例会テーブルを作成し、CSVファイルに保存する。
    - **「臨時会」のみ `type_teirei=2`**
    - **それ以外は `type_teirei=1`**
    - **HTML ファイルを処理**
    """
    # **市町村名をフォルダパスの最後から取得**
    city_name = os.path.basename(folder_path)

    # **JISコードを JSON から取得**
    with open(jis_code_json_path, 'r', encoding='utf-8') as json_file:
        jis_code_data = json.load(json_file)
    jis_code = next((key for key, value in jis_code_data.items() if value == city_name), None)

    if not jis_code:
        print(f"⚠ 市町村名 '{city_name}' に対応する JISコードが見つかりません。")
        return None

    # **出力 CSV のパスを `{city_name}_teirei.csv` に設定**
    output_csv = os.path.join(folder_path, f"{city_name}_teirei.csv")

    teireikai_list = []
    year_counter = defaultdict(int)
    temp_meeting_data = defaultdict(list)
    session_tracker = defaultdict(lambda: {"regular": 0, "special": 0})  # 定例会・臨時会の「第○回」を個別カウント

    # **ファイル名の正規表現**
    file_pattern = re.compile(r'(\d{4})(\d{2})(\d{2})(\d{5})\.html')

    for filename in sorted(os.listdir(folder_path)):  # **ファイル名順に処理**
        match = file_pattern.match(filename)
        if not match:
            print(f"⚠ ファイル名のフォーマットが不正: {filename}")
            continue

        year, month, day, jis_code_extracted = match.groups()
        year = int(year)  # **`year` を明示的に int 型にする**
        file_path = os.path.join(folder_path, filename)

        # **HTML からテキストを抽出**
        content = extract_text_from_html(file_path)

        # **臨時会と定例会の判定**
        type_teirei = 1  # デフォルトは定例会
        if "臨時会" in content[:200]:  # **最初の200文字で判定**
            type_teirei = 2  # **「臨時会」が最初に出現したら確定で 2**

        # **「第○回」の抽出**
        session_match = re.search(r'第\s*([０-９0-9]+)\s*回', normalize_text(content))
        if session_match:
            session_number = int(session_match.group(1))  # **全角→半角変換済み**
        else:
            # **「第○回」がない場合、その年の開催回数で補完**
            session_key = (year, type_teirei)
            if type_teirei == 1:
                session_tracker[session_key]["regular"] += 1
                session_number = session_tracker[session_key]["regular"]
            else:
                session_tracker[session_key]["special"] += 1
                session_number = session_tracker[session_key]["special"]

        # **定例会ごとのデータを整理**
        key = (year, session_number, type_teirei)  # **定例会と臨時会で別カウント**
        temp_meeting_data[key].append({
            "filename": filename,
            "date": f"{year}{month}{day}",
            "type_teirei": type_teirei,
            "year": year  # **明示的に year を保存**
        })

    # **年ごとに `time` を適切に再計算**
    year_session_count = defaultdict(int)

    # **定例会ごとに整理し、テーブルを作成**
    final_teireikai_list = []

    for (year, session_number, type_teirei), meetings in temp_meeting_data.items():
        meetings.sort(key=lambda x: x["date"])

        start_date = meetings[0]["date"]
        final_date = meetings[-1]["date"]
        meeting_count = len(meetings)

        # **ID_teireiごとにグループ化**
        ID_teirei = f"{type_teirei}{jis_code}{year}{start_date[4:6]}"

        final_teireikai_list.append({
            "ID_teirei": ID_teirei,
            "city_name": city_name,
            "jis_code": jis_code,
            "type_teirei": type_teirei,
            "year": year,
            "time": None,  # ここで一旦 None にしておき、後で正しく付与する
            "start_date": start_date,
            "final_date": final_date,
            "mag": "",
            "meeting_count": meeting_count
        })

    df_teireikai = pd.DataFrame(final_teireikai_list)

    # **ID_teireiごとにグループ化し、start_dateとfinal_dateを統合**
    df_teireikai = df_teireikai.groupby("ID_teirei").agg({
        "city_name": "first",
        "jis_code": "first",
        "type_teirei": "first",
        "year": "first",
        "start_date": "min",
        "final_date": "max",
        "mag": "first",
        "meeting_count": "sum"
    }).reset_index()

    # **time を年内の開催順に振り直す**
    df_teireikai = df_teireikai.sort_values(by=["year", "start_date", "type_teirei"]).reset_index(drop=True)
    df_teireikai["time"] = df_teireikai.groupby("year").cumcount() + 1

    # **カラムの順番を元に戻す**
    column_order = [
        "ID_teirei", "city_name", "jis_code", "type_teirei", "year", "time",
        "start_date", "final_date", "mag", "meeting_count"
    ]
    df_teireikai = df_teireikai[column_order]

    df_teireikai.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"✅ 定例会テーブルを {output_csv} に保存しました。")

    return df_teireikai

# **実行例**
folder_path = "/Users/ynkhiru09/Library/CloudStorage/OneDrive-KansaiUniversity/四国/徳島県/吉野川市"
jis_code_json_path = "/Users/ynkhiru09/Desktop/プログラム/jiscode.json"

df_teireikai = extract_teireikai_data(folder_path, jis_code_json_path)

print(df_teireikai.head())
