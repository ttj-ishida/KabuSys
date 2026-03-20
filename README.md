# KabuSys

日本株向けの自動売買/データ基盤ライブラリ（KabuSys）。  
DuckDB をデータ格納に用い、J-Quants API や RSS ニュースを取得して ETL → 特徴量生成 → シグナル生成 → 発注監査までのワークフローをサポートします。

## プロジェクト概要
- 目的: 日本株のデータ取得・品質管理・特徴量生成・シグナル生成・監査ログを一貫して提供するライブラリ。
- 設計方針:
  - DuckDB を単一の永続ストアとして利用（raw / processed / feature / execution の多層スキーマ）。
  - ルックアヘッドバイアス対策（時点データのみ参照、fetched_at の記録など）。
  - 冪等性（ON CONFLICT / UPSERT を多用）。
  - 本番 API（発注等）には直接依存しないモジュール分割。

## 主な機能一覧
- データ取得（J-Quants）
  - 日足（OHLCV）、財務諸表、JPX カレンダーをページネーション対応で取得し DuckDB へ保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL / パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- スキーマ管理
  - DuckDB スキーマ初期化（init_schema）
- 特徴量計算（research / strategy 用）
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - クロスセクション Z スコア正規化（zscore_normalize）
  - features テーブルへの保存（build_features）
- シグナル生成
  - features + ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ書き込み（generate_signals）
  - Bear レジーム判定、ストップロス等のエグジット判定を含む
- ニュース収集
  - RSS フィードの取得・前処理・記事保存（SSRF 対策、gzip 上限、トラッキング除去）
  - 銘柄コード抽出と紐付け
- カレンダー管理
  - JPX カレンダーの更新 / 営業日判定ユーティリティ
- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル定義

## 要求ライブラリ（例）
最低限必要な外部依存（pipでインストール）:
- duckdb
- defusedxml

例:
pip install duckdb defusedxml

（プロジェクトの setup.cfg / pyproject.toml があればそちらを利用してください）

## セットアップ手順

1. リポジトリのチェックアウト
   - 例: git clone ...

2. Python 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存インストール
   - pip install -r requirements.txt  （requirements.txt があれば）
   - または最低限: pip install duckdb defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（execution 層で使用する場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャネルID
   - 任意（デフォルト有り）:
     - KABUSYS_ENV — 開発環境: `development`（デフォルト）、`paper_trading`、`live`
     - LOG_LEVEL — `INFO`（デフォルト）等
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: `data/monitoring.db`）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化
   - Python REPL やスクリプトから DuckDB スキーマを作成します。
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

## 使い方（Quickstart）

以下は代表的な操作例です。

- DuckDB 初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL の実行（J-Quants から差分取得 → 保存 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト

  オプション:
  - id_token を外部で取得して注入可能（テスト用途）
  - run_daily_etl(..., run_quality_checks=False) で品質チェックをスキップ

- 特徴量ビルド（features テーブル更新）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2024, 1, 1))  # 指定日付の features をビルド

- シグナル生成
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 1), threshold=0.6)

- RSS ニュース収集（raw_news / news_symbols へ保存）
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))  # sources を渡さないとデフォルト使用

- カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

- J-Quants API からデータを直接取得して保存（テストや細かい制御向け）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  jq.save_daily_quotes(conn, records)

## 主要 API / エントリポイント（抜粋）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=0.6)

※ 各関数は docstring に詳細な仕様・設計方針が記載されています。実際に使用する際は該当モジュールの docstring を参照してください。

## 設定（環境変数の詳細）
- 自動 .env 読み込み
  - デフォルトでプロジェクトルート（.git または pyproject.toml のある場所）から `.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env
  - 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- Settings（kabusys.config.settings）で次を参照:
  - jquants_refresh_token: JQUANTS_REFRESH_TOKEN
  - kabu_api_password: KABU_API_PASSWORD
  - kabu_api_base_url: KABU_API_BASE_URL （デフォルト http://localhost:18080/kabusapi）
  - slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env: KABUSYS_ENV（development, paper_trading, live）
  - log_level: LOG_LEVEL（DEBUG/INFO/...）

## ディレクトリ構成（主要ファイル）
プロジェクト内の主要なモジュール構成を示します（抜粋）。

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
    - features.py
    - calendar_management.py
    - audit.py
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
  - monitoring/  (モニタリング層は別途実装想定)

各モジュールは docstring に詳細な処理フロー・設計方針が書かれているため、実装の理解に役立ちます。

## 運用上の注意
- DuckDB のファイルパスは settings.duckdb_path を利用。バックアップ・ローテーションは運用に合わせて実装してください。
- J-Quants の API レート制限（120 req/min）に注意。クライアントは内部でスロットリングを実装しています。
- ニュース収集は外部 URL を扱うため SSRF や XML 攻撃対策（defusedxml、ホストチェック、サイズ制限等）を行っていますが、運用時はソースを検証してください。
- 本リポジトリでは発注（Broker へ送信）部分は抽象化または未実装の箇所があります。実際に発注を行う場合は別途 execution 層を実装し、監査（audit）テーブルと整合させてください。
- 環境が `live` の場合は特に注意深くログ・テストを行ってください（settings.is_live フラグあり）。

## 開発・貢献
- コードの追加や修正はモジュール単位で行い、docstring とユニットテストを充実させてください。
- 自動 .env 読み込みや安全性チェックはユニットテストで KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。

---

詳細な関数仕様や処理フローは各モジュールの docstring（ソース内コメント）を参照してください。必要であれば README に追加したい実行例や運用手順を追記します。