import os
import pandas as pd

# 入出力フォルダを指定
input_folder = "/Users/ynkhiru09/Downloads/osaka_"
output_folder = "/Users/ynkhiru09/Downloads/osaka_test"
os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.endswith("_qa.csv"):
        file_path = os.path.join(input_folder, filename)
        df = pd.read_csv(file_path)
        paired_rows = []
        i = 0

        while i < len(df):
            row = df.iloc[i]
            if pd.notna(row["question"]):
                if i + 1 < len(df):
                    next_row = df.iloc[i + 1]
                    if pd.notna(next_row["answer"]):
                        paired_rows.append({
                            "question_speaker": row["speaker"],
                            "question": row["question"],
                            "answer_speaker": next_row["speaker"],
                            "answer": next_row["answer"],
                            "kaigi_id": row["kaigi_id"],
                            "ID_teirei": row["ID_teirei"],
                            "q_市議選日": row.get("市議選日"),
                            "q_giin_id": row.get("giin_id"),
                            "q_city_name": row.get("city_name"),
                            "q_name": row.get("name"),
                            "q_kana": row.get("kana"),
                            "q_age": row.get("age"),
                            "q_gender": row.get("gender"),
                            "q_title": row.get("title"),
                            "q_position": row.get("position"),
                            "q_new_and_old": row.get("new_and_old"),
                            "q_party": row.get("party"),
                            "q_kaiha": row.get("kaiha"),
                            "q_shicho_or_giin": row.get("shicho_or_giin"),
                            "a_市議選日": next_row.get("市議選日"),
                            "a_giin_id": next_row.get("giin_id"),
                            "a_city_name": next_row.get("city_name"),
                            "a_name": next_row.get("name"),
                            "a_kana": next_row.get("kana"),
                            "a_age": next_row.get("age"),
                            "a_gender": next_row.get("gender"),
                            "a_title": next_row.get("title"),
                            "a_position": next_row.get("position"),
                            "a_new_and_old": next_row.get("new_and_old"),
                            "a_party": next_row.get("party"),
                            "a_kaiha": next_row.get("kaiha"),
                            "a_shicho_or_giin": next_row.get("shicho_or_giin"),
                        })
                        i += 2
                        continue
            i += 1

        # 保存
        if paired_rows:
            paired_df = pd.DataFrame(paired_rows)
            output_name = filename.replace("_qa.csv", "_paired.csv")
            output_path = os.path.join(output_folder, output_name)
            paired_df.to_csv(output_path, index=False, encoding="utf-8")
            print(f"✔ 処理完了: {filename} → {output_name}")
        else:
            print(f"⚠ ペアなしスキップ: {filename}")

print("✅ 全ファイルの処理が完了しました。")
