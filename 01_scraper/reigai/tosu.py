# coding: utf-8
# このコードは鳥栖市の議事録サイトからPDFを自動ダウンロードするためのものです

import os
import re
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

DOWNLOAD_FOLDER = "/Users/ynkhiru09/Downloads/tosu"
JIS_CODE = "41203"

options = Options()
options.add_argument("--headless")  # ヘッドレスモードで実行
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_FOLDER,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

print("ディレクトリ：", DOWNLOAD_FOLDER)
print("市町村コード：", JIS_CODE)

start_time = time.time()

for year in range(2024, 2010, -1):
    url = f"https://ssp.kaigiroku.net/tenant/tosu/SpMinuteBrowse.html?tenant_id=545&view_years={year}"
    driver.get(url)
    time.sleep(2)

    sections = driver.find_elements(By.CSS_SELECTOR, "ul.parent_bar")
    for section in sections:
        try:
            heading = section.find_element(By.XPATH, "./preceding-sibling::h2[1]").text.strip()
            if not ("定例会" in heading or "臨時会" in heading):
                continue
            print("▶", heading)

            links = section.find_elements(By.CSS_SELECTOR, "ul.child_bar > li > a")
            for link in links:
                title = link.text
                href = link.get_attribute("href")
                print("▶▶", title)
                date_match = re.search(r'(\d{2})月(\d{2})日', title)
                if date_match:
                    mm, dd = date_match.groups()
                    yyyymmdd = f"{year}{mm}{dd}"
                else:
                    print("⚠ 日付抽出失敗:", title)
                    yyyymmdd = f"{year}0000"

                file_name = f"{yyyymmdd}{JIS_CODE}.pdf"

                # 新しいタブで開く
                driver.execute_script("window.open(arguments[0]);", href)
                driver.switch_to.window(driver.window_handles[1])
                time.sleep(2)

                try:
                    # 編集モードに移動
                    driver.find_element(By.ID, "edit_icon").click()
                    time.sleep(1)

                    # 全選択 → 印刷 → ダウンロード
                    driver.find_element(By.ID, "allcheck_icon").click()
                    time.sleep(0.5)
                    driver.find_element(By.ID, "download_icon").click()
                    time.sleep(2)
                    print("✅ ダウンロード実行:", file_name)

                except Exception as e:
                    print("⚠ 会議内処理失敗:", e)

                # タブを閉じて戻る
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)

        except Exception as e:
            print("⚠ セクション処理失敗:", e)
            continue

driver.quit()
end_time = time.time()
print("\nすべての処理が完了しました。")
print("実行時間：", round(end_time - start_time, 2), "秒")
