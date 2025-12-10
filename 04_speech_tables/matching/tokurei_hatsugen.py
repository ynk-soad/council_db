from bs4 import BeautifulSoup
import re
import os
import pandas as pd
import time

def replace_number_with_marker(text, marker="○"):
    # 各行の先頭に数字があれば、その数字を「○」に置き換える
    # 数字を検出して置き換え
    return re.sub(r'^\d+', marker, text)
m = "○"

def replace_nearby_fullwidth_space(text, markers, distance=25):
    # 正規表現パターンを修正：記号（○など）から指定された距離内の全角スペースを最初にマッチ
    pattern = r'([{}].{{0,{}}})　'.format(re.escape(markers), distance)
    
    # 最初に現れる全角スペースまでを最短マッチし、そこにコロンを追加
    return re.sub(pattern, lambda m: m.group(1) + '：', text)

def convert_fullwidth_to_halfwidth(text):
  return re.sub(r'[０-９]', lambda x: chr(ord(x.group()) - 0xFEE0), text)


#ファイルが含まれるディレクトリ
folder_path = "/Users/ynkhiru09/Downloads/shimabara"
file_list = os.listdir(folder_path)

keywords = ["開会"]

stime = time.time()

#苗字→フルネーム用のデータフレーム
df = pd.read_csv("/Users/ynkhiru09/Downloads/shimabara/島原市マッチング.csv")
print(df)

pat = r'(○開会午.*?時\d{2}分)'

for file_name in file_list:
    t = ""
    if file_name.endswith(".txt"):
        print(file_name,"を実行中...")
        file_path = os.path.join(folder_path, file_name)
        #ファイル名から会議IDの取得
        kaigi_id = file_name[:13]
        export_path = file_path.replace("html", "txt")
        f = open(file_path, "r", encoding="utf-8")
        html_content = f.read()
        
        soup = BeautifulSoup(html_content, "html.parser")
        #テキストの抽出
        # class="page-text__voice" の要素を取得
        page_text_voice = soup.find_all(class_="page-text__voice")

        # 取得した要素を順番に格納（リストに保存）
        elements = []
        for voice_element in page_text_voice:
            text = voice_element.get_text(strip=True)

            # 臨時議長2名は予めリネーム
            text = text.replace("赤井臨時議長","赤井佐太郎")
            text = text.replace("岡本臨時議長","岡本𠮷司")
            text = replace_number_with_marker(text)
            text = replace_nearby_fullwidth_space(text,m)
            text = convert_fullwidth_to_halfwidth(text)
            text = text.replace("\u3000","")
            match = re.search(pat, text)
            if match:
                result = match.group(1) # マッチした部分の前に特定の文字（例：○）を差し込む 
                text = result + '○'

            text = text.replace("○○","○")

            for _, row in df.iterrows():
                # パターンを作成 (苗字と役職にマッチする部分を検索)
                pattern = f"○{row['苗字']}{row['役職']}"

                # フルネームに置換
                replacement = f"○{row['フルネーム']}"
                
                # パターンに一致する箇所を置換
                text = re.sub(pattern, replacement, text)
            t = t + text
            
            keyword_positions = [t.find(keyword) for keyword in keywords if keyword in t]
            # 発言テーブルに目次等が入り込まないために予め削除する。
            if not keyword_positions:
                continue  # キーワードが見つからない場合、空の文字列を返す
            # 最初のキーワードの位置を取得
            start_position = min(keyword_positions)
            # キーワードの位置以降のテキストを抽出
            t_r = t[start_position:]

            """print(text)
            print("##################################################################################")
            print("##################################################################################")
            """
            # inner HTML or text can be extracted
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        print(t_r)
        with open(export_path, mode='w',encoding = "utf-8") as f:
            f.write(t_r)

ftime = time.time()
print("実行時間：",int(ftime-stime),"秒")
