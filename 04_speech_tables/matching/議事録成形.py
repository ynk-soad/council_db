import re
import os
import pandas as pd
import time

# ○◆◎から始まる行の場合、1つ目の"　"を":"に変換する関数
def replace_nearby_fullwidth_space(text, markers, distance=20):
    pattern = r'([{}].{{0,{}}})\u3000'.format(re.escape(markers), distance)
    return re.sub(pattern, lambda m: m.group(1) + ';', text)

# 全角数字を半角に変換する関数
def convert_fullwidth_to_halfwidth(text):
    return re.sub(r'[０-９]', lambda x: chr(ord(x.group()) - 0xFEE0), text)

# 文字間の1文字分の空白を削除する関数
def remove_single_spaces_between_characters(text):
    return re.sub(r'(?<=\S)\s(?=\S)', '', text)

# 入力フォルダと出力フォルダの指定
input_folder = "/Users/ynkhiru09/Downloads/miyazaki"  # 入力フォルダのパス
output_folder = "/Users/ynkhiru09/Downloads/miyazaki/改訂"  # 出力フォルダのパス
os.makedirs(output_folder, exist_ok=True)  # 出力フォルダが存在しない場合、作成する

# フォルダ内のテキストファイル一覧を取得
file_list = [f for f in os.listdir(input_folder) if f.endswith(".txt")]

# 名前マッチング用のデータフレームを読み込み
name_matching_csv = "/Users/ynkhiru09/Downloads/miyazaki/宮崎市マッチング.csv"  # 名前マッチングCSVファイルのパス
df = pd.read_csv(name_matching_csv)
print("名前マッチングデータ:", df)

# キーワードの指定
keywords = ["開議", "開会"]

# 正規表現パターン
pat = r'(開議\s*\d{1,2}時\d{1,2}分)'

stime = time.time()

# ファイルごとの処理
for file_name in file_list:
    print(f"{file_name} を処理中...")
    input_path = os.path.join(input_folder, file_name)
    output_path = os.path.join(output_folder, f"{file_name}")

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 前処理: 全角→半角変換
    text = replace_nearby_fullwidth_space(text, "○◆◎◯●◇")
    text = convert_fullwidth_to_halfwidth(text)
    text = text.replace("\u3000", "")

    # 文字間の1文字分の空白を削除
    text = remove_single_spaces_between_characters(text)

    # 正規表現によるキーワード以降のテキスト抽出
    keyword_positions = [text.find(keyword) for keyword in keywords if keyword in text]
    if keyword_positions:
        start_position = min(keyword_positions)
        text = text[start_position:]
    else:
        print(f"キーワードが見つからないためスキップ: {file_name}")
        continue

    #    # 名前の置換
    for _, row in df.iterrows():
        # NaN 回避 & 文字列化
        surname = str(row['苗字'])
        role = str(row['役職'])
        fullname = str(row['フルネーム'])

        if not surname or not role or not fullname:
            continue

        # 1) 「苗字＋役職」パターンをフルネームに置換
        #    例: 「馬渡議員」 -> 「馬渡光春」
        pattern1 = re.escape(surname + role)
        text = re.sub(pattern1, fullname, text)

        # 2) かっこ付きの名前をフルネームに置換
        #    前処理で全角・半角スペースを消しているので、
        #    「（松本　匠君）」 → 「（松本匠君）」になっている前提でマッチさせる
        #    例: 「14番（松本匠君）」 -> 「14番（松本匠）」 みたいなイメージ
        kakko_pattern = r"（" + re.escape(surname) + r"[^）]*?君）"
        # かっこの中身をフルネームに差し替える
        text = re.sub(kakko_pattern, f"（{fullname}）", text)


    # 結果の保存
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

ftime = time.time()
print(f"全ての処理が完了しました。実行時間: {int(ftime - stime)} 秒")
