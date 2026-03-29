# KabuSys

日本株のデータプラットフォームと自動売買／リサーチ補助ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI でのセンチメント評価）、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）を主な機能として提供します。

---

## 主要機能（抜粋）

- データ取得 / ETL
  - J-Quants API からの株価（日次 OHLCV）・財務データ・JPX カレンダーの差分取得と DuckDB への冪等保存
  - 日次 ETL パイプライン（run_daily_etl）
- ニュース収集・NLP
  - RSS フィードからのニュース収集（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロ記事を利用した市場レジーム判定（score_regime）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC 計算、統計サマリー（calc_forward_returns, calc_ic, factor_summary）
  - Zスコア正規化ユーティリティ（zscore_normalize）
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック（quality モジュール）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env 自動読み込み（プロジェクトルートを探索）と Settings API（kabusys.config.settings）

---

## 要件（推奨）

- Python >= 3.10（PEP 604 の型記法や型ヒントに依存）
- 以下パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- その他（利用機能に依存）
  - urllib / 標準ライブラリのみで動作する部分が多いですが、Slack 等の外部連携を行う場合は該当 SDK を追加してください。

（実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install することを推奨します）

---

## セットアップ手順

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際は pyproject.toml / requirements.txt があればそれを使用してください。

3. .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と `.env.local`（ローカル上書き用）を置くと自動で読み込まれます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_station_password
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化（監査ログ等）
   - 監査用 DuckDB データベースを初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存接続に監査スキーマを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```

---

## 使い方（代表例）

- DuckDB 接続を作成して ETL を実行（日次 ETL）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント (score_news)
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数に設定済みか api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定 (score_regime)
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(records), "件のファクターレコード取得")
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI 呼び出しや J-Quants 呼び出しはネットワーク I/O を伴うため、テスト時には該当関数をモック（unittest.mock.patch）することが設計上想定されています。
- 各関数は「ルックアヘッドバイアス」を避ける設計（target_date 未満のデータのみ参照する等）になっています。バックテスト用途でも安全に扱えるよう留意してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（注文実行等で使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（モニタリング等）
- DUCKDB_PATH: デフォルト DuckDB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: 環境 (development / paper_trading / live)
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 管理（.env 自動ロードロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py        : ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py : マクロ+MA200 による市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py        : ETL パイプライン（run_daily_etl など）
    - etl.py             : ETLResult 再エクスポート
    - jquants_client.py  : J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py  : RSS 収集（SSRF 対策・前処理・保存）
    - calendar_management.py : マーケットカレンダー管理（is_trading_day 等）
    - quality.py         : データ品質チェック
    - stats.py           : 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py           : 監査ログ（監査テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py     : Momentum / Volatility / Value の計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリー 等
  - others: strategy / execution / monitoring パッケージが __all__ で参照される設計（実装はコードベースに依存）

各モジュールにはドキュメンテーション文字列と設計方針が付与されており、外部 API 呼び出しは再試行・バックオフ・フォールバックの考慮がなされています。

---

## テスト・デバッグのヒント

- OpenAI / J-Quants 等の外部 API 呼び出しはユニットテスト時にモックして差し替えることが想定されています（各モジュール内で _call_openai_api 等に分離しているため差し替えが容易です）。
- 環境変数の自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで .env の干渉を避けられます）。
- DuckDB をインメモリで使いたい場合は接続文字列に `":memory:"` を指定できます（監査 DB 初期化等でサポート）。

---

必要に応じて README に具体的なコマンド（CI 用、データ初期ロード手順、SQL スキーマの初期化手順など）を追加できます。追加したい項目があれば教えてください。