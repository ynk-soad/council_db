import os
import re
import json
import unicodedata
import pandas as pd
from collections import defaultdict

# **パスの設定**
folder_path = "/Users/ynkhiru09/Downloads/ishigaki"
jis_code_json_path = "/Users/ynkhiru09/Desktop/プログラム/テーブル作成集/jiscode.json"

# **市町村名をフォルダパスの最後から取得**
city_name = os.path.basename(folder_path)
teirei_csv_path = os.path.join(folder_path, f"{city_name}_teirei.csv")
kaigi_csv_path = teirei_csv_path.replace("_teirei.csv", "_kaigi.csv")

with open(jis_code_json_path, 'r', encoding='utf-8-sig') as json_file:
    jis_code_data = json.load(json_file)
if city_name in jis_code_data:
    jis_code, city_name = jis_code_data[city_name]
else:
    print(f"⚠ 市町村名 '{city_name}' に対応する JISコードが見つかりません。")
    exit()

def normalize_text(text):
    return unicodedata.normalize('NFKC', text).strip()

def list_files(folder_path):
    return [f for f in os.listdir(folder_path) if re.match(r"\d{8}\d{5}\.txt", f)]

def extract_date(file_name):
    match = re.match(r"(\d{8})\d{5}\.txt", file_name)
    return match.group(1) if match else None

def create_teireikai_table():
    temp_meeting_data = defaultdict(list)
    session_tracker = {}

    file_pattern = re.compile(r'(\d{4})(\d{2})(\d{2})(\d{5})\.txt')

    for filename in sorted(os.listdir(folder_path)):
        match = file_pattern.match(filename)
        if not match:
            print(f"⚠ ファイル名のフォーマットが不正: {filename}")
            continue

        year, month, day, _ = match.groups()
        year = int(year)
        file_path = os.path.join(folder_path, filename)

        with open(file_path, 'r', encoding='utf-8') as file:
            content = "".join(file.readlines()[:20])

        type_teirei = 2 if "臨時会" in content else 1

        session_match = re.search(r'第\s*([０-９0-9]+)\s*回', normalize_text(content))
        if session_match:
            session_number = int(session_match.group(1))
        else:
            month_key = f"{year}{month}{type_teirei}"
            if month_key not in session_tracker:
                session_tracker[month_key] = len(session_tracker) + 1
            session_number = session_tracker[month_key]

        key = (year, session_number, type_teirei)
        temp_meeting_data[key].append({"date": f"{year}{month}{day}", "type_teirei": type_teirei})

    final_teireikai_list = []
    for (year, session_number, type_teirei), meetings in temp_meeting_data.items():
        meetings.sort(key=lambda x: x["date"])
        start_date = meetings[0]["date"]
        final_date = meetings[-1]["date"]
        ID_teirei = f"{type_teirei}{jis_code}{year}{start_date[4:6]}"

        final_teireikai_list.append({
            "ID_teirei": ID_teirei,
            "city_name": city_name,
            "jis_code": jis_code,
            "type_teirei": type_teirei,
            "year": year,
            "start_date": start_date,
            "final_date": final_date,
            "mag": "",
            "meeting_count": len(meetings)
        })

    df_teireikai = pd.DataFrame(final_teireikai_list)
    df_teireikai = df_teireikai.groupby("ID_teirei", as_index=False).agg({
        "city_name": "first",
        "jis_code": "first",
        "type_teirei": "first",
        "year": "first",
        "start_date": "min",
        "final_date": "max",
        "mag": "first",
        "meeting_count": "sum"
    })
    df_teireikai = df_teireikai.sort_values(by="start_date").reset_index(drop=True)
    df_teireikai.to_csv(teirei_csv_path, index=False, encoding="utf-8-sig")
    print(f" 定例会テーブルを {teirei_csv_path} に保存しました。")
    return df_teireikai

def create_kaigi_table():
    rmtg_df = pd.read_csv(teirei_csv_path, dtype=str)
    rmtg_df["start_date"] = pd.to_datetime(rmtg_df["start_date"], format="%Y%m%d")
    rmtg_df["final_date"] = pd.to_datetime(rmtg_df["final_date"], format="%Y%m%d")

    file_lists = list_files(folder_path)
    file_dates = [extract_date(f) for f in file_lists]

    kaigi_df = pd.DataFrame(columns=["ID_teirei", "kaigi_id", "jis_code"])

    for file_date in file_dates:
        file_date = pd.to_datetime(file_date, format="%Y%m%d")

        for _, row in rmtg_df.iterrows():
            if row["start_date"] <= file_date <= row["final_date"]:
                new_row = pd.DataFrame({
                    "ID_teirei": [row["ID_teirei"]],
                    "kaigi_id": [file_date.strftime("%Y%m%d") + row["jis_code"]],
                    "jis_code": [row["jis_code"]]
                })
                kaigi_df = pd.concat([kaigi_df, new_row], ignore_index=True)

    kaigi_df = kaigi_df.drop_duplicates()
    kaigi_df = kaigi_df.sort_values(by=["kaigi_id"]).reset_index(drop=True)
    kaigi_df.to_csv(kaigi_csv_path, index=False, encoding="utf-8-sig")
    print(f" 会議テーブルを {kaigi_csv_path} に保存しました。")
    return kaigi_df

# メイン処理
df_teireikai = create_teireikai_table()
df_kaigi = create_kaigi_table()
print("\n--- 定例会テーブル ---")
print(df_teireikai)
print("\n--- 会議テーブル ---")
print(df_kaigi)
