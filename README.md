# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants などの外部データソースから市場データ・財務データ・ニュースを取得して DuckDB に保存し、ファクター計算、特徴量作成、シグナル生成、発注管理までのパイプラインを想定したモジュールを提供します。

主な目的
- データ取得（J-Quants） → DuckDB 保存（Raw / Processed / Feature / Execution 層）
- 研究用ファクター計算・特徴量正規化
- 戦略シグナル生成（BUY / SELL 判定）
- ニュース収集と銘柄紐付け
- ETLパイプライン／カレンダー管理／監査ログ設計

バージョン: 0.1.0（パッケージ定義: src/kabusys/__init__.py）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API から日足 / 財務 / マーケットカレンダーを取得（ページネーション対応）
  - レート制御、リトライ、トークン自動更新、取得時刻（fetched_at）記録
  - DuckDB への冪等保存（ON CONFLICT / upsert）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日に基づく差分取得）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（別モジュール quality と連携）

- スキーマ管理（kabusys.data.schema）
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - 接続ユーティリティ

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策、gzip 制限、XML パースの安全化）
  - 記事正規化・記事ID生成（URL 正規化 → SHA256）
  - raw_news, news_symbols への冪等保存

- 研究・ファクター（kabusys.research）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ（kabusys.data.stats）

- 特徴量作成（kabusys.strategy.feature_engineering）
  - research モジュールの生ファクターをマージ・ユニバースフィルタ・正規化して features テーブルへ UPSERT

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成
  - Bear レジーム検出・ストップロスなどのエグジット判定
  - signals テーブルへ冪等保存

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日、期間内営業日リスト取得、カレンダー夜間更新ジョブ

- 監査ログ設計（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティを確保するテーブル定義（監査ログ）

---

## 前提 / 要件

- Python 3.10+
  - 型注釈に `|`（ユニオン）構文を使用しているため Python 3.10 以上を想定しています。
- 主要依存ライブラリ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリで実装された機能を多く使用しています（urllib, json, logging 等）。

実際の運用では、発注連携（kabuステーション等）や Slack 通知などの追加パッケージが必要になる場合があります。

---

## 環境変数（主なもの）

このプロジェクトは環境変数 / .env を通じて設定を取得します（kabusys.config.Settings）。

必須（実運用で必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API（または証券会社API）用パスワード
- SLACK_BOT_TOKEN — Slack Bot Token（通知用）
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite （監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" にすると .env 自動ロードを無効化

注意: .env.local は .env の上書き（優先）で読み込まれます。プロジェクトルートは .git または pyproject.toml を起点に自動検出されます。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   実際のプロジェクトでは pyproject.toml / requirements.txt に従ってインストールしてください。

4. 環境変数を用意
   - プロジェクトルートに `.env` を作成し、必須値を設定します（例）:
     ```
     JQUANTS_REFRESH_TOKEN=*****
     KABU_API_PASSWORD=*****
     SLACK_BOT_TOKEN=*****
     SLACK_CHANNEL_ID=*****
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - テストや CI で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマの初期化
   - Python REPL またはスクリプトから init_schema を呼び出します:
     ```python
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # :memory: も可
     conn.close()
     ```

---

## 使い方（代表的な呼び出し例）

以下はライブラリ関数を直接呼び出す例です。実運用では CLI やジョブスケジューラ（cron / Airflow 等）から呼び出してください。

- 日次 ETL を実行（市場カレンダー・株価・財務を取得して保存）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量を作成（features テーブル構築）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date.today())
  print("features upserted:", n)
  conn.close()
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print("signals generated:", count)
  conn.close()
  ```

- ニュース収集（RSS から raw_news を保存）
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes: 既知の銘柄コードセット（抽出に使用）
  known_codes = {"7203", "6758", "9433", ...}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  conn.close()
  ```

---

## 推奨運用上の注意

- DuckDB ファイルはバックアップやスナップショットを運用ポリシーに合わせて保存してください。
- J-Quants API のレート制限を守るため、fetch 関数は内部でスロットリングとリトライを行います。大規模な backfill の場合は API 制限に注意してください。
- features / signals の作成は必ず営業日（market_calendar）に合わせて行ってください。pipeline.run_daily_etl は営業日調整を行います。
- ニュース収集は外部URLを扱うため SSRF 対策やレスポンスサイズ制限を実装していますが、収集対象の追加は注意して行ってください。
- 実口座運用（live）時は KABUSYS_ENV を "live" に設定し、ログ／モニタリング／リスク管理を厳密に行ってください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 内の主要モジュール（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                            — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                   — J-Quants API クライアント（取得・保存）
    - news_collector.py                   — RSS ニュース収集・保存
    - pipeline.py                         — ETL パイプライン（run_daily_etl 等）
    - schema.py                           — DuckDB スキーマ定義・初期化
    - stats.py                            — 統計ユーティリティ（zscore_normalize 等）
    - features.py                         — data.stats エクスポートラッパ
    - calendar_management.py              — カレンダー管理 / update job
    - audit.py                            — 監査ログ用 DDL（signal / order / execution）
    - (その他 monitoring / quality 等が想定)
  - research/
    - __init__.py
    - factor_research.py                  — momentum/volatility/value の計算
    - feature_exploration.py              — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py              — features テーブル構築
    - signal_generator.py                 — signals 生成ロジック
  - execution/
    - __init__.py                         — 発注層用エントリ（実装はここから拡張）
  - monitoring/ (想定: 監視・Slack 通知等)

（注）上記はコードベースの抜粋です。フルツリーはリポジトリの src/kabusys 以下を参照してください。

---

## 追加情報 / 開発メモ

- .env の自動ロードはプロジェクトルートを .git または pyproject.toml で特定して行います。パッケージ配布後も CWD に依存せず動作する設計です。
- jquants_client は取得時刻（UTC）を記録し、look-ahead bias の観点からいつデータが利用可能だったかをトレースできるようにしています。
- DB の DDL は外部キーや制約を設けていますが、DuckDB バージョンの制約（ON DELETE CASCADE 未サポート 等）に合わせた注意書きを含みます。
- ユニットテストや CI、運用向けの CLI/ジョブラッパーは別途用意すると運用性が向上します。

---

必要に応じて README の補足（環境ごとの設定例、実行スクリプト、CI / cron 設定例、監視アラート設計など）を作成します。どの部分を優先して追記しましょうか？