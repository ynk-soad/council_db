import os
import pandas as pd

input_folder = "/Users/ynkhiru09/Downloads/osaka_hatsugen"    
output_folder = "/Users/ynkhiru09/Downloads/osaka_"  

os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.endswith(".csv"):
        file_path = os.path.join(input_folder, filename)
        df = pd.read_csv(file_path)

        # 議長の発言を除外
        df = df[df["gicho"] != 1.0].copy()

        # 発言区分の設定
        df["question"] = None
        df["answer"] = None

        # 議員で市長ではない発言者をベースに
        is_giin = df["giin_id"].notna()
        is_shicho = df["shicho_or_giin"] == 1.0
        is_normal_giin = is_giin & ~is_shicho

        # 質問らしい語
        question_keywords = [
            "質問", "尋ね", "伺い", "答弁", "求め", "所見",  "お考え", "考え",
            "どうか", "いかが", "明らかに", "いただけますか", "どうなっている", 
            "お聞きしたい", "教えて", "お答え", "取り上げ", "取り組み", "なりますか", 
            "でしょうか", "討論"
        ]
        # 除外したい語
        question_exclude_keywords = [
            "質問を終わります", "ご答弁ありがとうございました", "以上でございます", "以上です",
            "ご清聴ありがとうございました",
            "休憩", "質問は終了","登壇","許します"
        ]

        # 質問語を含むかどうか
        keyword_mask = df["statement"].astype(str).apply(
            lambda x: any(kw in x for kw in question_keywords)
        )

        # 除外語を含むかどうか
        exclude_mask = df["statement"].astype(str).apply(
            lambda x: any(bad in x for bad in question_exclude_keywords)
        )

        # 最終的なquestionのマスク
        mask_question = is_normal_giin & keyword_mask & ~exclude_mask
        mask_answer = ~mask_question & (~is_giin | is_shicho)

        df.loc[mask_question, "question"] = df.loc[mask_question, "statement"]
        df.loc[mask_answer, "answer"] = df.loc[mask_answer, "statement"]


        # 必要なカラムのみ抽出（speakerを一番左に）
        # 不要な空行を削除
        df_output = df[["speaker", "question", "answer", "kaigi_id", "ID_teirei", "市議選日", "giin_id", "city_name", "name", "kana", "age", "gender", "title", "position", "new_and_old", "party", "kaiha", "shicho_or_giin"]]
        df_output = df_output[~((df_output["question"].fillna("").str.strip() == "") & (df_output["answer"].fillna("").str.strip() == ""))]


        def wrap_text(text, width=50):
          if pd.isna(text):
            return ""
          return "\n".join([text[i:i+width] for i in range(0, len(text), width)])

        df_output["question"] = df_output["question"].apply(lambda x: wrap_text(x, 50))
        df_output["answer"] = df_output["answer"].apply(lambda x: wrap_text(x, 50))

        # 出力ファイル名を生成
        output_filename = filename.replace(".csv", "_QA.csv")
        output_path = os.path.join(output_folder, output_filename)

        # CSVとして保存（utf-8でBOM無し）
        df_output.to_csv(output_path, index=False, encoding="utf-8")

        print(f"Processed:  {output_filename}")

print("すべてのファイル処理が完了しました。")
