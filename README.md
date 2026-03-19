# KabuSys

日本株向けの自動売買システム（ライブラリ / ツール群）

バージョン: 0.1.0

このリポジトリは、データ取得（J‑Quants）、ETL、特徴量エンジニアリング、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む日本株自動売買プラットフォームのコアコンポーネント群を提供します。DuckDB を内部データストアとして用い、研究（research）と運用（execution）を分離して設計されています。

主な設計方針:
- ルックアヘッドバイアスを排除（target_date 時点のデータのみ使用）
- 冪等性（DB 挿入は ON CONFLICT / DO UPDATE 等で実装）
- API 呼び出しはレート制限とリトライ、トークン自動リフレッシュ対応
- 外部依存は最小限（標準ライブラリ + duckdb 等）

---

## 機能一覧

- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーのページネーション対応取得
  - レートリミッタ、リトライ（指数バックオフ）、401時のトークン自動リフレッシュを備える
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得 + backfill）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル群定義と初期化
- 特徴量エンジニアリング
  - research モジュールの raw ファクターを正規化・合成して features テーブルへ保存
  - ユニバースフィルタ（最低株価・平均売買代金）や Z スコア正規化を実装
- シグナル生成
  - features と ai_scores を統合して最終スコアを算出、BUY/SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム抑制、ストップロス等のエグジット判定を実装
- ニュース収集
  - RSS フィードから記事を収集し raw_news に冪等保存、銘柄コード抽出（既知コードセットとの照合）
  - SSRF 防止、XML 脆弱性対策、サイズ制限等の安全対策を実装
- マーケットカレンダー管理
  - JPX カレンダー取得・先読み、営業日判定ユーティリティ（next/prev/get_trading_days 等）
- 研究ユーティリティ
  - forward returns, IC（Spearman ρ）、ファクター統計サマリ、Z スコア正規化など

---

## セットアップ手順

前提:
- Python 3.9+（型注釈や一部構文に依存）
- duckdb がインストール可能であること

ローカル開発環境でのインストール例:

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール（例）
   - 本コードベースの外部依存は duckdb と defusedxml 等が必要です。適宜 requirements.txt を用意している場合はそれを使ってください。最低限:
   ```
   pip install duckdb defusedxml
   ```
   - 開発時はパッケージを編集しやすくするため editable インストールを推奨:
   ```
   pip install -e .
   ```

4. 環境変数 (.env) の準備
   - プロジェクトのルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 bot token
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードの無効化フラグ
     - KABUSYS_... 他
   - 例（.env）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - デフォルトでは DUCKDB_PATH が `data/kabusys.duckdb`（settings.duckdb_path）に設定されます。初期化は以下コードで実行できます:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   - CLI スクリプトがある場合はそちらを利用できます（プロジェクトに合わせて）。

---

## 使い方（主要なユースケース）

以下は Python REPL やスクリプトから呼び出す例を簡潔に示します。

1. DuckDB 接続の初期化
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")
   # 既存 DB に接続するだけなら:
   # conn = get_connection("data/kabusys.duckdb")
   ```

2. 日次 ETL（市場カレンダー・株価・財務の差分取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量構築（features テーブルへ）
   ```python
   from kabusys.strategy import build_features
   from datetime import date
   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")
   ```

4. シグナル生成（signals テーブルへ）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {total}")
   ```

5. ニュース収集ジョブ（RSS を取得し raw_news に保存）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes: 銘柄抽出に使う有効コードの set（例: {"7203","6758",...}）
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set())
   print(res)
   ```

6. マーケットカレンダー操作
   ```python
   from kabusys.data.calendar_management import is_trading_day, next_trading_day
   from datetime import date
   d = date(2026, 3, 1)
   print(is_trading_day(conn, d))
   print(next_trading_day(conn, d))
   ```

---

## 主要モジュール（概要）

- kabusys.config
  - .env / 環境変数の読み込みと settings オブジェクト
  - 自動 .env 読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行われる
- kabusys.data.jquants_client
  - J-Quants API クライアント（取得・保存ユーティリティ）
  - レート制御、再試行、トークンリフレッシュを実装
- kabusys.data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）と初期化関数
- kabusys.data.pipeline
  - 差分 ETL / 日次 ETL の実装
- kabusys.data.news_collector
  - RSS フィード収集、前処理、raw_news/ news_symbols 保存
- kabusys.data.calendar_management
  - カレンダー更新ジョブと営業日判定ユーティリティ
- kabusys.research
  - calc_momentum / calc_volatility / calc_value 等の factor 計算
  - calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - build_features（特徴量構築）
  - generate_signals（シグナル生成）
- kabusys.execution
  - （発注・約定・ポジション管理は execution 層で実装予定 / 空のパッケージ）

---

## ディレクトリ構成

（src 配下を基準とした主要ファイル・モジュール構成の抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - calendar_management.py
    - features.py
    - audit.py
    - (その他 data 関連モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (モニタリング関連は今後の実装想定)

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化

設定は .env（および .env.local）に記述することで起動時に自動で取り込まれます。

---

## 運用上の注意点

- J-Quants の API レート制限（120 req/min）を遵守するため、jquants_client 内にレートリミッタを備えています。大量取得の際はバックオフや分割を検討してください。
- DuckDB スキーマ初期化は一度実行しておくこと。初期化は冪等で何度実行しても安全です。
- シグナル → 発注 → 約定のフローをトレースするための監査テーブル群（audit）が定義されています。発注実装時には order_request_id 等を正しく扱ってください。
- NewsCollector は SSRF / XML 脆弱性 / 大量レスポンス対策を実装していますが、公開 RSS を扱うときはソースの信頼性に注意してください。
- 本リポジトリのコードは主要なアルゴリズム・SQL を示しており、実運用に投入する前に十分なテスト（バックテスト・フォワードテスト）とリスク管理ルールの実装が必要です。

---

## 開発・拡張について

- 研究（research）モジュールは外部ライブラリに依存しない実装です。より高度な分析や可視化には pandas / numpy / matplotlib 等を用いた別ノートブックを用意すると良いです。
- execution 層（ブローカー接続・注文送信）は現状インターフェースを分離しています。実証実験 → ブローカーAPI実装の流れで実装してください。
- テスト: 各モジュールは依存注入（id_token 注入、_urlopen のモック等）を考慮して設計されています。ユニットテストを書きやすいです。

---

この README はコードベースの主要機能・使い方をまとめたものです。具体的な運用手順や追加の CLI、サービス化（systemd / Airflow など）は用途に応じて実装してください。質問や具体的な利用例（cron / コンテナ化 / CI 等）について要望があれば追記します。