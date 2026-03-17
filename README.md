# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
J-Quants API や RSS を取り込み、DuckDB に冪等的に保存、品質チェックやカレンダー管理、監査ログの初期化までを含むデータプラットフォーム + 補助モジュール群です。

主な設計方針
- データ取得は冪等（ON CONFLICT）で DB に安全に保存
- API レート制限・リトライ・トークン自動リフレッシュに対応
- Look-ahead bias を防ぐため取得時刻（UTC）を記録
- ニュース収集では SSRF / XML Bomb / 大容量レスポンスなどの攻撃対策を実装
- 品質チェックで欠損・スパイク・重複・日付不整合を検出
- 監査ログ（signal → order → execution のトレース）をサポート

---

## 機能一覧
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務四半期データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）・リトライ・401 時のトークン自動リフレッシュ対応
  - DuckDB への冪等保存関数（save_*）
- ニュース収集（RSS）
  - RSS フィード取得・URL 正規化・トラッキングパラメータ除去
  - defusedxml による XML パースで安全に処理
  - 記事ID は正規化 URL の SHA-256 の先頭 32 文字（冪等保証）
  - raw_news / news_symbols テーブルへの一括保存（INSERT ... RETURNING）
  - 銘柄コード抽出（4桁数字、known_codes によるフィルタ）
- ETL パイプライン
  - 差分更新（最終取得日から差分のみ取得）
  - バックフィル機能（後出し修正吸収）
  - 市場カレンダー先読み
  - 品質チェックの実行（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日リスト、カレンダー更新ジョブ
  - カレンダー未取得時は曜日ベースでフォールバック
- データスキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層の DDL を定義
  - init_schema / init_audit_schema / init_audit_db で簡単初期化
- 監査ログ（audit）
  - signal_events, order_requests, executions テーブルによるトレーサビリティ
  - 全ての TIMESTAMP は UTC を想定

---

## セットアップ手順

前提
- Python 3.9+（type hint に | を使っているため 3.10 以上が想定される場合がありますが、互換性はプロジェクトに合わせてください）
- ネットワークアクセス（J-Quants / RSS）

推奨手順（一例）
1. 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール
   - 必要な主な外部依存:
     - duckdb
     - defusedxml
   例:
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそちらからインストールしてください）

3. 環境変数の設定
   - .env ファイル（プロジェクトルートの .env / .env.local を自動読み込み）または OS 環境変数で設定します。
   - 自動ロードはデフォルトで有効。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（プロジェクト内 Settings で必須とされるもの）
   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID       — Slack チャンネル ID

   任意 / デフォルトあり
   - KABU_API_BASE_URL      — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH            — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH            — デフォルト: data/monitoring.db
   - KABUSYS_ENV            — 値: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DB スキーマ初期化（DuckDB）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
   # 監査ログを別DB/同DBに初期化する場合:
   from kabusys.data import audit
   audit.init_audit_schema(conn)  # 既存の conn に監査テーブルを追加
   # 監査専用 DB を初期化する場合:
   # audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主な API と実行例）

※ ここでは主要なユースケースの最小例を示します。

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema

  # DB を初期化（初回のみ）
  conn = schema.init_schema("data/kabusys.duckdb")

  # ETL を実行（target_date を指定しないと本日）
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS から記事を収集して保存）
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  # 既定の RSS ソース (DEFAULT_RSS_SOURCES) を使う場合
  res = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(res)  # { source_name: 新規保存件数, ... }
  ```

- J-Quants API を直接使う（トークン取得・データフェッチ）
  ```python
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings.jquants_refresh_token を内部で使用
  quotes = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 監査ログの初期化（signal/order/execution テーブル）
  ```python
  from kabusys.data import schema, audit
  conn = schema.init_schema("data/kabusys.duckdb")
  audit.init_audit_schema(conn)  # 監査テーブルを追加
  ```

- 市場カレンダーユーティリティ
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  from datetime import date
  calendar_management.is_trading_day(conn, date(2024, 1, 1))
  next_day = calendar_management.next_trading_day(conn, date(2024, 1, 1))
  ```

ログレベルや実行環境は `KABUSYS_ENV` / `LOG_LEVEL` で制御します。

---

## ディレクトリ構成（主要ファイル）
（リポジトリ上の src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数読み込み・Settings 定義（自動 .env ロード機能）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント、fetch/save 関数
    - news_collector.py          — RSS ニュース収集・正規化・DB 保存
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     — マーケットカレンダー管理
    - audit.py                   — 監査ログテーブル定義・初期化
    - quality.py                 — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - schema.py                  — DuckDB スキーマ定義と init_schema / get_connection
  - strategy/
    - __init__.py                — 戦略層用パッケージ（拡張ポイント）
  - execution/
    - __init__.py                — 発注 / 実行層（拡張ポイント）
  - monitoring/
    - __init__.py                — 監視用モジュール（拡張ポイント）

---

## 注意事項 / 実運用上のポイント
- 環境変数の読み込み:
  - 自動でプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を読み込みます。
  - 既存 OS 環境変数は上書きされません（.env.local は override=True だが protected によって OS 変数は保護されます）。
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで利用）。
- J-Quants API:
  - レート制限 120 req/min を守るためモジュール内でスロットリングしています。
  - 401 受信時は内部でトークンを自動リフレッシュして 1 回だけ再試行します。
  - リトライは指数バックオフ（最大 3 回）を行い、429 の Retry-After ヘッダを優先します。
- ニュース収集:
  - RSS のレスポンスサイズは最大 10 MB に制限（Gzip 展開後も同様）。
  - リダイレクト先のスキーム検査・プライベート IP 検査を行い SSRF を防止します。
- DuckDB スキーマ:
  - DDL は冪等化されており、何度実行しても安全です。
  - audit.init_audit_schema は既存接続に監査テーブルを追加します（UTC タイムゾーン設定あり）。
- 品質チェック:
  - run_all_checks はエラー・警告を集約して返します。呼び出し側のポリシーで ETL 継続／停止を判断してください。

---

## 貢献 / 拡張ポイント
- strategy/ や execution/ は拡張ポイントとして設計されています。戦略ロジック、ポートフォリオ構築、ブローカー連携はここに実装してください。
- monitoring/ 以下に Prometheus / メトリクス、健康チェック、アラート連携を追加することが想定されています。

---

README は開発時に必要な基本情報をまとめたものです。実行環境や運用ポリシーに合わせて .env の管理、機密情報の取り扱い、スケジューラ（cron / Airflow 等）からの実行やログ集約を検討してください。必要があればサンプルの .env.example や簡易運用ガイドを追加します。