# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータ基盤・ETL・監査ログを備えた自動売買システムのコアライブラリです。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に保存し、品質チェックや監査ログ（シグナル→発注→約定トレース）を行うためのモジュール群を提供します。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPXマーケットカレンダーの取得
  - レート制限（120 req/min）に従ったスロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 発生時の自動トークンリフレッシュ
  - 取得時刻（UTC）を記録して Look-ahead Bias を防止

- データ永続化（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマ
  - ON CONFLICT DO UPDATE による冪等な保存関数
  - スキーマ初期化ユーティリティ（init_schema, init_audit_schema）

- ETL パイプライン
  - 差分更新（最終取得日を基に未取得分のみ取得）
  - バックフィル（後出し修正吸収のため過去数日再取得）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- データ品質チェック
  - 欠損（OHLC）検出（エラー）
  - 主キー重複検出（エラー）
  - スパイク（前日比）検出（警告）
  - 将来日付／非営業日データ検出（エラー/警告）

- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求（冪等キー） → 約定 を UUID 連鎖で追跡可能
  - 発注・約定のステータス管理テーブル
  - UTC タイムスタンプ、削除しない設計（監査証跡保持）

- 環境設定管理
  - .env / .env.local からの自動読み込み（プロジェクトルート判定）
  - 必須環境変数取得とバリデーション
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL 管理

---

## セットアップ手順

前提: Python 3.10 以上（PEP 604 の union 型 `X | Y` を利用）。

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境の作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   ※このリポジトリに requirements.txt がある場合はそれを利用してください。最低限必要なのは duckdb（Python モジュール）です。
   ```bash
   pip install duckdb
   # またはプロジェクト配布形態に応じて
   # pip install -e .
   ```

4. 環境変数の設定  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として下記のような値を用意します。

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL はデフォルトで http://localhost:18080/kabusapi
   #KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動ロードを無効にする場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（主要な API と実行例）

以下はライブラリを利用した基本的な操作例です。実運用ではログ設定やエラーハンドリングを適切に追加してください。

- 設定の参照
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print(settings.env, settings.log_level)
  ```

- DuckDB スキーマの初期化
  ```python
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")  # ファイルがなければ作成
  # またはインメモリ
  # conn = schema.init_schema(":memory:")
  ```

- 監査ログテーブルの初期化（既存接続に追加）
  ```python
  from kabusys.data import audit

  audit.init_audit_schema(conn)
  ```

- J-Quants API からデータ取得（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
  ```

- ETL（デイリー）実行（推奨）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を省略すると today を対象に実行
  print(result.to_dict())
  ```

- 品質チェックを単独で実行
  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=None)  # target_date を指定して絞ることも可能
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意:
- J-Quants のレート制限や認証フローに従うため、jquants_client は内部でスロットリング／リトライやトークンキャッシュを行います。
- ETL は各ステップで例外をキャッチして処理を継続する設計です。返却される ETLResult の errors や quality_issues を確認してください。

---

## 環境変数（主要項目）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API のパスワード
- KABU_API_BASE_URL (任意): kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): 実行環境（development, paper_trading, live）
- LOG_LEVEL (任意): ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意): 自動 .env 読み込みを無効化（値を設定すると無効）

プロジェクトはプロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` を読み込みます。.env.local は .env の上書きとして扱われます（OS の環境変数は常に優先）。

---

## ディレクトリ構成

以下は主要なファイル/モジュールの構成です（src/kabusys をルートとする）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント、取得・保存関数
      - schema.py               # DuckDB スキーマ定義と初期化
      - pipeline.py             # ETL パイプライン（差分更新・品質チェック）
      - audit.py                # 監査ログ（シグナル→発注→約定のトレース）
      - quality.py              # データ品質チェック
    - strategy/
      - __init__.py             # 戦略関連（空のプレースホルダ）
    - execution/
      - __init__.py             # 発注・実行関連（空のプレースホルダ）
    - monitoring/
      - __init__.py             # 監視関連（空のプレースホルダ）

スキーマは Raw / Processed / Feature / Execution レイヤーでテーブルを定義し、インデックスも含みます。監査テーブルは audit.py にて別途初期化できます（init_audit_schema / init_audit_db）。

---

## 運用上の注意

- J-Quants の API レート制限を守ってください。モジュールは 120 req/min に合わせた実装になっていますが、追加の外部呼び出しを行う場合は注意が必要です。
- DuckDB のファイルは適切にバックアップしてください（監査ログは削除しない前提で設計されています）。
- 本ライブラリはデータ取得・保存・品質チェック・監査ログに重点を置いており、実際のブローカーへの注文送信（kabu ステーション連携）やポートフォリオ管理ロジックは execution/ や strategy/ に実装を追加して利用します。
- 環境（KABUSYS_ENV）が "live" の場合は本番データ操作になるため十分に検証してから切り替えてください。

---

必要であれば、README にサンプル .env.example、CI 設定、ローカルでの簡易デバッグ手順、あるいは発注ワークフローのサンプルコードの追加を行います。どの情報をより詳しく載せたいか指示してください。