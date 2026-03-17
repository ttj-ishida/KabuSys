# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（プロトタイプ）。  
J-Quants API や RSS ニュースを収集して DuckDB に保存し、ETL／品質チェック／マーケットカレンダー管理／監査ログなどの基盤機能を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです：

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集と銘柄コード抽出（SSRF・XML Bomb・サイズ制限対策）
- DuckDB を用いたスキーマ定義と冪等なデータ保存（ON CONFLICT ロジック）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー操作（営業日判定・次/前営業日の取得）
- 監査ログ（信号→発注→約定をトレースするテーブル群）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）

設計上、産出物は監査可能で冪等性を重視し、外部 API の失敗に対して堅牢になるよう作られています。

---

## 主な機能一覧

- 環境変数管理（.env/.env.local 自動読み込み、無効化オプションあり）
- J-Quants クライアント（get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レート制限（120 req/min）管理
  - 再試行（指数バックオフ、HTTP 408/429/5xx 対応）
  - 401 時はリフレッシュトークンで自動リフレッシュして 1 回リトライ
  - データ取得時に fetched_at を UTC で記録
- DuckDB スキーマ初期化（raw / processed / feature / execution / audit 層を定義）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
  - run_daily_etl で日次 ETL を一括実行
- ニュース収集（RSS）モジュール
  - トラッキングパラメータ除去・URL 正規化・記事ID は SHA-256 の先頭 32 文字
  - SSRF 対策（スキーム検査、プライベートアドレス拒否、リダイレクト事前検査）
  - gzip サイズ上限チェック（デフォルト 10MB）
  - raw_news 保存と記事→銘柄の紐付け保存（冪等）
- マーケットカレンダー管理（営業日判定、次/前営業日、期間内営業日リスト）
- 監査ログスキーマ（signal_events / order_requests / executions など）
- 品質チェック（欠損・重複・スパイク・日付不整合）

---

## セットアップ手順

前提：
- Python 3.10+（typing の一部表記により）を推奨
- DuckDB を利用するためネイティブ拡張が必要（pip インストールで取得されます）

1. リポジトリをクローン／チェックアウト（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   必要な主な依存は以下です：
   - duckdb
   - defusedxml
   （その他は標準ライブラリを利用）

   例：
   ```
   pip install duckdb defusedxml
   ```

   （パッケージ化されている場合は `pip install -e .` などで開発インストールします）

4. 環境変数を準備
   プロジェクトルートに `.env`（および任意で `.env.local`）を作成します。必要なキー例：

   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   自動読み込みはデフォルトで有効です。テストなどで無効化する場合：
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（例）

Python から直接利用する基本例を示します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ファイルを作成して全テーブルを作成
  ```

- 日次 ETL 実行（J-Quants トークンは settings から自動使用）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を省略すると今日が対象
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- ニュース収集の実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 銘柄抽出用の有効なコードセット（例: {'7203','6758',...}）
  results = run_news_collection(conn, known_codes=set(['7203','6758']))
  print(results)  # {source_name: 新規保存件数}
  ```

- 監査ログ初期化（監査専用 DB に分ける場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants の ID トークンを手動取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

注記：
- run_daily_etl、run_prices_etl 等は例外を個別にハンドリングし、失敗しても他の処理は継続します。戻り値（ETLResult）で品質問題やエラーの有無を確認してください。
- ニュース収集は外部ネットワークを利用するため、SSRF やサイズ制限のため一部フィードがスキップされることがあります。

---

## 環境変数と設定（Settings）

主要な設定項目は `kabusys.config.Settings` 経由でアクセスできます。主な必須環境変数：

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabu API パスワード
- SLACK_BOT_TOKEN: Slack Bot トークン
- SLACK_CHANNEL_ID: 通知先チャンネル ID

その他：
- DUCKDB_PATH / SQLITE_PATH（DB ファイルパス）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（ログレベル）

自動的にプロジェクトルートの `.env` / `.env.local` をロードします（.git または pyproject.toml を基準にルートを探索）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要なファイルとモジュール構成（抜粋）：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査テーブル定義と初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略関連のプレースホルダ（拡張用）
  - execution/
    - __init__.py            — 発注/実行関連のプレースホルダ（拡張用）
  - monitoring/
    - __init__.py            — 監視関連のプレースホルダ（拡張用）

（上記はこのコードベースに含まれる主要モジュールの概観です）

---

## 開発上の注意点 / 実運用メモ

- J-Quants のレート制限（120 req/min）を守るため、クライアントに RateLimiter が組み込まれています。外部からの連続呼び出し時は注意してください。
- DuckDB を使ったデータ永続化は ON CONFLICT（冪等）設計になっていますが、外部から直接 DB に書き込む場合は一貫性に注意してください。
- ニュース収集では SSRF・XML 攻撃・大規模レスポンス対策が実装されています。RSS フィードの形式差異や gzip 圧縮の扱いで一部記事がスキップされることがあります。ログを参照して原因を確認してください。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。運用での保持方針を設計してください。

---

## ライセンス・貢献

この README ではライセンス情報は含まれていません。リポジトリルートの LICENSE や CONTRIBUTING ガイドを参照してください。

---

README の補足や、使い方の追加例（Slack 通知・kabu API 発注処理等）が必要であれば教えてください。必要に応じてサンプルスクリプトや unit test のテンプレートも作成します。