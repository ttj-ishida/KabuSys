# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
J-Quants など外部データソースからのデータ取得、DuckDB による永続化、ETL パイプライン、ニュース収集、マーケットカレンダー管理、監査ログ等の機能を提供します。

---

## 概要

KabuSys は以下を目的としたモジュールセットです。

- J-Quants API から株価（日足）、財務データ、マーケットカレンダーを取得して DuckDB に保存する。
- RSS フィードからニュース記事を収集し、前処理・銘柄抽出を行って DuckDB に保存する。
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を実行する。
- マーケットカレンダー（JPX）を管理し、営業日判定 / 前後営業日・期間の営業日列挙を提供する。
- 監査ログ（シグナル→発注→約定）用のテーブルを提供し、トレーサビリティを確保する。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行する。

設計上の特徴：

- J-Quants API に対するレート制御（120 req/min）とリトライ（指数バックオフ）を内蔵
- トークン自動リフレッシュ（401 時に一度リトライ）
- DuckDB への保存は冪等（ON CONFLICT）を利用
- ニュース収集は SSRF / XML Bomb 対策、受信サイズ制限などセキュリティ対策あり
- ETL は差分更新・バックフィルを行い、品質チェックは Fail-Fast せず問題を収集する

---

## 主な機能一覧

- data/
  - jquants_client
    - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()
    - レートリミッタ、リトライ、自動トークン更新、fetched_at の記録
  - news_collector
    - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
    - URL 正規化・トラッキングパラメータ除去、記事IDはSHA-256（先頭32文字）
    - SSRF / Gzip / XML パース対策、チャンク INSERT とトランザクション
  - schema
    - init_schema(), get_connection()
    - DuckDB のスキーマ（Raw / Processed / Feature / Execution）作成
  - pipeline
    - run_prices_etl(), run_financials_etl(), run_calendar_etl(), run_daily_etl()
    - 差分更新・バックフィル・品質チェック統合
  - calendar_management
    - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
    - market_calendar がない場合は曜日ベースのフォールバック
  - audit
    - init_audit_schema(), init_audit_db()
    - シグナル／発注要求／約定の監査テーブル群（監査用DDL）
  - quality
    - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()
    - QualityIssue を返却し詳細を収集
- config.py
  - 環境変数読み込み（.env / .env.local 自動ロード: プロジェクトルート検出）
  - Settings クラスで必要な設定値を提供（必須キーは取得時に例外）

---

## セットアップ手順

1. 必要な Python バージョンを用意する（3.9+ を想定）
2. 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   プロジェクトに pyproject.toml / requirements.txt があればそれを使用してください。

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - `.env.local` が存在する場合は `.env` の上書き（OS 環境変数は保護）を行います。

   必須（例）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   ```
   任意 / デフォルトあり:
   ```
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルト値
   DUCKDB_PATH=data/kabusys.duckdb                    # デフォルト
   SQLITE_PATH=data/monitoring.db                     # デフォルト
   KABUSYS_ENV=development                            # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - 使い始めにスキーマを作成します（以下は例）。
   ```
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（例）

基本的な Python スニペット。

- DB 初期化（スキーマ作成）
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants トークンは Settings から自動取得）
  ```
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行
  ```
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は銘柄コードセット（例: {"7203", "6758"}）
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  print(stats)
  ```

- カレンダー更新ジョブ（夜間バッチで実行）
  ```
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 監査スキーマの初期化（audit 用テーブルを追加）
  ```
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 品質チェックを手動実行
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- J-Quants API を直接呼ぶ（トークン取得 / データ取得）
  ```
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意点：
- Settings 経由で必須環境変数を取得するため、未設定の場合は ValueError が発生します。
- run_daily_etl 等は内部で例外を捕捉して処理を継続する設計ですが、errors/quality_issues を返すので結果を確認してください。

---

## 環境変数（主なキー）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。

.env の自動ロード順序（優先度低→高）:
1. .env
2. .env.local（存在する場合は上書き。ただし OS 環境変数は保護される）

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py          # RSS からのニュース収集・前処理・DB 保存
    - schema.py                  # DuckDB スキーマ定義 & init_schema()
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     # マーケットカレンダー管理
    - audit.py                   # 監査ログ用テーブル（signal/order/execution）
    - quality.py                 # データ品質チェック
  - strategy/
    - __init__.py                # 戦略関連モジュール群（拡張ポイント）
  - execution/
    - __init__.py                # 発注・ブローカー連携モジュール（拡張ポイント）
  - monitoring/
    - __init__.py                # 監視・メトリクス関連（拡張ポイント）

--- 

## 実運用・運用上の注意

- J-Quants のレート制限（120 req/min）を超えないように設計されていますが、外部で並列実行する場合は注意してください。
- run_daily_etl は品質チェックでエラーを検出しても自動停止しない設計です。呼び出し側で result.has_quality_errors / result.has_errors を確認して運用判断してください。
- ニュース収集は外部 RSS を大量に叩く場合、収集頻度と帯域/負荷を考慮してください。SSRF 対策や受信サイズ制限は組み込まれています。
- DuckDB ファイルは単一ファイルでローカル永続化されます。マルチプロセスでの同時書き込みやバックアップ戦略は別途検討してください。
- 監査ログ（audit）テーブル群は削除しない前提（ON DELETE RESTRICT）です。データ保持ポリシーに応じた管理を行ってください。

---

## 開発・拡張ポイント

- strategy/ と execution/ は空の初期モジュールとして用意されています。アルゴリズムやブローカー接続をここに実装してください。
- monitoring/ は監視用ジョブや Prometheus エクスポーター等を実装するためのエントリポイントです。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。
- news_collector._urlopen などはテストのためにモック可能な設計です。

---

不明点や README に追加したいサンプル（CI 設定、詳細な .env.example、requirements）などがあれば教えてください。README をさらに詳しく（コマンド例・運用フロー図・CI ワークフロー等）に拡張できます。