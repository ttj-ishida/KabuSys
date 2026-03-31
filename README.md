# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム向けライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログ（発注／約定トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- ETL/保存は冪等（ON CONFLICT / DELETE→INSERT 等）で安全に実行
- 外部 API 呼び出しはリトライ / レート制御 / フェイルセーフを備える
- DuckDB を中心としたローカルDBでデータ管理

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local 自動ロード（必要に応じて無効化可能）
- データ取得・ETL（kabusys.data.pipeline, jquants_client）
  - J-Quants から株価日足 / 財務データ / マーケットカレンダーの差分取得・保存
  - ETL 実行結果を ETLResult で返す
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、URL 正規化、SSRF 保護、前処理、raw_news への保存を想定
- AI（OpenAI）を用いた解析（kabusys.ai）
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
  - それぞれ JSON Mode + 再試行・フェイルセーフ実装
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義・初期化
  - 監査DB初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

インストール例（仮の requirements が無い場合の最低限）:
```bash
python -m pip install "duckdb>=0.7" openai defusedxml
```

（実際のプロジェクトでは pyproject.toml / requirements.txt に基づくインストールを行ってください）

---

## 環境変数（主なもの）

このプロジェクトは多数の環境変数を参照します。必須のものは以下の通り。

- JQUANTS_REFRESH_TOKEN  
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY  
  - OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD  
  - kabuステーション API のパスワード（発注等に使用）
- SLACK_BOT_TOKEN  
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID  
  - Slack 通知先チャンネル ID

その他（任意・デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に 1 等を設定
- KABU_API_BASE_URL — kabu API のベース URL（デフォルトローカル）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト data/monitoring.db）

自動 .env ロードについて:
- パッケージはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、
  そこにある `.env` を読み込みます。`.env.local` は `.env` を上書きします。
- テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env.example`
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install -r requirements.txt
   # または最低限:
   pip install duckdb openai defusedxml
   ```
4. `.env` をプロジェクトルートに作成し、必要な環境変数を設定
5. DuckDB ファイルや監査DBの初期化（必要に応じて）

---

## 使い方（簡易サンプル）

以下は代表的な利用例です。実行は Python スクリプトまたは REPL から行ってください。

- DuckDB に接続して日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に保存（OpenAI API キーは環境変数または api_key 引数で指定）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # 例
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジームスコアを計算して market_regime に保存:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作られ、UTC タイムゾーンが設定されます
```

- RSS を取得（news_collector.fetch_rss の単独利用例）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 実装上の注意点 / 仕様メモ

- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を使用し、レスポンスの厳密な JSON パースを試みます。API エラーやパース失敗時はフェイルセーフとしてスコアを 0.0 にフォールバックする箇所があります。
- J-Quants API は固定レート制御（120 req/min）およびリトライロジックを実装しています。401 はトークンリフレッシュをトライします。
- ETL や保存関数は冪等に設計されています（INSERT ... ON CONFLICT / DELETE→INSERT 等）。
- news_collector は SSRF 対策、受信サイズ制限、トラッキングパラメータ除去、XML パースの安全対策（defusedxml）を備えています。
- 日付の扱いはすべて timezone を混在させないように注意（内部では UTC naive または UTC に正規化して扱う箇所が多いです）。
- 型注釈や union (|) を利用しているため Python 3.10+ を推奨します。

---

## ディレクトリ構成

（主要ファイル・モジュールの要約）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロード・設定クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント計算（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult エクスポート
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai, data, research はそれぞれの機能群を提供します。

---

## 開発 / テスト

- 自動 .env ロードを無効にしてユニットテストを行う場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI / J-Quants など外部 API 呼び出しはモックしてテストすることを推奨します（コード内でも patch しやすい設計になっています）。

---

必要に応じて README のサンプルコードや .env.example の詳細を追記できます。特定の利用ケース（ETL の定期実行、監査DB 運用、kabuステーションとの連携例など）について詳しく記述したい場合は、対象を指定してください。