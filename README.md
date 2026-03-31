# KabuSys

日本株向けの自動売買 / データパイプライン / リサーチ用ライブラリ群です。  
DuckDB をデータ層に、J-Quants API をデータ取得に、OpenAI（gpt-4o-mini など）をニュースNLP・レジーム判定に利用することを想定した設計になっています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能群を持つ Python パッケージです。

- データ収集（J-Quants から株価・財務・カレンダー）と ETL パイプライン
- ニュースの収集・前処理と LLM を使った銘柄センチメント付与
- 市場レジーム（bull / neutral / bear）の判定（ETF ma200 とマクロニュースの合成）
- 監査ログ（signal → order_request → executions）のスキーマ/初期化（DuckDB）
- ファクター計算・特徴量探索・統計ユーティリティ（リサーチ用途）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- カレンダー（JPX）管理・営業日判定ユーティリティ

設計上の特徴：
- ルックアヘッドバイアス防止（target_date を明示、内部で date.today() を直接参照しない設計）
- 冪等性を重視（DB への保存は ON CONFLICT / INSERT...DO UPDATE 等で実装）
- 外部 API 呼び出しに対する堅牢なリトライ／バックオフ処理
- DuckDB をメインの分析 DB として利用

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数の自動ロード（プロジェクトルートの .env / .env.local）と設定読み取り
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、ページネーション、レート制御、ID トークン取得
  - save_* / fetch_* 系関数で DuckDB への保存・取得を行う
- kabusys.data.pipeline
  - 日次 ETL パイプライン（run_daily_etl）や個別 ETL ジョブの実装
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news テーブルへの保存ロジック
- kabusys.ai.news_nlp
  - ニュースを LLM に投げて銘柄ごとの ai_score を生成（score_news）
- kabusys.ai.regime_detector
  - ETF（1321）の MA200 乖離とマクロセンチメント合成による市場レジーム判定（score_regime）
- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）の DDL と初期化（init_audit_db / init_audit_schema）
- kabusys.research
  - ファクター計算（momentum / value / volatility）や特徴量解析ユーティリティ

---

## 必要条件 / 推奨依存パッケージ

基本的に Python 環境で利用します。主な依存（プロジェクトに requirements があればそれに従ってください）:

- Python 3.10+（typing の演算子などを使用）
- duckdb
- openai (公式 SDK)
- defusedxml
- （標準ライブラリの urllib 等を利用）

インストール例（仮）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを開発インストールする場合
pip install -e .
```

※ 実際のプロジェクトでは requirements.txt / pyproject.toml の内容に従ってください。

---

## 環境変数 / 設定

kabusys.config.Settings により以下の環境変数が参照されます（必須項目は _require() により未設定時に例外）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先 Channel ID
- OPENAI_API_KEY — OpenAI API キー（score_news / regime で使用）

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/...）

自動 .env 読み込み:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を基準）を探し `.env` と `.env.local` を順に読み込みます。
- 自動読み込みを無効化する: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

.env のパース仕様は強めに実装されています（export 句・クォート、コメント処理等）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール
3. 必要な環境変数を設定（.env をプロジェクトルートに作成）
4. DuckDB データベースディレクトリを作成（必要なら）

例:

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -e .  # または pip install -r requirements.txt

# プロジェクトルートに .env を作る（例）
cat > .env <<EOF
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
EOF
```

---

## 使い方（簡易サンプル）

以下は代表的な利用例です。各例とも事前に環境変数を設定しておく必要があります。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# ETL を今日実行する例
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP（ai スコア）を取得して ai_scores に書き込む:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み件数:", n_written)
```

- 市場レジーム判定（score_regime）:

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または api_key 引数で渡せます
```

- 監査ログ DB 初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- ニュース RSS を単独で取得する（news_collector）:

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

src = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(src, source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- score_news / score_regime は OpenAI API を利用するため、OPENAI_API_KEY を環境変数で設定してください（または関数呼び出し時に api_key 引数で渡す）。
- DuckDB に保存されるタイムスタンプは UTC に統一されています（audit 初期化関数 は TimeZone を UTC にセットします）。

---

## ディレクトリ構成（主要ファイル）

パッケージは `src/kabusys` 配下に実装されています。主なファイル・サブパッケージ:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント付与（score_news）
  - regime_detector.py  — 市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント、保存ロジック
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — JPX カレンダー管理、営業日判定
  - news_collector.py   — RSS 収集・前処理
  - quality.py          — データ品質チェック
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - audit.py            — 監査ログ DDL / 初期化
  - etl.py              — ETLResult の公開（alias）
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記は主要ファイルの抜粋です。実装の詳細は該当ソースをご確認ください。）

---

## 設計上の注意 / 運用メモ

- ルックアヘッドバイアス防止のため、内部関数は target_date を明示的に受け取り、必要なデータは target_date を基準に過去のデータのみ参照します。バックテストや研究用途の際はこの設計方針を尊重してください。
- J-Quants のレートリミットや OpenAI のレートリミットに配慮した実装（スロットリング、指数バックオフ、リトライ）がありますが、運用時は実際の利用量に伴う制御を確認してください。
- .env の自動読み込みは便利ですが、テスト時や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- DuckDB の executemany に関するバージョン依存性（空リスト不可など）に注意している箇所があります（pipeline/news_nlp 等で対応済み）。

---

## 貢献 / 開発

- ローカルでの開発は仮想環境を使い、パッケージを editable インストールして進めるのが容易です。
- テストや CI のセットアップはプロジェクトルートの設定に従ってください（この README にはテストフレームワークや CI 設定は含まれていません）。

---

問題や不明点があれば、どの機能についての README をさらに詳しく記載するか教えてください。例えば「ETL の設定例」「OpenAI 呼び出しのモック方法」「監査ログスキーマのER図」など、用途に応じて深掘りできます。