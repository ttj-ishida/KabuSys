# KabuSys

日本株向け自動売買（データ収集・ETL・監査）ライブラリ / フレームワーク

概要:
- KabuSys は J-Quants や各種 RSS を利用して日本株のデータを取得・保存し、ETL・品質チェック・監査ログ・ニュース収集などを行うための内部ライブラリ群です。
- DuckDB を永続ストレージに用い、冪等な保存やトレーサビリティを重視した設計になっています。

主な設計方針（抜粋）:
- API のレート制限・リトライ（指数バックオフ）に対応
- データ取得時の fetched_at による Look-ahead Bias 対策
- DuckDB へは ON CONFLICT/RETURNING を活用して冪等保存
- RSS 取得は SSRF / XML Bomb / 不正スキーム対策などセキュアに実装
- 品質チェックは Fail-Fast ではなく検出結果を収集して呼び出し元が判断できるように設計

---

機能一覧
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
- データ取得（J-Quants）
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レート制御、再試行、トークン自動リフレッシュ
- データ保存（DuckDB）
  - raw / processed / feature / execution 層のスキーマ定義・初期化
  - 冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）
- ETL パイプライン
  - 差分更新（バックフィル対応）、品質チェック呼び出し
  - 日次 ETL の統合エントリポイント
- ニュース収集
  - RSS からの記事抽出、前処理、記事ID（正規化URL の SHA-256 部分）生成、raw_news 保存
  - 銘柄コード抽出と news_symbols の紐付け
- カレンダー管理
  - 営業日判定 / 前後営業日検索 / 夜間カレンダー更新ジョブ
- 監査ログ（Audit）
  - signal → order_request → execution の階層的トレース用テーブル群と初期化機能
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合など

---

セットアップ手順（開発用）
1. Python 環境を用意
   - Python 3.9+ を推奨
   - 仮想環境を作成・有効化:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 主要な依存:
     - duckdb
     - defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクト配布時は requirements.txt / pyproject.toml を参照してください）

3. 環境変数を用意
   - プロジェクトルートに .git または pyproject.toml がある場合、.env と .env.local が自動ロードされます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須環境変数（少なくともこれらを設定してください）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   サンプル .env:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb

---

使い方（簡単な例）

- スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

  - ":memory:" を指定するとインメモリ DuckDB を使えます。

- 日次 ETL を実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集（RSS）を実行
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（例）
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)

- カレンダー夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- 監査ログ用スキーマ初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 設定値の取得
  from kabusys.config import settings
  print(settings.env, settings.jquants_refresh_token)

注意点:
- J-Quants API クライアントは 120 req/min のレート制限を守るため内部でスロットリングを行います。
- リトライは最大 3 回、408/429/5xx はリトライ対象、401 受信時は自動でトークンをリフレッシュして1回だけ再試行します。
- News Collector は外部入力（RSS）を扱うため、SSRF / 大容量応答 / XML 攻撃等の防御策を多数実装しています。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数と設定管理（.env 自動ロード、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS 取得・前処理・DB保存・銘柄抽出
    - schema.py — DuckDB のスキーマ定義と init_schema()
    - pipeline.py — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py — 市場カレンダーの管理・営業日判定
    - audit.py — 監査ログテーブル定義と初期化ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py (戦略モジュールのプレースホルダ)
  - execution/
    - __init__.py (発注・実行管理のプレースホルダ)
  - monitoring/
    - __init__.py (監視用プレースホルダ)

各モジュールの役割（要約）:
- config.py: 環境変数の読み込みと settings オブジェクト。自動ロードはプロジェクトルートに基づき .env/.env.local を読み込みます。
- data/jquants_client.py: J-Quants との通信、ページネーション、取得データの DuckDB への保存（save_*）を提供。
- data/news_collector.py: RSS フィード安全取得、記事ID生成、raw_news / news_symbols への保存。
- data/schema.py: Raw / Processed / Feature / Execution 層などテーブル群の DDL を定義し init_schema() で作成。
- data/pipeline.py: 差分 ETL （run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）と品質チェックの統合。
- data/calendar_management.py: 営業日判定や前後営業日検索、夜間カレンダー更新ジョブ実装。
- data/audit.py: 監査用テーブル（signal_events / order_requests / executions）と初期化ユーティリティ。
- data/quality.py: 各種データ品質チェックと QualityIssue の定義。

---

開発・運用上の注意
- DuckDB はシングルファイル DB であり、複数プロセスで同時に書き込むユースケースでは排他・運用ポリシーを検討してください。
- ETL の差分ロジックはバックフィル（既定: 3 日）に依存して API 側の後出し修正を吸収します。運用要件に合わせて backfill_days を調整してください。
- 環境設定（特に API トークン・パスワード）は安全に管理してください（CI/CD シークレット管理、Vault 等）。
- 本ライブラリは内部ロジックの断片を含むため、実運用ではエラーハンドリングや通知（Slack）などの周辺機能を組み合わせて使用してください。

---

貢献・拡張
- 戦略（strategy）モジュールや発注実行（execution）、監視（monitoring）などはプレースホルダが用意されています。ここへ具体的な戦略・ブローカー連携実装を追加してください。
- テストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動環境読み込みを無効にすると良いです。

---

連絡先 / ライセンス
- 本 README はコードベースの構成と利用方法をまとめたものです。ライセンス情報や詳細な使用条件はプロジェクトのルートにある LICENSE / CONTRIBUTING を参照してください（無ければプロジェクト管理者に確認してください）。

以上。必要であれば README に含める CLI コマンド例や追加の使用例（Slack 通知、スケジューリング例、CI 設定など）を追記します。どの項目を詳しくしますか？