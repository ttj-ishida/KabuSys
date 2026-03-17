# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API から市場データを差分取得して DuckDB に保存し、ニュース収集・品質チェック・カレンダー管理・監査ログなどの機能を備えています。戦略・発注・モニタリング層と連携して自動売買システムのデータ基盤を構築するためのユーティリティ群を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レートリミット（120 req/min）対応、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias の防止
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィード取得・前処理（URL 除去・空白正規化）
  - URL 正規化・トラッキングパラメータ除去・SHA-256 による記事ID生成（冪等）
  - SSRF 対策、受信サイズ制限、defusedxml による XML 攻撃対策
  - DuckDB への一括保存と銘柄コード抽出（news_symbols）

- ETL パイプライン
  - 日次 ETL: 市場カレンダー→株価→財務 の順で差分取得・保存
  - 差分更新、バックフィル（後出し修正吸収）、品質チェックの実行（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を ETLResult オブジェクトで返却

- マーケットカレンダー管理
  - 営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）
  - 夜間バッチでカレンダーを差分更新（calendar_update_job）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理
  - UUID によるトレーサビリティ、UTC タイムスタンプ固定

- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、主キー重複、日付不整合を検出
  - QualityIssue オブジェクトで詳細を返す（error / warning）

---

## 動作要件（推奨）

- Python 3.10+
- 必要パッケージ（主要）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

（パッケージ管理はプロジェクト方針に合わせて requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージのインストール
   例（pip）:
   ```bash
   pip install duckdb defusedxml
   ```
   ※ 実際の依存はプロジェクトに合わせて requirements.txt / pyproject.toml を使用してください。

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。自動ロードは .git または pyproject.toml を探してプロジェクトルートを特定します。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意／デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   `.env` の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベーススキーマの初期化（DuckDB）
   - インメモリまたはファイルにスキーマを作成:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ用スキーマ初期化（別 DB にする場合）:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要 API と例）

以下は簡単な使用例です。実際はログ設定やエラーハンドリングを追加してください。

- 日次 ETL を実行する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集と保存
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  # known_codes: 銘柄抽出に使う 4桁コードの集合（任意）
  known_codes = {"7203","6758", ...}
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- J-Quants トークンを直接取得する（テスト用など）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数の JQUANTS_REFRESH_TOKEN を使用
  ```

- DB の既存接続を取得（初回は init_schema 推奨）
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

---

## 主要モジュール説明（概要）

- kabusys.config
  - 環境変数の自動ロード（.env / .env.local）、必須値チェック、設定ラッパー (settings)

- kabusys.data.jquants_client
  - J-Quants API 呼び出し、認証、fetch/save 関数（save_* は DuckDB への冪等保存を行う）

- kabusys.data.news_collector
  - RSS 取得・前処理・記事ID生成・DuckDB 保存・銘柄コード抽出

- kabusys.data.schema
  - DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution 層のテーブルとインデックス）

- kabusys.data.pipeline
  - 日次 ETL の差分取得ロジック、各 ETL ジョブ（prices / financials / calendar）、品質チェックの統合

- kabusys.data.calendar_management
  - 営業日判定や next/prev_trading_day、夜間カレンダー更新ジョブ

- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）スキーマの初期化ユーティリティ

- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合のチェックロジック

- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - 戦略・発注・モニタリング用のパッケージ群（初期化ファイルあり。戦略実装・ブローカー接続等はここに拡張）

---

## ディレクトリ構成

以下はソースの主要ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（README 上で示したのは主要モジュール。プロジェクトではさらにファイル・テスト・ドキュメントがある可能性があります）

---

## 運用上の注意 / ベストプラクティス

- 環境変数は機密情報を含むため、.env ファイルを VCS にコミットしないでください（.gitignore を利用）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動で .env をロードしないため、テスト時に利用可能です。
- J-Quants API のレート制限（120 req/min）を守る設計ですが、大量バッチ時は想定外の制約に注意してください。
- DuckDB はシングルファイル DB なのでバックアップと排他アクセス設計（ロック）を考慮してください。
- ニュース取得は外部 RSS に依存するため、RSS の形式差やパフォーマンスに対して堅牢な実装が組まれていますが、プロダクション運用ではタイムアウト・リトライ・監視を設定してください。

---

## 付記（開発者向け）

- 型アノテーションとデータクラスを使っているため、静的解析ツール（mypy 等）を通すと保守性が向上します。
- テストを書く際は、外部 API 呼び出しやネットワーク I/O（_urlopen 等）をモックしてください。
- DuckDB のトランザクション管理や RETURNING を利用して正確な件数取得を行っています。大きいバルク挿入時はチャンクサイズに注意してください（news_collector の _INSERT_CHUNK_SIZE 等）。

---

README にある使い方は典型的な例です。必要に応じて具体的なコマンドや CI/CD 用のスクリプト、requirements ファイル、環境別設定ファイル（.env.example）を追加してください。必要なら README を拡張してデプロイ手順・監視設定・トラブルシュート項を追加できます。