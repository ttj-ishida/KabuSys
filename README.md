# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants / kabuステーション / OpenAI 等と連携し、データ収集（ETL）、品質チェック、ニュースNLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログの管理などを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB ベースのローカルデータストアで ETL を行い冪等性を重視
- 外部 API 呼び出しはリトライ／バックオフ／レート制御を備える
- OpenAI は JSON Mode を用いて機械可読なレスポンスを期待する
- テスト容易性のためキー関数は差し替え可能（モック可能）

---

## 機能一覧

- データ取得 / ETL（J-Quants）
  - 株価日足（OHLCV）取得・保存（fetch_daily_quotes / save_daily_quotes）
  - 財務情報取得・保存（fetch_financial_statements / save_financial_statements）
  - JPX マーケットカレンダー取得・保存（fetch_market_calendar / save_market_calendar）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック（quality）
  - 欠損チェック、主キー重複、スパイク検出、日付整合性チェック
- ニュース収集（news_collector）
  - RSS 取得、前処理、raw_news への冪等保存（SSRF / Gzip / XML 攻撃対策あり）
- ニュース NLP（ai.news_nlp）
  - OpenAI を用いた銘柄ごとのニュースセンチメント評価（ai_scores への書き込み）
- マーケットレジーム判定（ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離 + マクロニュースセンチメントの合成で日次レジーム算出
- リサーチ用ファクター計算（research）
  - モメンタム、ボラティリティ、バリュー等の定量ファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 監査ログ / トレーサビリティ（data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
- 設定管理（config）
  - .env（.env.local）または環境変数からの自動読み込みと Settings API

---

## 要件

- Python 3.10+
- 依存パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml

インストール例（プロジェクトルートで仮想環境を作成した上で）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ化されている場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # requirements.txt がある場合
   # 主要パッケージを個別にインストールする場合:
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   プロジェクトルートの `.env` / `.env.local` を用いるか、OS 環境変数を設定します。自動読み込みはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   主要な環境変数例（.env の例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development  # development|paper_trading|live
   LOG_LEVEL=INFO
   ```

   注意点:
   - 設定は Settings クラス経由で取得できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。
   - 自動環境変数ロードは、プロジェクトルートを .git または pyproject.toml を基準に検出して `.env` / `.env.local` を読み込みます。

4. データベースディレクトリの作成（必要に応じて）
   - デフォルトでは DUCKDB_PATH = data/kabusys.duckdb、SQLITE_PATH = data/monitoring.db

---

## 使い方（主要な API と例）

以下は Python REPL / スクリプト内での利用例です。事前に適切な環境変数（特に J-Quants のトークンや OPENAI_API_KEY）を設定してください。

- DuckDB 接続の生成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（ai.news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print(f"書き込み銘柄数: {n_written}")
```

- マーケットレジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- ニュース RSS の取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 監査ログスキーマの初期化（監査用 DB を新規に作る場合）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn に対して監査テーブルが作成される
```

- カレンダー・ヘルパー例
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

---

## 重要な挙動・運用メモ

- 環境変数の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を検出）から .env → .env.local の順で読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し:
  - gpt-4o-mini を用いた JSON Mode を期待しています。API エラー時はフェイルセーフによりスコアを 0.0 にフォールバックする設計箇所があります。
- J-Quants API:
  - レート制御（120 req/min）とリトライを組み込んでいます。
  - get_id_token によりリフレッシュトークンから ID トークンを取得します（settings.jquants_refresh_token が必要）。
- DuckDB の executemany で空リストを渡すとエラーになるバージョン対応のため、空リストチェックを行ってから実行しています。
- 日付は基本的に naive date / datetime（UTCで解釈）を扱う設計です。ETL / 監査テーブルではタイムスタンプを UTC で保存するよう設定します。

---

## ディレクトリ構成

主要ファイル・ディレクトリの概要（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の公開
    - news_collector.py      — RSS 収集 / 前処理
    - calendar_management.py — 市場カレンダー管理・営業日計算
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - research/（その他モジュール）
  - (その他のトップレベルパッケージ: strategy, execution, monitoring を __all__ で公開予定)

各モジュールは README の該当箇所に示した責務を持ち、DuckDB 接続や外部 API キーを引数または環境変数経由で受け取ります。

---

## 開発・テスト

- モジュール内部の外部 API 呼び出し部（OpenAI / urllib / jq client 等）はモック可能に設計されています。ユニットテスト時は該当関数をパッチして挙動をコントロールしてください。
- 自動環境読み込みやファイル I/O を無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用できます。

---

質問や追加で欲しい使い方（例: バックテスト連携、運用ジョブの cron 設定例、Slack 通知の実装例）があれば教えてください。必要に応じて README を補強してサンプルスクリプトや運用手順を追加します。