# KabuSys

日本株向けの自動売買 / データ基盤ツール群。J-Quants や RSS 等から市場データ・ニュースを収集し、DuckDB に蓄積、ETL・品質チェック、カレンダー管理、監査ログなど自動売買システムに必要な基盤機能を提供します。

## 主な特徴（機能一覧）
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応、指数バックオフを伴うリトライ、401 の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録、DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（RSS）
  - RSS フィード取得、前処理（URL除去・空白正規化）、URL 正規化（UTM 等除去）→ SHA-256 による記事 ID 生成
  - SSRF 対策、defusedxml による XML セキュリティ、gzip 制限、受信サイズ制限
  - DuckDB へ冪等保存（INSERT ... RETURNING）と銘柄コード紐付け
- ETL パイプライン
  - 差分更新（最終取得日から backfill）、市場カレンダー先読み、品質チェック統合
  - 日次 ETL エントリポイント（run_daily_etl）
- マーケットカレンダー管理
  - 営業日判定・前後営業日取得・範囲内営業日列挙、夜間バッチでカレンダー更新
- データ品質チェック
  - 欠損、主キー重複、スパイク（前日比）・将来日付・非営業日データ検出
  - QualityIssue 型で問題を集約（重大度: error / warning）
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 までのトレースを可能にする監査テーブル群（冪等キー、UTC タイムスタンプ）

## 要求環境・依存パッケージ
必須:
- Python 3.9+
- duckdb
- defusedxml

（プロジェクトで使用している他ライブラリはコード参照。setup / requirements ファイルがあればそちらを利用してください）

## セットアップ手順（開発環境向けの一例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject があればそちらを利用）

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（*.env の読み込みは、.git または pyproject.toml を基準にプロジェクトルートを検出します）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
   - KABUSYS_ENV: development / paper_trading / live（省略時 development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（省略時 INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: (値が存在すると自動 .env 読込を無効化)
   - オプション:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   注意: settings オブジェクト（kabusys.config.settings）はこれら環境変数を参照します。未設定の必須キーにアクセスすると ValueError が投げられます。

## 使い方（コード例）
以下は代表的な使用例です。Python スクリプトや REPL、バッチジョブから利用できます。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日
  print(result.to_dict())
  ```

- ニュース収集ジョブ（既知銘柄セットを渡して銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

- J-Quants から株価を直接取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  # id_token を明示的に渡すこともできる（省略時は settings の refresh token を使用）
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- 監査ログ（audit）テーブル初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

## 主要モジュール（概要）
- kabusys.config
  - 環境変数の自動読み込み（.env / .env.local、プロジェクトルート基準）
  - settings オブジェクトでアプリ設定を参照可能
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、fetch_* / save_* 関数群
  - レート制御、リトライ、トークン管理、DuckDB への冪等保存
- kabusys.data.news_collector
  - RSS 取得、前処理、記事ID生成、DuckDB 保存、銘柄抽出
- kabusys.data.schema
  - DuckDB のスキーマ定義と init_schema(), get_connection()
- kabusys.data.pipeline
  - 差分取得ロジック（backfill）、run_daily_etl（統合 ETL）
- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job（夜間バッチ）
- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
- kabusys.data.audit
  - 監査ログ用テーブル初期化（signal/events/order_requests/executions 等）
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - パッケージ用の空の名前空間（戦略実装、発注実行、監視ロジック等を想定）

## 環境変数自動読み込みの挙動
- ロード優先度: OS 環境変数 > .env.local > .env
- プロジェクトルートはこのモジュールの __file__ を基点に上位ディレクトリを探索し、.git または pyproject.toml が見つかったディレクトリをルートと見なします
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（値は任意）

## データベースについて
- デフォルトの DuckDB ファイルは data/kabusys.duckdb（settings.duckdb_path）です
- init_schema(db_path) でスキーマを冪等に作成します。":memory:" を渡すとインメモリ DB を使用
- save_* 系は重複を避けるため ON CONFLICT（UPSERT）を使用しています

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - pipeline.py
  - calendar_management.py
  - schema.py
  - audit.py
  - quality.py
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（README はプロジェクトの実際のルート構成に合わせて調整してください）

## 運用上の注意・設計上の要点
- J-Quants API のレート制限（120 req/min）を守るためスロットリングを行っています。大規模なページネーション取得時は時間がかかります。
- トークンが 401 で失効した場合、1 回自動でリフレッシュして再試行します。get_id_token は refresh token を用いて ID トークンを取得します。
- ニュース収集では SSRF・XML 脆弱性・gzip bomb への対策が組み込まれています。外部フィードの取り込みは慎重に行ってください。
- DuckDB の INSERT ... RETURNING を利用して実際に挿入された行数や ID を正確に取得できます。
- 品質チェックは Fail-Fast ではなく、問題を網羅的に収集して報告する設計です。呼び出し側で重大度に応じた対応を実装してください。
- すべてのタイムスタンプは原則 UTC で扱うように設計されています（監査ログ等で特に明示）。

---

必要であれば、README に「運用手順（cron/airflow での日次ジョブ定義）」「例 .env.example」「CI 用のセットアップ手順」などを追加で作成します。どの情報を補足したいか教えてください。