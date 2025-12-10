# coding: utf-8
# this code for discuss net

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import random
import re
import os

# ダウンロード先のフォルダを指定
DOWNLOAD_FOLDER = r"C:\Users\monst\Desktop\沖縄市"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)  # フォルダがなければ作成

EXCLUDE_WORD = ['資料','一覧','質問','日程','議員','告示','委員会']

# Chromeのオプション設定
options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_FOLDER,  # ダウンロード先フォルダを指定
    "download.prompt_for_download": False,  # ダウンロード時の確認ダイアログを無効化
    "download.directory_upgrade": True,  # ディレクトリが変更された場合に自動的にアップグレード
    "safebrowsing.enabled": True  # セーフブラウジングを有効化
})

# Chromeのドライバを起動
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 時間計測用
stime = time.time()

# 対象年の範囲（2024年〜2011年）
years_to_scrape = range(2024, 2010, -1)

#市町村コード
jiscode = "47211"

for target_year in years_to_scrape:
    url = f'https://ssp.kaigiroku.net/tenant/okinawa/MinuteBrowse.html?tenant_id=563&view_years={target_year}'
    print(f"\n===== {target_year}年のページへアクセス中 =====")
    driver.get(url)
    time.sleep(random.uniform(1.5, 2.5))

    processed_meetings = []

    while True:
        time.sleep(random.uniform(1.5, 2.5))
        rows = driver.find_elements(By.CSS_SELECTOR, '#council_list tr')

        found_new_meeting = False
        for row in rows:
            try:
                link_element = row.find_element(By.CSS_SELECTOR, 'a.link-council')
                link_text = link_element.text

                if link_text in processed_meetings:
                    continue

                print("処理中の会議:", link_text)

                # 和暦を西暦に変換
                match_y = re.search(r'平成(\d{2})年', link_text)
                if match_y:
                    year_w = int(match_y.group(1))
                    year_s = year_w + 1988
                else:
                    match_r_gannen = re.search(r'令和[\s　]*元年', link_text)
                    if match_r_gannen:
                        year_s = 2019
                    else:
                        match_r = re.search(r'令和[\s　]*(\d{1,2})年', link_text)
                        if match_r:
                            year_r = int(match_r.group(1))
                            year_s = 2018 + year_r
                        else:
                            year_s = target_year

                print("西暦：", year_s, "年")
                time.sleep(1)

                if any(word in link_text for word in EXCLUDE_WORD):
                    pass
                elif '定例会' in link_text or '臨時会' in link_text:
                    processed_meetings.append(link_text)
                    found_new_meeting = True
                    link_element.click()
                    time.sleep(1.5)

                    links = driver.find_elements(By.CLASS_NAME, 'link-minute-view')
                    for i in range(len(links)):
                        title = links[i].text
                        match_md = re.search(r'(\d{2})月(\d{2})日', title)
                        if match_md:
                            month, day = match_md.groups()
                            month_date = f"{month}{day}"
                        else:
                            month_date = "0000"

                        file_name = f"{year_s}{month_date}{jiscode}.txt"
                        print(file_name, "を保存中...")
                        time.sleep(1)

                        links[i].click()
                        time.sleep(random.uniform(1.5, 2.5))

                        try:
                            driver.find_element(By.ID, "tab-minute-plain").click()
                        except:
                            print("議事録タブが見つかりませんでした")
                            driver.back()
                            continue

                        elements = driver.find_elements(By.CLASS_NAME, 'info-txt')
                        texts = [element.text for element in elements]

                        # ダウンロード先にファイルを保存
                        with open(os.path.join(DOWNLOAD_FOLDER, file_name), 'w', encoding='utf-8') as file:
                            file.write('\n'.join(texts))
                        driver.back()

                    try:
                        meeting_list_button = driver.find_element(By.ID, "btn-council-list")
                        meeting_list_button.click()
                        time.sleep(random.uniform(1.5, 2.5))
                    except Exception as e:
                        print("会議一覧ボタンが見つかりませんでした:", e)
                        driver.back()

            except Exception as e:
                print(f"エラーが発生しました: {e}")
                continue

        if not found_new_meeting:
            print(f"{target_year}年の処理が完了しました。")
            break

# 終了処理
driver.quit()
ftime = time.time()
print("\nすべての処理が完了しました。")
print("実行時間：", round(ftime - stime, 2), "秒")

