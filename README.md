# KabuSys

日本株向けの自動売買・データプラットフォームライブラリ（KabuSys）。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、監査ログ、マーケットカレンダー管理、研究ユーティリティなどを含むモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のアルゴリズム取引に必要なデータ基盤と分析ツールを提供します。主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と LLM（OpenAI）によるニュースセンチメント評価
- 市場レジーム判定（ETF MA + マクロニュース融合）
- ファクター計算（モメンタム/バリュー/ボラティリティ等）と研究ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定まで追跡可能な監査ログテーブル（DuckDB）
- 運用環境（development / paper_trading / live）を意識した設定管理

設計方針として「ルックアヘッドバイアス防止」「冪等性（idempotency）」「フェイルセーフ」「外部 API のレート制御/リトライ」を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save 関数、認証・レート制御・リトライ）
  - ニュース収集（RSS 取得・前処理・保存）
  - カレンダー管理（is_trading_day 等）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを LLM にかけて銘柄別センチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- research/
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- config.py
  - .env / .env.local 自動読み込み（無効化可）と環境変数経由の設定アクセス（settings オブジェクト）

---

## 要件（主な依存）

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （標準ライブラリ: urllib, json, datetime, logging 等）

インストール例（仮）:
```bash
python -m pip install duckdb openai defusedxml
# もしパッケージ化されていれば:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして、パッケージをインストール（開発モード等）。
2. 必要な Python パッケージをインストール。
3. .env を作成して必要な環境変数を設定（下記参照）。
   - プロジェクトルートにある `.env` / `.env.local` は自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨ディレクトリ（例）:
- data/ ディレクトリを作成しておくとデフォルトの DuckDB / SQLite パスがその中に作られます。

---

## 必須・主要な環境変数

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI を用いる AI 処理で必要（score_news / score_regime）。関数引数で渡すことも可能。

オプション（デフォルト値あり）:
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / ... （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

注意: config.Settings によって環境値は検証されます。必須変数が未設定の場合は ValueError が発生します。

---

## 使い方（主要ユースケース）

以下は簡単な実行例です。実行はプロジェクトの仮想環境内で行ってください。

1) DuckDB 接続を作り、日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースセンチメントを評価して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定（ma200 + macro news）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化する
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# settings.duckdb_path を使うか専用ファイルを指定
conn_audit = init_audit_db(settings.duckdb_path)
# または ":memory:" でインメモリ DB
```

5) 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# momentum は各銘柄ごとの dict のリスト
```

---

## 設計上の注意 / 運用メモ

- ルックアヘッドバイアスを避けるため、ほとんどの関数は date や conn を引数に取り、内部で date.today() 等に依存しない設計です。
- OpenAI 呼び出し（news_nlp / regime_detector）はリトライやフォールバック（失敗時に 0.0 等）を実装していますが、API キーとレート管理は適切に行ってください。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter とリトライを備えています。get_id_token は自動リフレッシュされます。
- DuckDB の executemany に空リストを渡すとバージョンによっては例外が出るため、コード側で空チェックを行っています。
- news_collector では SSRF 対策・gzip サイズ制限・XML 安全パーサ（defusedxml）を使用しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - quality.py
  - stats.py
  - calendar_management.py
  - news_collector.py
  - audit.py
  - etl.py (簡易エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (監視関連モジュールはコードベースに含まれています（省略））
- execution/, strategy/, monitoring/ 等（パッケージエクスポート上は存在）

各モジュールの責務はソース内ドキュメント（docstring）に詳述されています。実運用前に README と docstring を参照の上、テスト環境で動作確認してください。

---

## 開発・テスト

- 環境変数読み込みは .env / .env.local をプロジェクトルート（.git または pyproject.toml のある階層）から自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して無効化できます。
- OpenAI 呼び出し等は内部で分離されたラッパを使っているため、unittest.mock.patch による差し替えがしやすくなっています（例: kabusys.ai.news_nlp._call_openai_api をモック）。

---

この README はコードベースに含まれる docstring と実装から要点をまとめたものです。より詳細な運用手順（実際の ETL スケジュール、Slack 通知設定、kabuステーションの発注実装など）は運用ドキュメントを別途用意してください。