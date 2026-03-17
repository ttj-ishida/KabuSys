# KabuSys

日本株自動売買プラットフォーム用のライブラリ群（KabuSys）。  
データ取得・ETL、ニュース収集、マーケットカレンダー管理、監査ログ（トレーサビリティ）、および発注／約定管理の基盤機能を提供します。

## 概要
KabuSys は J‑Quants や kabuステーション 等の外部サービスからデータを取得し、DuckDB を中心としたローカルデータベースに格納して分析・戦略実行の基盤を構築することを目的としたモジュール群です。  
設計上のポイント：

- API レート制限・リトライ制御・トークン自動リフレッシュを内包した J‑Quants クライアント
- DuckDB に対する冪等な保存（ON CONFLICT 処理）
- RSS ベースのニュース収集（SSRF対策・gzip/サイズ制限・トラッキング除去）
- 市場カレンダーを用いた営業日判定ロジック
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマと初期化ユーティリティ

## 主な機能
- J‑Quants API クライアント
  - 日次株価（OHLCV）、四半期財務（BS/PL）、JPX カレンダー取得
  - レートリミット・リトライ・トークン自動更新・ページネーション対応
- ETL パイプライン
  - 差分取得・バックフィル・保存・品質チェック
  - 日次 ETL（run_daily_etl）
- データスキーマ
  - Raw / Processed / Feature / Execution 層の DuckDB テーブル定義と初期化
- ニュース収集（RSS）
  - URL 正規化（トラッキングパラメータ除去）・記事ID生成（SHA-256先頭32文字）
  - SSRF 対応（スキーム／プライベートホスト検査）・サイズ制限・XML 攻撃対策（defusedxml）
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理
  - カレンダー更新ジョブ・営業日計算（next/prev/get）・SQ判定
- 品質チェック
  - 欠損、スパイク、重複、日付不整合検出
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルと初期化ユーティリティ

---

## 前提（依存）
最低限必要な Python パッケージ（抜粋）：

- Python 3.9+
- duckdb
- defusedxml

（プロジェクトの配布方法に応じて requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順（例）
1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   ```
   プロジェクトに requirements があればそれを使用してください：
   ```bash
   pip install -r requirements.txt
   # または
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（必須は明記）：
   - JQUANTS_REFRESH_TOKEN (必須) — J‑Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 環境 (development | paper_trading | live)
   - LOG_LEVEL — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)

   例 `.env`（トークン等は適切に置き換えてください）：
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python からスキーマを初期化します：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

   監査ログ専用 DB を初期化する場合：
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/kabusys_audit.duckdb")
   conn.close()
   ```

---

## 使い方（主要 API と例）
以下はライブラリの主要な使い方例です。実運用では例外処理やログ出力を適切に組み込みください。

1. 日次 ETL を実行する
   ```python
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")   # 初回は init_schema を使用
   result = run_daily_etl(conn)  # target_date を省略すると今日の処理を行う
   print(result.to_dict())
   conn.close()
   ```

2. ニュース収集ジョブを実行する
   ```python
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.data.news_collector import run_news_collection

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット（例）
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # ソース毎の新規保存件数
   conn.close()
   ```

3. カレンダー更新ジョブ（夜間バッチ想定）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"saved calendar rows: {saved}")
   conn.close()
   ```

4. 監査スキーマ初期化（既存 conn に追加する）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.audit import init_audit_schema

   conn = init_schema("data/kabusys.duckdb")
   init_audit_schema(conn)  # 監査テーブルを追加
   conn.close()
   ```

5. J‑Quants クライアントを直接利用してデータ取得
   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   jq.save_daily_quotes(conn, records)
   conn.close()
   ```

---

## 環境変数の詳細（まとめ）
- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視 DB、デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — '1' を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成
リポジトリの主要ファイル／モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定読み込み
    - data/
      - __init__.py
      - schema.py                     — DuckDB スキーマ定義 / init_schema
      - jquants_client.py             — J‑Quants API クライアント（fetch / save）
      - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
      - news_collector.py             — RSS ニュース収集・保存
      - calendar_management.py        — 市場カレンダー管理／営業日ロジック
      - quality.py                    — データ品質チェック
      - audit.py                      — 監査ログ（signal/order_requests/executions）
      - pipeline.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各モジュールは責務ごとに分離されています。主要なデータ操作は duckdb 接続（DuckDBPyConnection）を引数に受け取る設計で、テストしやすくなっています。

---

## 開発メモ / 運用ヒント
- 自動環境読み込みはプロジェクトルート（.git や pyproject.toml）を基準に行われます。テスト時や CI で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J‑Quants の ID トークンは内部キャッシュされ、401 時に自動リフレッシュされます。必要に応じて get_id_token に明示的な refresh_token を渡せます。
- ニュース収集では RSS のリダイレクト先も検査し、プライベートIP/ループバックへのアクセスを防止します。
- DuckDB の初期化は冪等（何度実行しても安全）です。監査スキーマは別途初期化可能。
- ETL のログや品質チェック結果は ETLResult に集約されるため、監査ログやアラートに利用できます。

---

問題の報告や改善提案、追加ドキュメントを希望される場合は欲しい内容（例: デプロイ手順、CI/CD 例、具体的な設定ファイルテンプレート、より詳しい API 使用例）を教えてください。README をその内容に合わせて拡張します。