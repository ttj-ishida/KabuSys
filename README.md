# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL、データ品質チェック、ニュース収集・NLP、リサーチ向けファクター計算、監査ログ（トレーサビリティ）、および市場レジーム判定などの機能を提供します。

主な目的：
- J-Quants API を用いた株価・財務・カレンダーの差分取得と DuckDB 保存（ETL）
- ニュース収集（RSS）と LLM を用いた銘柄センチメント評価
- ファクター計算・特徴量探索（研究用途）
- 発注フローの監査ログ用スキーマ初期化
- 市場レジーム判定（MA と マクロニュースの融合）

---

## 機能一覧

- 環境設定
  - `.env` / `.env.local` の自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を基準）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN 等）
  - 環境切替（KABUSYS_ENV: development / paper_trading / live）

- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - 日次 ETL パイプライン（run_daily_etl）
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - データ品質チェック（missing / duplicates / spike / date consistency）
  - ニュース収集（RSS -> raw_news、SSRF対策・URL正規化）
  - 監査ログ（audit スキーマ定義 & init_audit_db）

- AI（kabusys.ai）
  - ニュースセンチメント評価（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON mode で呼び出す実装（リトライ・フォールバックあり）

- 研究用（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / factor summary / rank）
  - 汎用統計ユーティリティ（zscore_normalize）

- 汎用ユーティリティ
  - 統計関数（zscore_normalize）
  - データ保存ユーティリティ（DuckDB 向けの冪等保存）

---

## セットアップ手順

前提
- Python 3.10 以上（typing | union 表記使用のため）
- DuckDB、OpenAI SDK 等が必要

1. リポジトリをクローン（あるいはパッケージを取得）
   - プロジェクトルートには `.git` または `pyproject.toml` があることが望ましい（.env の自動読み込みに利用）。

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 必要最低限の例:
     - pip install duckdb openai defusedxml
   - 開発用や packaging がある場合:
     - pip install -e .   （pyproject.toml がある場合にローカルパッケージとしてインストール）

   （実際の要件ファイルはプロジェクトに合わせて準備してください）

4. 環境変数の設定
   - 必須（使用する機能により必要な変数が異なります）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（執行関連）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — 通知（オプション）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - オプショナル:
     - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（1 をセット）

   - .env 自動読み込みのルール:
     - プロジェクトルートが特定できる場合、読み込み順は:
       1. OS 環境変数（既存）
       2. .env（override=False: 未設定キーのみセット）
       3. .env.local（override=True: .env を上書き。ただし OS 環境変数は保護）
     - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。

5. データベースや監査スキーマの初期化（例）
   - 監査ログ用 DuckDB を作成・初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - メインのデータ DuckDB は `DUCKDB_PATH` に保存します。接続は duckdb.connect(path) で作成してください。

---

## 使い方（基本例）

- 日次 ETL を実行する（J-Quants から株価・財務・カレンダーを取得して検査まで行う）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを算出（OpenAI API が必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"スコア取得銘柄数: {count}")
  ```

- 市場レジーム判定（1321 MA200 とマクロニュースを合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- RSS フィードを取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  src_name, url = "yahoo_finance", DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(url, source=src_name)
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- 監査テーブルをアプリ内で初期化する
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- テスト時の差し替え
  - AI 呼び出しは内部で `_call_openai_api` を使っているので、unittest.mock.patch で差し替えてテストできます（examples に従う）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須：ETL）
- KABU_API_PASSWORD: kabu ステーション API パスワード（執行機能）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効にする（1）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 & 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETLResult 再エクスポート
    - calendar_management.py — マーケットカレンダー管理
    - news_collector.py — RSS 取得・前処理・保存ロジック
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — momentum/value/volatility
    - feature_exploration.py — forward returns / IC / factor summary / rank

---

## 設計上の注意点・運用上のヒント

- Look-ahead bias 防止
  - 多くの関数は内部で datetime.today() / date.today() を直接参照しないよう設計されています。テストや運用では明示的に target_date を渡してください。

- 冪等性
  - J-Quants からの保存関数は ON CONFLICT DO UPDATE を使用して冪等性を持たせています（save_* 系）。

- OpenAI 呼び出し
  - レスポンスは JSON mode（厳密な JSON）を期待していますが、パース失敗時は安全側にフォールバックしてスコアを 0.0 にするなどフェイルセーフ設計です。
  - テスト時は内部の _call_openai_api をモックしてください。

- DB バージョン互換性
  - DuckDB の executemany の扱いやリストバインドの挙動に注意した実装（空リストの扱い回避など）を行っています。

---

## 貢献 / 開発

- コードはモジュール単位でテストしやすいように設計されています（依存注入や内部関数差し替えポイントあり）。
- 新しい機能追加や修正を行う際は、Look-ahead bias とデータの冪等性に注意してください。
- .env の自動読み込みは便利ですがテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して副作用を抑えられます。

---

README に記載の内容は現状コードベースの実装に基づいた概要です。実行環境や運用ポリシーに合わせて .env、DB パス、API キー管理を適切に行ってください。必要であれば、サンプルスクリプトや CI/CD 用の実行手順を別途追記できます。