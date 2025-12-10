#  Council DB – Japanese Local Assembly Minutes Pipeline
地方議会の議事録（会議録）を自動的に収集・整形・構造化し、  
**定例会・会議テーブル・議員マスタ・発言テーブル・Q&A 生成までを一気通貫で行う ETL + NLP パイプライン**です。

研究目的としては、全国の地方議会の議事録をデータベース化し、  
将来的に **RAG（Retrieval-Augmented Generation）による議会情報検索**を実現するプロジェクトです。

---

#  Features

## 1. 議事録スクレイピング（Scraper）
- discuss.net 対応（複数バージョン）
- PDF / HTML / TXT 形式の議事録の自動取得
- 市ごとの専用 scraper（例：大阪市、東かがわ市、鳥栖市など）
- PDF のダウンロードと命名規則統一

## 2. PDF → TXT 変換（Preprocess）
- PDF 形式の議事録を TXT 化
- UTF-8 に統一する文字コード変換
- 不要な空白・改行の整形処理

## 3. 定例会・会議テーブル生成（Meeting Tables）
- TXT/HTML から定例会情報を抽出
- 会議 ID・会議日程・開催回次などの構造化
- 自治体ごとの特殊な書式にも対応

## 4. 議員テーブル生成（Giin Tables）
- go2senkyo.com から市議会議員の候補者情報・当選者情報をスクレイピング
- 年度別議員リスト（補欠選挙を含む）の作成
- 議長・副議長・監査委員など役職を自動抽出して補完
- giin_year / giin_sakusei による統合マスタ作成

## 5. 発言テーブル生成（Speech Extraction）
- 議事録から発言者・肩書き・本文を抽出
- ○議員 / ◎市長 / ◆部長 などの記号パターンに対応
- HTML 形式の議事録専用抽出ロジック（大阪市など）
- 例外パターン（hatsugen_reigai）も処理

## 6. Q&A ペア生成（RAG 用）
- 発言内容から質問と回答を自動ペアリング
- 1発言内から最大3文以内で回答をまとめる高速処理
- GPT モデルを使った要約と整形
- RAG 検索システムへの入力用データを生成


#  Folder Structure
```
council_db/
├─ 01_scraper/ # 議事録スクレイピング
│ ├─ osaka/ # 大阪市専用 scraper / HTML パーサー
│ ├─ discuss3.py
│ ├─ pdf_dl.py
│ ├─ pdf_txt.py
│ ├─ higashikagawa.py
│ ├─ tosu.py
│ └─ rename_minutes_files.py
│
├─ 02_meeting_tables/ # 定例会・会議テーブル生成
│ ├─ teirei_sakusei_txt.py
│ ├─ teirei_sakusei_html.py
│ ├─ kaigi_sakusei.py
│ └─ teirei_kaigi_sakusei.py
│
├─ 03_giin_tables/ # 議員テーブル生成
│ ├─ giinlist_sakusei.py
│ ├─ giin_year.py
│ ├─ giin_sakusei.py
│ ├─ gicho.py
│ ├─ 副議長探索.py
│ └─ 監査委員検索.py
│
├─ 04_speech_tables/ # 発言抽出・QA生成
│ ├─ preprocess/
│ │ ├─ convert_to_utf8.py
│ │ ├─ format.py
│ │ └─ format_minutes.py
│ ├─ extraction/
│ │ ├─ 発言.py
│ │ ├─ html_hatsugen.py
│ │ └─ hatsugen_reigai.py
│ ├─ qa_generation/
│ │ ├─ hatsugen_paired.py
│ │ └─ hatsugen_qa.py
│
├─ utils/
│ └─ jiscode.json
│
├─ secrets/ (ignored)
│ └─ OPENAI_API_KEY.env
│
└─ .gitignore

yaml
コードをコピーする
```


#  How to Setup

## 1. Clone repository
git clone https://github.com/ynk-soad/council_db.git

shell
コードをコピーする

## 2. Python 環境構築
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt # （必要なら追加）

bash
コードをコピーする

## 3. APIキーの設定
`secrets/OPENAI_API_KEY.env` に以下を記入：

OPENAI_API_KEY=xxxx

yaml
コードをコピーする



#  Pipeline Overview
```
[01_scraper]
↓
[PDF / HTML / TXT]
↓ （convert_to_utf8 / format）
[Preprocessed Text]
↓
[02_meeting_tables / 03_giin_tables]
↓
[会議テーブル / 議員テーブル]
↓
[04_speech_tables]
↓
[発言テーブル]
↓
[QA生成（RAG 用）]

yaml
コードをコピーする
```


#  Use Cases

- 地方議会の議事録データベース構築  
- 議員・職員の発言履歴の可視化  
- 政策議論の構造分析  
- RAG による議会向け AI チャットボット  
- 行政データ分析研究の基盤整備  

---

#  Author

**Haru (ynk-soad)**  
Graduate School of Informatics  
Kansai University  

研究テーマ：  
「地方議会データのETLパイプライン構築とRAG検索システムの開発」

---

#  License

This project is released under the MIT License.
