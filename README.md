# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのデータ基盤・ETL・監査機能群を提供する Python パッケージです。J-Quants API などから市場データ・財務データ・ニュースを取得して DuckDB に格納し、品質チェックやカレンダー管理、監査ログの初期化などを行うためのモジュールを含みます。

## プロジェクト概要
- 目的: 日本株自動売買システムのデータ収集・整形・品質管理・監査基盤を提供する。
- 主な技術:
  - Python 3.10+
  - DuckDB（ローカル分析DB）
  - J-Quants API 経由のデータ取得
  - RSS からのニュース収集（XML セキュリティ対策済み）
- 設計方針:
  - API のレート制御・リトライ（指数バックオフ・トークン自動更新）
  - データ取得時刻（fetched_at）を保持して Look-ahead Bias を防止
  - 冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を重視
  - SSRF・XML Bomb 等のセキュリティ対策を実装

---

## 機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN 等）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足価格（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レートリミット制御、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_*）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・正規化・前処理
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 ベースの記事ID生成（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP検出、リダイレクト検査）
  - defusedxml を用いた安全な XML パース
  - DuckDB への冪等保存（raw_news / news_symbols）

- データスキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層の DuckDB テーブル定義
  - init_schema() による一括初期化（冪等）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日に基づく差分・バックフィル）
  - 市場カレンダー先読み
  - データ保存・品質チェック（kabusys.data.quality 連携）
  - run_daily_etl() による日次 ETL 統合

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、期間内の営業日取得
  - 夜間バッチ（calendar_update_job）でのカレンダー差分更新

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue オブジェクトで問題を集約（severity: error/warning）

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定までのトレーサビリティ用テーブルを初期化
  - init_audit_schema / init_audit_db を提供（UTC タイムゾーン固定）

- （骨組み）strategy / execution / monitoring パッケージ（拡張用プレースホルダ）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型アノテーションで | 演算子を使用）
- duckdb, defusedxml などが必要

1. リポジトリをクローン
   - 例:
     git clone <repo-url>
     cd <repo>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .\.venv\Scripts\activate    (Windows PowerShell)

3. 必要パッケージをインストール
   - 最低依存（例）:
     pip install duckdb defusedxml
   - pyproject.toml / requirements.txt があればそちらから:
     pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成して設定できます。
   - 自動ロード順序: OS環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN   （J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD       （kabu API パスワード）
     - SLACK_BOT_TOKEN         （Slack ボットトークン）
     - SLACK_CHANNEL_ID        （通知先チャンネルID）
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO
     - DUCKDB_PATH (例: data/kabusys.duckdb) デフォルト値あり
     - SQLITE_PATH (監視用 sqlite path) デフォルト値あり

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 監査テーブルは別途初期化可能:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（基本例）

- DuckDB 接続とスキーマ初期化
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # デフォルトは本日を対象に実行
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- ニュース収集の単独実行
  ```python
  from kabusys.data.news_collector import run_news_collection

  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

- J-Quants の ID トークンを直接取得
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # 環境変数の JQUANTS_REFRESH_TOKEN を使用
  ```

- 品質チェックを個別実行
  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意:
- すべての主要な関数は duckdb.DuckDBPyConnection を受け取ります。接続を共有して使ってください。
- ETL 実行中のログやエラーは logger 経由で出力されます。必要に応じて logging.basicConfig() で設定してください。

---

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu ステーション API パスワード
- SLACK_BOT_TOKEN (必須): Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須): Slack 通知先チャンネルID
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視用パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env ロードを無効化

.env の書式は標準的な KEY=VALUE をサポートし、export プレフィックスやクォート、コメントの扱いは config モジュールの実装に従います。

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内部の主要な構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py          # J-Quants API クライアント（取得・保存）
      - news_collector.py         # RSS 取得・前処理・保存
      - schema.py                 # DuckDB スキーマ定義・初期化
      - pipeline.py               # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py    # 市場カレンダー管理（判定・更新ジョブ）
      - audit.py                  # 監査ログ（signal/order/execution）初期化
      - quality.py                # データ品質チェック
    - strategy/
      - __init__.py               # 戦略モジュール（拡張用）
    - execution/
      - __init__.py               # 発注実行モジュール（拡張用）
    - monitoring/
      - __init__.py               # 監視・メトリクス（拡張用）

---

## 運用上の注意／推奨
- J-Quants API のレート制限（120 req/min）に従ってください。ライブラリ内で制御はありますが、大規模取得時は設計に注意。
- 定期実行（cron / workflow）で:
  - 深夜に calendar_update_job を実行してカレンダーを先読み
  - 朝に run_daily_etl を実行して前日の更新を取り込む
- DuckDB ファイルは定期的にバックアップしてください（ローカルファイル故障に備え）。
- ニュース RSS の HTTP 呼び出しは外部 URL を扱うため、SSRF 等のリスクがある点を考慮してください。news_collector は基本的な対策を実装していますが、組織ポリシーに従ってください。
- 監査ログ（audit）テーブルは削除せず保持する方針で設計されています。

---

## 拡張ポイント
- strategy / execution / monitoring パッケージは本 README の機能で利用する戦略実装や証券会社連携、監視アラート実装などを追加するための拡張ポイントです。
- DuckDB 上での SQL 分析・Pandas 連携・機械学習パイプラインの追加が容易です。

---

ご不明点や追加で記載したいサンプル（cron設定、CI/CD、詳細な環境変数テンプレートなど）があれば教えてください。README をそれに合わせて拡張します。