# KabuSys

KabuSys は日本株向けの自動売買システム用ライブラリ群です。J-Quants / kabuステーション 等の外部 API からデータを取得・保管し、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログなど自動売買基盤に必要な機能を提供します。

主な設計方針は「冪等性」「トレーサビリティ（fetched_at / UTC 等）」「API レート制御とリトライ」「SSRF や XML Bomb 等のセキュリティ対策」です。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定の読み込み
  - .env / .env.local / OS 環境変数からの設定読み込み（自動読み込み、無効化可）
  - 必須環境変数の取得とバリデーション

- J-Quants API クライアント（jquants_client）
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - レートリミット（120 req/min）の管理・リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（news_collector）
  - RSS フィード取得・前処理（URL 除去、空白正規化）
  - トラッキングパラメータ除去による URL 正規化・SHA-256 による記事 ID 生成（冪等）
  - SSRF 対策（スキーム検証、プライベートホスト検査、リダイレクト検査）
  - defusedxml による安全な XML パース
  - DuckDB への冪等保存（INSERT ... RETURNING、トランザクション）

- データスキーマ管理（schema）
  - Raw / Processed / Feature / Execution / Audit 層を含む DuckDB スキーマ定義
  - init_schema(db_path) での初期化（冪等）

- ETL パイプライン（pipeline）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新／バックフィル（API の後出し修正を考慮）
  - 品質チェック（欠損、重複、スパイク、日付不整合）への連携

- マーケットカレンダー管理（calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティ
  - calendar_update_job による夜間差分更新

- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 に至るトレース用のテーブル群（UUID・冪等キー）
  - init_audit_schema / init_audit_db による初期化

- データ品質チェック（quality）
  - 欠損データ、重複、スパイク（前日比）、日付不整合の検出
  - QualityIssue 型で問題を集約して返却

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 のユニオン型 (A | B) を使用）
- git 等の環境

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージをインストール
   - 主な外部依存（コードから読み取れるもの）:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - パッケージ化済みであれば編集インストール:
     ```
     pip install -e .
     ```

4. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（CWD ではなくソースファイル位置から .git / pyproject.toml を探索してプロジェクトルートを特定します）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（省略時 data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（省略時 development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時 INFO）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方

以下は代表的なユースケースの例です。実運用ではジョブスケジューラ（cron / systemd timer / Airflow 等）や監視を組み合わせて実行してください。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   # conn を使って以降の ETL / ジョブを実行
   ```

2. 日次 ETL を実行する
   ```python
   from kabusys.data import pipeline, schema
   from kabusys.config import settings
   from datetime import date

   conn = schema.init_schema(settings.duckdb_path)
   result = pipeline.run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   run_daily_etl は以下を順に実行します:
   - 市場カレンダー ETL（先読み）
   - 株価日足 ETL（差分 + backfill）
   - 財務データ ETL（差分 + backfill）
   - 品質チェック（オプション）

3. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data import news_collector, schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   # known_codes は銘柄抽出で参照する有効コードの集合（例: prices テーブルから取得）
   known_codes = {"7203", "6758", "9984"}  # 実際は DB から取得する
   result = news_collector.run_news_collection(conn, known_codes=known_codes)
   print(result)
   ```

4. カレンダー夜間更新ジョブ
   ```python
   from kabusys.data import calendar_management, schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   saved = calendar_management.calendar_update_job(conn)
   print(f"saved: {saved}")
   ```

5. 監査ログスキーマの初期化（audit）
   ```python
   from kabusys.data import schema, audit
   conn = schema.init_schema("/path/to/kabusys.duckdb")
   audit.init_audit_schema(conn, transactional=True)
   ```

注意点
- jquants_client の get_id_token は settings.jquants_refresh_token を使用します。トークン管理に注意してください。
- ニュース収集は外部 URL を取得するため、ネットワークや RSS ソースの健全性に依存します。SSRF 防御・サイズ制限・XML パース例外処理などを実装済みですが、運用監視を設けてください。

---

## ディレクトリ構成

リポジトリの主要部分（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集・保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（日次 ETL 等）
    - calendar_management.py  — マーケットカレンダー管理・ユーティリティ
    - audit.py                — 監査ログ（signal/order/execution）スキーマ
    - quality.py              — データ品質チェック
  - strategy/                  — 戦略レイヤ（空パッケージ・拡張ポイント）
  - execution/                 — 発注・ブローカ連携（空パッケージ・拡張ポイント）
  - monitoring/                — 監視関連（空パッケージ・拡張ポイント）

補足:
- DuckDB を用いてローカルに軽量な分析 DB を構築する設計です。ファイルパスは settings.duckdb_path で指定されます。
- strategy / execution / monitoring は拡張ポイントとして用意されています。実際のアルゴリズムやブローカ接続はここに実装してください。

---

## 開発・貢献

- コードスタイル: 型注釈と docstring を重視しています。ユニットテストと統合テストを追加してください。
- 自動 .env ロードは便利ですが、テスト時に環境の分離が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- セキュリティに敏感な部分（トークン/パスワード/外部 URL 取り扱い）は設計時に注意しています。追加の外部依存（HTTP クライアント / retry ライブラリ 等）を導入する際は脆弱性評価を行ってください。

---

必要であれば、README に以下を追記できます:
- 具体的な cron/systemd での運用例
- よくあるトラブルシュート（例: Token 期限切れ、DuckDB ロック）
- テスト実行コマンドや CI 設定例

追記希望があれば目的に合わせてドキュメントを拡張します。