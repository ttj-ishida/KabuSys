# KabuSys — 日本株自動売買システム

軽量な日本株向け自動売買基盤のコアライブラリです。データ取得（J-Quants）、ETL（差分更新・バックフィル）、DuckDB スキーマ定義、品質チェック、監査ログ（トレーサビリティ）といったデータプラットフォーム／実行基盤の主要機能を提供します。

主な設計方針：
- API レート制限・リトライ・トークン自動リフレッシュを備えた堅牢なデータ取得
- DuckDB を用いた3層データ設計（Raw / Processed / Feature）および実行・監査テーブル
- ETL は差分更新・バックフィルを行い冪等性を重視
- 品質チェックで欠損・スパイク・重複・日付不整合を検出し監査情報を記録

---

## 機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み (KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可)
  - 必須環境変数のチェックとアクセス用プロパティ（settings）
- J-Quants API クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レート制限（120 req/min）を守る固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回。408/429/5xx を対象）
  - 401 発生時にリフレッシュトークンで自動リフレッシュして再試行
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution のテーブル定義
  - インデックス、外部キー、チェック制約の定義
  - init_schema() で初期化・接続取得
- ETL パイプライン（data/pipeline.py）
  - run_daily_etl() による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得、バックフィル、品質チェック（quality モジュール連携）
  - ETLResult による詳細結果の返却（取得件数、保存件数、品質問題、エラー等）
- 品質チェック（data/quality.py）
  - 欠損（OHLC 欄）、スパイク（前日比）、重複、日付不整合（未来日・非営業日）を検出
  - QualityIssue のリストとして問題を返す（severity: error|warning）
- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions テーブルでトレーサビリティを保証
  - 発注の冪等キー（order_request_id）やタイムスタンプ（UTC）を強制

---

## セットアップ手順

前提
- Python 3.9+（型ヒントの | 演算子、typing の仕様に依存）
- DuckDB を利用するので duckdb パッケージが必要

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール
   - このリポジトリに requirements.txt がある場合はそれを使ってください。
   - 最低限 duckdb が必要です。
   ```
   pip install duckdb
   ```
   - その他 HTTP クライアント等（標準ライブラリのみで実装されているため追加不要な場合あり）。

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` として設定を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると自動ロード無効）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベースの初期化（DuckDB）
   Python REPL またはスクリプト上で：
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返します
   # またはメモリ DB
   # conn = init_schema(":memory:")
   ```

---

## 使い方（簡単な例）

- settings による環境変数アクセス
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)  # 必須
  print(settings.kabu_api_base_url)      # 省略時はローカルの kabu API
  ```

- J-Quants からデータ取得（クライアント関数直接呼び出し）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.config import settings

  # id_token を明示的に渡すか、モジュールキャッシュを利用（自動リフレッシュ対応）
  id_token = jq.get_id_token()  # POST /token/auth_refresh を呼ぶ
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,3,31))
  ```

- ETL の実行（日次）
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # 初回は init_schema、以降は get_connection でも可
  result = run_daily_etl(conn)  # target_date を指定しないと今日が対象
  print(result.to_dict())
  if result.has_errors or result.has_quality_errors:
      # アラートや手動対応
      pass
  ```

- 監査ログ初期化（audit テーブルの追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  # 既存 conn に監査テーブルを追加
  init_audit_schema(conn)
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

---

## 環境変数の自動読み込みについて

- kabusys.config モジュールはパッケージロード時にプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local (override=True) > .env
  - OS 環境変数は保護され上書きされません。
- 自動読み込みを無効化したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- .env のパースは shell ライクな形式をサポート（export プレフィックス、クォート、行末コメントの一部対応）。

---

## ディレクトリ構成

このリポジトリの主要ファイルと想定構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定・自動 .env ロード・settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・リトライ・保存）
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - schema.py              — DuckDB スキーマ定義・初期化
    - audit.py               — 監査ログ（トレーサビリティ）定義・初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py            — 発注実行・ブローカー連携の拡張ポイント
  - monitoring/
    - __init__.py            — 監視・メトリクス収集（拡張ポイント）

補足:
- DuckDB スキーマは data/schema.py に網羅されています（Raw / Processed / Feature / Execution の各テーブルとインデックス）。
- audit.py は監査用テーブル群を追加するためのユーティリティを提供します。

---

## 運用上の注意点

- API レート制限: J-Quants の制限（120 req/min）を厳守するため、jquants_client は内部でスロットリングを行っています。大量の並列リクエストは避けてください。
- トークン管理: get_id_token はリフレッシュトークンを用いて ID トークンを取得します。401 応答時に自動リフレッシュする仕組みがありますが、リフレッシュトークン自体の管理は慎重に行ってください。
- DuckDB ファイル（settings.duckdb_path）はバックアップ対象として扱ってください。監査ログは削除しない（前提）で設計されています。
- ETL は品質チェックでエラーを検出しても可能な限り処理を継続し、呼び出し元が結果（ETLResult）に基づいて対応を決定します。

---

必要であれば次の内容も作成できます：
- .env.example のテンプレート
- CI/Cron 用の ETL 実行スクリプトサンプル
- 戦略・発注処理のサンプルワークフロー

ご希望があれば教えてください。