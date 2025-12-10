import os
import re
import pandas as pd

# 必要なパスを設定
folder_path = "/Users/ynkhiru09/Downloads/osakahu"
city_name = os.path.basename(folder_path)
teirei_csv_path = os.path.join(folder_path, f"{city_name}_teirei.csv")
kaigi_csv_path = teirei_csv_path.replace("_teirei.csv", "_kaigi.csv")

def list_files(folder_path):
    return [f for f in os.listdir(folder_path) if re.match(r"\d{8}\d{5}\.txt", f)]

def extract_date(file_name):
    match = re.match(r"(\d{8})\d{5}\.txt", file_name)
    return match.group(1) if match else None

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
    print(f"会議テーブルを {kaigi_csv_path} に保存しました。")
    return kaigi_df

# 実行例
if __name__ == "__main__":
    df_kaigi = create_kaigi_table()
    print(df_kaigi)