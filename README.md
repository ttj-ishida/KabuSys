# KabuSys

日本株向け自動売買データ基盤・ETL・監査ライブラリ

このリポジトリは、日本株のデータ取得・保存・品質チェック・監査ログを扱う内部ライブラリ群です。J-Quants API からのデータ取得、DuckDB へのスキーマ定義／初期化、日次 ETL パイプライン、品質チェック、監査ログ用スキーマなどを提供します。

---

## 概要

KabuSys は次の目的で設計されています。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得する
- DuckDB にデータを冪等に保存（ON CONFLICT DO UPDATE）する
- 差分更新（最終取得日ベース）やバックフィルに対応した日次 ETL パイプラインを提供する
- データ品質チェック（欠損、スパイク、重複、日付不整合）を行う
- 発注〜約定までの監査ログテーブルを初期化・管理する

設計上のポイント:

- API レート制限（120 req/min）を固定間隔スロットリングで遵守
- リトライ（指数バックオフ、最大 3 回）・401 の自動リフレッシュ対応
- 取得時刻（fetched_at）を UTC で保存し Look-ahead Bias を低減
- SQL はパラメータバインドを使用し、インジェクション対策

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価、財務、カレンダーの取得）
  - レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への保存用関数（save_daily_quotes 等）
- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema() で全テーブルとインデックスを冪等に作成
- data/audit.py
  - 発注・約定の監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_audit_schema() / init_audit_db() を提供
- data/pipeline.py
  - 日次 ETL パイプライン（run_daily_etl）
  - 差分取得、保存、品質チェック（quality.py）を連携
- data/quality.py
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック
  - run_all_checks() でまとめて実行
- config.py
  - 環境変数管理（.env 自動読み込み機能、Settings クラス）
  - 必須環境変数の検査と便利なプロパティ
- monitoring / strategy / execution
  - 将来的な監視・戦略・発注モジュール用パッケージプレースホルダ

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントで union 型などを使用）
- DuckDB（Python パッケージ）

1. リポジトリをクローンしてインストール（開発モード推奨）
   - git clone ...
   - cd <repo_root>
   - python -m pip install -e .

2. 必要パッケージ（例）
   - duckdb（pip でインストールされる想定: pip install duckdb）
   - （ネットワークは標準ライブラリを使用）

3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID : Slack チャネル ID（必須）

   任意・デフォルトあり:
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視 DB など（デフォルト: data/monitoring.db）

5. .env の例（プロジェクトルートに保存）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプト内での利用例です。

1. DuckDB スキーマの初期化（全テーブル作成）
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   # settings.duckdb_path は .env の DUCKDB_PATH を参照
   conn = init_schema(settings.duckdb_path)
   ```

2. 監査ログテーブルの初期化（既存 conn に追加）
   ```python
   from kabusys.data.audit import init_audit_schema

   init_audit_schema(conn)
   ```

3. J-Quants から株価を取得して DB に保存（個別操作）
   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.config import settings
   import duckdb

   conn = duckdb.connect(settings.duckdb_path)
   token = jq.get_id_token()  # refresh token から id_token を取得
   records = jq.fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,3,31))
   saved = jq.save_daily_quotes(conn, records)
   print(f"saved: {saved}")
   ```

4. 日次 ETL の実行（推奨）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

5. 品質チェックを個別に実行する
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn)
   for i in issues:
       print(i.check_name, i.severity, i.detail)
   ```

ログや例外は標準 logging を通じて出力されます。環境変数 `LOG_LEVEL` で調整できます。

---

## ディレクトリ構成

以下は主要ファイルの構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得・保存）
      - schema.py               # DuckDB スキーマ定義・初期化
      - pipeline.py             # ETL パイプライン（run_daily_etl 等）
      - audit.py                # 監査ログスキーマ（signal/order/execution）
      - quality.py              # データ品質チェック
    - execution/                 # 発注関連モジュール（プレースホルダ）
      - __init__.py
    - strategy/                  # 戦略関連（プレースホルダ）
      - __init__.py
    - monitoring/                # 監視関連（プレースホルダ）
      - __init__.py

README.md 等のプロジェクトルートファイルはリポジトリルートに配置します。

---

## 実装上の注意・トラブルシューティング

- .env の自動読み込みはパッケージ内で .git または pyproject.toml を探索してプロジェクトルートを検出して行います。テストや CI で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）やリトライ／Retry-After を考慮した実装になっていますが、運用時は他プロセスとの呼び出し頻度に注意してください。
- DuckDB のスキーマ初期化は冪等（存在するテーブルはスキップ）です。初回だけ init_schema() を実行してください。
- get_id_token() は内部で refresh token を使って id_token を取得します。401 エラー発生時は自動リフレッシュして 1 回リトライします。
- 品質チェックは Fail-Fast ではなく、すべての問題を収集して結果を返します（呼び出し元が致命度に応じて処理を決定）。
- ロギングや追加のモニタリングは運用要件に合わせて設定してください（Slack 通知等の実装は別途）。

---

必要であれば、README にサンプル .env.example を追加したり、CLI スクリプト（例: kabusys-etl run）を作るテンプレートも提供できます。どのような利用シナリオ（ローカル開発 / CI / 本番自動実行）を想定するか教えてください。