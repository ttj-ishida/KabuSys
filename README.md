# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。  
データ取得（J-Quants / RSS）、ETLパイプライン、DuckDBスキーマ、品質チェック、監査ログなど、トレーディングシステムに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株自動売買システムのための基盤モジュール群です。主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得する
- RSS からニュース記事を収集し、銘柄紐付けを行う
- DuckDB にスキーマを展開し、冪等に生データを保存する
- ETL（差分取得、バックフィル、品質チェック）を自動化する
- 発注・約定の監査ログ（トレーサビリティ）を保持する

設計上のポイントとして、API レート制御、リトライ、トークン自動リフレッシュ、SSRF対策、Gzip/サイズ制限、トランザクション管理、品質チェックなど安全性・堅牢性を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants から日次株価（OHLCV）、四半期財務情報、マーケットカレンダーを取得
  - レート制限（120 req/min）、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data.news_collector
  - RSS フィード収集・XML パース（defusedxml 使用）
  - URL 正規化・トラッキングパラメータ除去・記事ID（SHA-256先頭32文字）
  - SSRF 対策（リダイレクト検査、プライベートIP拒否）、レスポンスサイズ制限
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING）
- data.schema
  - DuckDB 向けのスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema() でテーブル・インデックスを冪等に作成
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー・株価・財務を差分取得して保存、品質チェック実行
  - 差分更新・バックフィルロジック、営業日調整、品質チェック（quality モジュール）
- data.quality
  - 欠損、スパイク（前日比）、重複、日付不整合（未来日・非営業日）を検出するチェック群
  - QualityIssue を返し、呼び出し側が対処可
- data.audit
  - シグナル→発注→約定の監査ログ用スキーマ（order_request_id の冪等性等）
  - init_audit_schema / init_audit_db による初期化

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 形式やその他の構文を使用）
- pip と virtualenv を推奨

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要な依存パッケージをインストール
   - 本コードで利用している主な外部ライブラリ:
     - duckdb
     - defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt があればそれを使用してください）
   ```bash
   pip install duckdb defusedxml
   # 開発用: pip install -e .
   ```

3. 環境変数を用意する
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（優先順: OS env > .env.local > .env）。
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: Slack チャネル ID
   - 任意・デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトからの基本操作例です。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # DB ファイルを作成・接続、テーブル作成
   ```

2. 日次 ETL を実行する（デフォルト: 本日）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # ETL 実行
   print(result.to_dict())
   ```

3. ニュース収集ジョブを実行する
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes を渡すと記事と銘柄の紐付けを行う（存在する銘柄コードセット）
   saved = run_news_collection(conn, known_codes={"7203", "6758"})
   print(saved)  # {source_name: saved_count}
   ```

4. 監査ログテーブルの初期化（監査専用 DB を作る場合）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   # または既存 conn に監査スキーマを追加
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

5. J-Quants トークンを直接取得（テスト等）
   ```python
   from kabusys.data.jquants_client import get_id_token
   id_token = get_id_token()  # settings.jquants_refresh_token を使用
   ```

ログ出力や詳細設定は環境変数（LOG_LEVEL など）で制御してください。

---

## 主要モジュール一覧（責任範囲）

- kabusys.config
  - 環境変数の自動読み込み（.env / .env.local）と設定アクセサ
  - Settings クラス経由で設定値を取得
- kabusys.data.jquants_client
  - J-Quants API 通信・ページネーション・保存ユーティリティ
  - fetch_* / save_* 系関数
- kabusys.data.news_collector
  - RSS フィード取得、記事正規化、raw_news への保存、銘柄抽出
- kabusys.data.schema
  - DuckDB スキーマ定義と init_schema / get_connection
- kabusys.data.pipeline
  - run_daily_etl、個別 ETL ジョブ（prices, financials, calendar）
- kabusys.data.quality
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - パッケージプレースホルダ（将来的な戦略・発注・監視ロジックの格納場所）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - audit.py
      - quality.py

---

## 運用上の注意・補足

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings.env の有効値: development / paper_trading / live。is_live 等のフラグを用いて挙動分岐できます。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は内部で固定間隔スロットリングとリトライを実装していますが、複数プロセスからの同時アクセスでは外部的な調整が必要です。
- news_collector は外部ネットワークを扱うため SSRF・XML Bomb・大容量レスポンスなどの対策を組み込んでいます（defusedxml、サイズ制限、ホスト検査など）。
- DuckDB は IN-MEMORY でもファイルベースでも使用可能です（":memory:" を指定可）。データ永続化時は DUCKDB_PATH を適切に設定してください。
- 品質チェックで検出された問題は ETLResult.quality_issues に格納されます。運用上は severity に応じてアラートや手動確認のワークフローを用意してください。

---

## 連絡先・貢献

リポジトリの issue / PR を通じて改善提案やバグ報告をお願いします。ドキュメント整備、テスト追加、モジュール拡張（戦略実装・ブローカー接続等）の貢献を歓迎します。

---

README の補足やサンプルの追加（CI、デモスクリプト、requirements.txt 等）が必要なら教えてください。