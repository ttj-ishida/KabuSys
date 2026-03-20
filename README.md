# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォーム／データ基盤のコアライブラリです。  
J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に保存し、研究用ファクター計算、特徴量合成、戦略シグナル生成、ニュース収集、ETL パイプラインなどを提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（計算は target_date 時点の情報のみを使用）
- DuckDB をデータ層として使用し、冪等な保存（ON CONFLICT）を行う
- 外部 API 呼び出しはクライアント層（jquants_client）に限定し、リトライ・レート制御を実装
- Research 層は本番発注・実行層に依存しない（解析用ユーティリティとして単体で利用可能）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（jquants_client）：株価日足 / 財務データ / マーケットカレンダーの取得（ページネーション対応、トークン自動リフレッシュ、レート制限）
  - DuckDB スキーマ定義と初期化（data.schema.init_schema）
  - 保存ユーティリティ（raw_prices / raw_financials / market_calendar などへの冪等保存）

- ETL パイプライン
  - 日次差分 ETL（data.pipeline.run_daily_etl）
  - 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェックフック（quality モジュール経由）

- 特徴量・戦略
  - ファクター計算（research.factor_research）：モメンタム / ボラティリティ / バリュー等
  - 特徴量合成（strategy.feature_engineering.build_features）：ユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT
  - シグナル生成（strategy.signal_generator.generate_signals）：features と ai_scores を統合して BUY/SELL シグナルを作成

- ニュース収集
  - RSS フィード収集（data.news_collector）：XML 安全対策、SSRF 対策、トラッキングパラメータ除去、記事ID のハッシュ化、raw_news / news_symbols への保存

- ユーティリティ
  - 統計ユーティリティ（data.stats.zscore_normalize）
  - マーケットカレンダー管理（data.calendar_management）
  - 監査ログ（data.audit）等のスキーマ

---

## セットアップ手順

前提
- Python 3.10 以上（コード中で X | Y の型表記を使用しているため）
- pip

1. リポジトリをクローン（既にローカルにある場合は省略）:
   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 依存パッケージをインストール（pyproject.toml / requirements.txt がある想定）:
   - 開発中に編集可能な形でインストールする場合:
     ```
     python -m pip install -e .
     ```
   - 必要な個別パッケージ（例）:
     ```
     python -m pip install duckdb defusedxml
     ```
   実環境では logging や net 周りのライブラリも利用されます。プロジェクトに requirements を用意している場合はそちらを使用してください。

3. 環境変数の設定
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 任意 / デフォルト有り: DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db), KABUSYS_ENV (development / paper_trading / live, default: development), LOG_LEVEL (default: INFO)
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxx...
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

4. DuckDB スキーマの初期化:
   - Python REPL やスクリプト内で:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - 引数に ":memory:" を渡せばメモリ DB を使えます（テスト向け）。

---

## 使い方（簡単な例）

以下は代表的な機能の呼び出し例です。実行は Python スクリプトや REPL で行います。

- DuckDB の初期化（上記）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL を実行（市場カレンダー取得 → 株価取得 → 財務取得 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 特徴量を作成（features テーブルに書き込む）
  ```python
  from kabusys.strategy import build_features
  from datetime import date

  written = build_features(conn, date(2025, 3, 20))
  print(f"features upserted: {written}")
  ```

- シグナル生成（signals テーブルに書き込む）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  count = generate_signals(conn, date(2025, 3, 20))
  print(f"signals written: {count}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  # known_codes は銘柄抽出に使う有効銘柄コードのセット（任意）
  saved_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(saved_map)
  ```

- 直接 J-Quants API を呼ぶ（テスト / デバッグ用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  token = get_id_token()
  recs = fetch_daily_quotes(id_token=token, date_from=date(2025,1,1), date_to=date(2025,1,31))
  saved = save_daily_quotes(conn, recs)
  ```

注意:
- run_daily_etl 等は内部で例外を捕捉しつつ処理を継続する設計です。戻り値の ETLResult にエラーや品質問題が記録されます。
- 本ライブラリは発注・ブローカー API 連携のためのスケルトン（execution / audit等）を用意していますが、実際の送信部分は証券会社 API に合わせた実装が必要です。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード（発注連携時）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視・モニタリング用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development|paper_trading|live)
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）

---

## ディレクトリ構成（主なファイル）

プロジェクトは src/ 配下の kabusys パッケージで構成されています。主要なファイル・モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動ロード）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（取得・保存）
  - news_collector.py            — RSS ニュース収集・保存
  - schema.py                    — DuckDB スキーマ定義と init_schema
  - stats.py                     — zscore_normalize 等の統計ユーティリティ
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - features.py                  — data 層の特徴量ユーティリティ再エクスポート
  - calendar_management.py       — 市場カレンダー管理（営業日判定等）
  - audit.py                     — 監査ログ用スキーマ（signal_events, order_requests, executions）
- src/kabusys/research/
  - __init__.py
  - factor_research.py           — ファクター計算（momentum/volatility/value）
  - feature_exploration.py       — IC計算・将来リターン・統計サマリー
- src/kabusys/strategy/
  - __init__.py
  - feature_engineering.py       — features テーブル作成（正規化・フィルタ）
  - signal_generator.py          — final_score 計算・BUY/SELL シグナル生成
- src/kabusys/execution/           — 発注・実行層（スケルトン）
- src/kabusys/monitoring/          — 監視・モニタリング（配置想定）

（上記はコードベースの主要モジュール抜粋です。詳細は各ソースファイルの docstring を参照してください。）

---

## 開発・運用上の注意点

- Python バージョンは 3.10 以上を推奨します（型ヒントに | を使用）。
- DuckDB のバージョン差異や制約機能の違いに注意（README 内の注釈にあるように DuckDB の一部バージョンでは ON DELETE CASCADE 等の機能が未サポート）。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は固定間隔のスロットリングとリトライを実装していますが、運用時は実行頻度の設計に注意してください。
- .env ファイルの扱い: プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を自動検出して `.env` / `.env.local` を読み込みます。テストなどで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- セキュリティ: ニュース収集は SSRF や XML Bomb を考慮して実装していますが、追加の実運用ガード（プロキシやネットワーク制限等）を検討してください。

---

問題の報告、機能追加、パッチの提案は Issue / Pull Request を通してお願いします。README に載せきれない使用例や運用手順はリポジトリ内のドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。