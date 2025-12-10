import re
import pandas as pd
import os
import chardet

# ファイルのエンコーディングを検出する関数
def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']

# 空のデータフレームと配列を作成
df = pd.DataFrame(columns=["speaker", "statement"])

# エラーログ用のリストを作成
error_log = []

# ファイルが含まれるディレクトリ
folder_path = "/Users/ynkhiru09/Downloads/osaka/osaka/2019"
file_list = os.listdir(folder_path)

# 委員会テーブルの読み込みと整形
legiinfo_coltype = {'ID_teirei': 'str'}
legi_info_path = "/Users/ynkhiru09/Downloads/osaka/osaka/2019/osaka_iinkai.csv"
legi_info_encoding = detect_encoding(legi_info_path)
legi_info = pd.read_csv(legi_info_path, dtype=legiinfo_coltype, encoding=legi_info_encoding)
legi_info = legi_info.dropna(subset=['ID_teirei'])
legi_info['name'] = legi_info['name'].str.replace('　', '')
legi_info['name'] = legi_info['name'].str.replace(' ', '')
print(legi_info)

# 会議テーブルの読み込みと必要部分の抽出
regmtg_coltype = {'ID_teirei': 'str', 'kaigi_id': 'str'}
regular_mtg_path = "/Users/ynkhiru09/Downloads/osaka/osaka/2019/osaka_kaigi.csv"
regular_mtg_encoding = detect_encoding(regular_mtg_path)
regular_mtg = pd.read_csv(regular_mtg_path, dtype=regmtg_coltype, encoding=regular_mtg_encoding)

# 列名の確認
print("Columns in regular_mtg:", regular_mtg.columns)

# 列名が正しいかどうかを確認
if 'ID_teirei' in regular_mtg.columns and 'kaigi_id' in regular_mtg.columns:
    # 定例会IDと会議IDの欠損値の行を削除
    regular_mtg = regular_mtg.dropna(subset=['ID_teirei', 'kaigi_id'])
else:
    print("Error: 'ID_teirei' or 'kaigi_id' not found in regular_mtg")

# 誤りを修正
regular_mtg = regular_mtg[["ID_teirei", "kaigi_id"]]
print(regular_mtg) 

# 全角数字を全て半角数字に変換する関数
def convert_fullwidth_to_halfwidth(text):
    return re.sub(r'[０-９]', lambda x: chr(ord(x.group()) - 0xFEE0), text)

# 指定した文字列以降の文字列を抽出する関数を定義
def extract_text_after(name, delimiter):
    try:
        index = name.index(delimiter)
        return name[index + len(delimiter):]
    except ValueError:
        return name  # delimiterが見つからない場合、元の文字列を返す

delimiter = '（'

# 複数の単語を削除する関数を作成
def remove_words(text, words_to_remove):
    for word in words_to_remove:
        text = text.replace(word, '')
    return text

# 特定の文字化けを修正する関数
def fix_character_encoding_issues(text):
    return text.replace('.橋繁夫', '高橋繁夫')

# giin_id が欠損している行に対して speaker_raw から title を抽出
def extract_title_from_speaker_raw(raw):
    match = re.match(r"[○◆◎]?(.*?)[（(]", raw)
    if match:
        title = match.group(1).strip()
        if "市長" not in title:  # 市長だけ除外
            return title
    return ""

# 消す単語の指定
words_to_remove = ['君', 'さん', '議員', '議長', '委員長']

# 正規表現パターン
pattern = r"[○◆◎](.*?)）(.*?)(?=[○◆◎]|$)"


for file_name in file_list:
    if file_name.endswith(".txt"):
        file_path = os.path.join(folder_path, file_name)
        # ファイル名から会議IDの取得
        kaigi_id = file_name[:13]
        export_path = file_path.replace("txt", "csv")

        try:
            # ファイルのエンコーディングを検出
            file_encoding = detect_encoding(file_path)
            
            with open(file_path, "r", encoding=file_encoding) as f:
                print(f"{file_name} を読み込み中...")
                text = f.read()

            # 全角数字を半角数字に変換
            tex = convert_fullwidth_to_halfwidth(text)
            tex = tex.replace("\u3000", "")
            matches = re.findall(pattern, tex, re.DOTALL)
            array = [[match[0], match[1].strip()] for match in matches]

            # 新しいデータフレームを作成して重複を防ぐ
            temp_df = pd.DataFrame(array, columns=["speaker", "statement"])
            temp_df['kaigi_id'] = kaigi_id

            temp_df["speaker_raw"] = temp_df["speaker"]


            # 発言テーブルと委員会テーブルをマッチングするための成形
            temp_df['speaker'] = temp_df['speaker'].apply(lambda x: extract_text_after(x, delimiter))
            temp_df['speaker'] = temp_df['speaker'].apply(lambda x: remove_words(x, words_to_remove))
            temp_df['speaker'] = temp_df['speaker'].apply(fix_character_encoding_issues)

            # `statement` 列の整形: 空行削除、文中空行削除、<br>や<br>　削除
            temp_df = temp_df[temp_df['statement'].str.strip() != '']
            temp_df['statement'] = temp_df['statement'].apply(lambda x: re.sub(r'<br>\s*', '', x))

            # 会議テーブルと発言テーブルのマッチング
            df2 = pd.merge(temp_df, regular_mtg, left_on='kaigi_id', right_on='kaigi_id', how='left')

            # 発言テーブルと委員会テーブルのマッチング
            output = pd.merge(df2, legi_info, left_on=["ID_teirei", "speaker"], right_on=["ID_teirei", "name"], how='left')
            print(output)

            # 完全に重複している行を削除 (speaker と statement 列が重複する場合)
            output = output.drop_duplicates(subset=["speaker", "statement"])

            output['name'] = output.apply(
               lambda row: row['speaker'] if pd.isna(row['name']) or row['name'] == '' else row['name'],
               axis=1
            )

            # 市長を除いた職名を speaker_raw から抽出し、新たに 'position' カラムを追加
            # position カラムを議員以外（giin_idがNaN）の人だけに付与
            output["position"] = output.apply(
               lambda row: extract_title_from_speaker_raw(row["speaker_raw"]) 
               if pd.isna(row["giin_id"]) and isinstance(row["speaker_raw"], str) else "",
               axis=1
            )


            # 必要な列のみを残す
            output = output[["speaker", "statement", "kaigi_id", "ID_teirei","市議選日" ,"giin_id", "city_name","name","kana","age", "gender", "title","position", "new_and_old", "party", "kaiha", "gicho", "gicho_sub", "kansa", "shicho_or_giin"]]
            output.to_csv(export_path, encoding="utf-8", index=False)

        except Exception as e:
            # エラーログにファイル名とエラーメッセージを追加
            error_log.append(f"{file_name}: {e}")

        # dfの初期化
        df = pd.DataFrame(columns=["speaker", "statement"])

# エラーログの出力
if error_log:
    print("\nエラーが発生したファイル一覧:")
    for error in error_log:
        print(error)
else:
    print("\n全てのファイルが正常に処理されました。")
