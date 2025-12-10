##coding == "utf-8"
# this code for ssp.kaigiroku.net

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import random 
import re
import os

# 市町村コードの指定
jiscode = 38206

# 出力先を指定
path = "/Users/ynkhiru09/Library/CloudStorage/OneDrive-KansaiUniversity/四国/愛媛県/saijo"
os.chdir(path)
print("ディレクトリ：", os.getcwd())
print("市町村コード：", jiscode)

# 時間計測
starttime = time.time()

# アクセス制限を回避すべくIPを変える。
proxy_ip = "36.89.212.253"
proxy_port = "8080"
chrome_options = Options()
chrome_options.add_argument(f"--proxy-server=http://{proxy_ip}:{proxy_port}")

"""
https://x.gd/pZTIv
https://www.proxynova.com/proxy-server-list/
"""

driver = webdriver.Chrome()
url = 'https://ssp.kaigiroku.net/tenant/saijo/SpMinuteBrowse.html?tenant_id=507&view_years=2019'
driver.get(url)
# 最大の読み込み時間を設定,今回は最大30秒待機できるようにする
wait = WebDriverWait(driver=driver, timeout=30)
time.sleep(random.uniform(1.5, 2.5))
ul_element = driver.find_element(By.CLASS_NAME, 'parent_bar')
li_elements = ul_element.find_elements(By.TAG_NAME, 'li')

# 各<li>要素のテキストを出力
wait.until(EC.presence_of_all_elements_located)
for li in li_elements:
    if "定例会" in li.text or "臨時会" in li.text:
        print("会議名称：", li.text)
        time.sleep(random.uniform(1.5, 2.5))

        # 年を取得
        year_s = None
        if match_y := re.search(r'平成[\s　]*(\d{2})年', li.text):
            year_s = int(match_y.group(1)) + 1988
        elif re.search(r'令和[\s　]*元年', li.text):
            year_s = 2019
        elif match_r := re.search(r'令和[\s　]*(\d{1,2})年', li.text):
            year_s = 2018 + int(match_r.group(1))
        elif match_s := re.search(r'(\d{4})年', li.text):
            year_s = int(match_s.group(1))
        else:
            print("年の取得に失敗:", li.text)
            continue

        print("西暦：", year_s, "年")
        name = li.text

        # 当該会議をクリック
        li.click()
        wait.until(EC.presence_of_all_elements_located)
        time.sleep(random.uniform(1.5, 2.5))


        # 会議日程のリストを取得
        date_list = driver.find_elements(By.CSS_SELECTOR, 'ul.child_bar > li')

        for k_date in date_list:
            if re.search(r'\d{2}号', k_date.text):
                print("対象会議:", k_date.text)
                wait.until(EC.presence_of_all_elements_located)
                time.sleep(random.uniform(1.5, 2.5))

                match_md = re.search(r'(\d{2})月(\d{2})日', k_date.text)
                if match_md:
                    month, day = match_md.groups()
                    month_date = f"{int(month):02}{int(day):02}"
                else:
                    print("日付情報が取得できませんでした:", k_date.text)
                    continue

                file_name = f"{year_s}{month_date}{jiscode}.txt"
                print(file_name, "を保存中...")

                k_date.click()
                wait.until(EC.presence_of_all_elements_located)
                time.sleep(random.uniform(1.5, 2.5))

                tr_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.minute_text.open'))
                )

                tr_texts = [tr.text for tr in tr_elements]
                print(tr_texts)

                with open(file_name, 'w', encoding='utf-8') as file:
                    file.write('\n'.join(tr_texts))

                time.sleep(random.uniform(1.5, 2.5))
                driver.back()

        img_element = driver.find_element(By.CSS_SELECTOR, 'img[src="images/pr_arrow.png"][class="rotate"]')
        img_element.click()
        wait.until(EC.presence_of_all_elements_located)
        time.sleep(random.uniform(1.5, 2.5))

endtime = time.time()
driver.quit()

print("実行時間：", int(endtime - starttime), "秒")
