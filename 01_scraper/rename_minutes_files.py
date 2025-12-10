import os
import re

# 実行対象のフォルダと市町村コードをここで指定
folder_path = "/Users/ynkhiru09/Downloads/a"
city_code = "27000"

def read_file_with_encodings(file_path, encodings=["cp932", "utf-8"]):
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"対応するエンコーディングで読み込めません: {file_path}")

kanji_numerals = {
    "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10
}

def kanji_to_number(kanji: str) -> int:
    """漢数字（簡易）を整数に変換（最大で31まで想定）"""
    if not kanji:
        return None
    if kanji == "十":
        return 10
    if "十" in kanji:
        parts = kanji.split("十")
        if parts[0] == "":
            tens = 1
        else:
            tens = kanji_numerals.get(parts[0], 0)
        units = kanji_numerals.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens * 10 + units
    else:
        return kanji_numerals.get(kanji, 0)

def rename_files_with_date_code_and_year(folder_path, city_code):
    date_pattern_arabic = re.compile(r'(\d{1,2})月\s*(\d{1,2})日')
    date_pattern_kanji = re.compile(r'([一二三四五六七八九十〇]+)月\s*([一二三四五六七八九十〇]+)日')
    year_pattern_heisei = re.compile(r'平成[\s　]*(\d{1,2})年')
    year_pattern_reiwa_gannen = re.compile(r'令和[\s　]*元年')
    year_pattern_reiwa = re.compile(r'令和[\s　]*(\d{1,2})年')

    files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    date_file_map = {}

    for filename in files:
        file_path = os.path.join(folder_path, filename)
        try:
            text = read_file_with_encodings(file_path)
        except UnicodeDecodeError:
            print(f"読み込みエラー: {filename}")
            continue

        date_found = None
        year_found = None

        for line in text.splitlines():
            line = line.strip()
            line = line.replace("　", " ")  # 全角スペースを半角に
            if line:
                # アラビア数字の日付
                date_match = date_pattern_arabic.search(line)
                if date_match:
                    month = int(date_match.group(1))
                    day = int(date_match.group(2))
                    date_found = f"{month:02}{day:02}"
                else:
                    # 漢数字の日付
                    date_match_k = date_pattern_kanji.search(line)
                    if date_match_k:
                        month = kanji_to_number(date_match_k.group(1))
                        day = kanji_to_number(date_match_k.group(2))
                        if month and day:
                            date_found = f"{month:02}{day:02}"

                match_heisei = year_pattern_heisei.search(line)
                if match_heisei:
                    year_found = 1988 + int(match_heisei.group(1))
                else:
                    match_reiwa_gannen = year_pattern_reiwa_gannen.search(line)
                    if match_reiwa_gannen:
                        year_found = 2019
                    else:
                        match_reiwa = year_pattern_reiwa.search(line)
                        if match_reiwa:
                            year_found = 2018 + int(match_reiwa.group(1))

            if date_found and year_found:
                break

        if date_found and year_found:
            key = f"{year_found}{date_found}"
            if key not in date_file_map:
                date_file_map[key] = []
            date_file_map[key].append(file_path)
        else:
            print(f"必要な情報が見つかりませんでした: {filename}")

    for date_key, paths in date_file_map.items():
        new_filename = f"{date_key}{city_code}.txt"
        new_file_path = os.path.join(folder_path, new_filename)

        if len(paths) == 1:
            try:
                os.rename(paths[0], new_file_path)
                print(f"単独リネーム: {os.path.basename(paths[0])} → {new_filename}")
            except Exception as e:
                print(f"リネーム失敗: {e}")
        else:
            meibo_files = [p for p in paths if "名簿" in os.path.basename(p)]
            other_files = [p for p in paths if "名簿" not in os.path.basename(p)]
            ordered_paths = meibo_files + other_files

            merged_content = ""
            for path in ordered_paths:
                try:
                    text = read_file_with_encodings(path)
                    merged_content += text + "\n"
                except UnicodeDecodeError:
                    print(f"結合スキップ: {os.path.basename(path)}")

            with open(new_file_path, 'w', encoding='utf-8') as new_file:
                new_file.write(merged_content)

            for path in paths:
                os.remove(path)

            print(f" {new_filename}")

# 実行
rename_files_with_date_code_and_year(folder_path, city_code)