# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ用 README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータパイプライン、特徴量作成、戦略シグナル生成、ニュース収集、監査ログなどを含む自動売買基盤向けの Python モジュール群です。  
主に以下の用途を想定しています：

- J-Quants API からの市場データ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存・スキーマ管理
- ETL（差分更新・バックフィル・品質チェック）
- 研究用のファクター計算、特徴量正規化、シグナル生成
- RSS からのニュース収集と記事→銘柄紐付け
- 発注/約定/ポジションの監査ログ設計（スキーマ・DDL）

設計方針としては「冪等性」「ルックアヘッドバイアス防止」「外部API呼び出し・発注層との分離」「テスト容易性」を重視しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（レートリミット、リトライ、トークンリフレッシュ対応）
  - raw / processed / feature / execution 層を分けた DuckDB スキーマ・初期化（init_schema）
- ETL パイプライン
  - 日次差分 ETL（market calendar / prices / financials）
  - 差分取得・バックフィル・品質チェック（quality モジュール経由）
- 研究・特徴量
  - ファクター計算（momentum, volatility, value）
  - クロスセクション Z-スコア正規化
  - features テーブルへの冪等書き込み
- シグナル生成
  - features と AI スコアを統合して final_score を計算
  - Bear レジーム判定、BUY/SELL シグナルの生成（signals テーブルへ冪等保存）
- ニュース収集
  - RSS フィード取得（SSRF 対策、サイズ制限、XML 防御）
  - raw_news 保存、記事ID は正規化 URL の SHA-256（先頭32文字）
  - 記事と銘柄コードの紐付け（news_symbols）
- カレンダー管理
  - market_calendar の取得・判定ユーティリティ（is_trading_day / next_trading_day 等）
- 監査・トレーサビリティ
  - signal_events / order_requests / executions 等のテーブル定義（監査ログ設計）

---

## 前提（Prerequisites）

- Python 3.10 以上（typing | None 型表記などを使用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - defusedxml

これらは pip でインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（または作業ディレクトリにコードを置く）

2. 仮想環境の作成（任意）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （パッケージ化されている場合はプロジェクトルートで `pip install -e .` を実行することでローカルインストールできます。）

4. 環境変数 / .env の準備  
   このプロジェクトは .env ファイル（プロジェクトルート）または OS 環境変数から設定を読み込みます（読み込み優先順位: OS 環境変数 > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   代表的な環境変数（最低限必要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を使う場合）
   - KABU_API_BASE_URL: kabu API ベース URL（省略時は http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - LOG_LEVEL: ログレベル ("DEBUG","INFO",...、デフォルト: INFO)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（クイックスタート）

以下は主要 API の簡単な利用例です。すべて Python スクリプト／REPL 内で動作します。

1. DuckDB スキーマ初期化
   ```
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   ```

2. 日次 ETL 実行（J-Quants からデータを差分取得して保存）
   ```
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

3. 特徴量作成（features テーブル生成）
   ```
   from datetime import date
   from kabusys.strategy import build_features

   n = build_features(conn, target_date=date(2025, 1, 31))
   print(f"features upserted: {n}")
   ```

4. シグナル生成（signals テーブルへ書き込み）
   ```
   from datetime import date
   from kabusys.strategy import generate_signals

   total = generate_signals(conn, target_date=date(2025, 1, 31), threshold=0.6)
   print(f"signals written: {total}")
   ```

5. ニュース収集（RSS 取り込み）
   ```
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   # known_codes: 銘柄抽出に使う有効コード集合（例として空集合なら抽出スキップ）
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
   print(res)
   ```

6. J-Quants 生データ取得（必要に応じて直接呼び出し）
   ```
   from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
   quotes = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
   ```

7. 設定参照
   ```
   from kabusys.config import settings
   print(settings.jquants_refresh_token)  # 未設定なら ValueError
   ```

注意:
- ETL / データ取得系はネットワーク呼び出しを行います。事前に J-Quants トークンなどを設定してください。
- 各書き込み処理は可能な限り冪等（ON CONFLICT / トランザクション）を保つ実装になっています。

---

## 環境変数・設定の詳細

- 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml の存在する場所）を基準に `.env` / `.env.local` をロードします。OS 環境変数は優先されます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings API: `from kabusys.config import settings` で利用できます。主要プロパティ:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env, log_level, is_live, is_paper, is_dev

---

## ロギング

各モジュールは Python の標準 logging を使用しており、`LOG_LEVEL` 環境変数でログレベルを制御できます。アプリケーション側でハンドラ（ファイル/STDOUT/JSONなど）を設定して運用してください。

---

## ディレクトリ構成

主要なファイル・モジュールを示します（src/layout）。リポジトリの構成に応じて微差が生じることがあります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得 + 保存）
      - news_collector.py       # RSS ベースのニュース収集
      - schema.py               # DuckDB スキーマ定義と init_schema
      - stats.py                # zscore_normalize など統計ユーティリティ
      - pipeline.py             # ETL パイプライン（run_daily_etl 等）
      - features.py             # data.stats の再エクスポート
      - calendar_management.py  # market_calendar 周りのユーティリティ
      - audit.py                # 監査ログ用スキーマ（signal_events, order_requests, executions）
      - (その他: quality.py など想定)
    - research/
      - __init__.py
      - factor_research.py      # momentum/volatility/value の計算
      - feature_exploration.py  # forward returns / IC / summary / rank 等
    - strategy/
      - __init__.py
      - feature_engineering.py  # features テーブル構築（build_features）
      - signal_generator.py     # generate_signals（BUY/SELL 判定）
    - execution/                # 発注層（空の __init__.py が存在）
    - monitoring/               # 監視系（sqlite 等）用ディレクトリ想定
    - research/                 # 研究用モジュール群（上記）
  - pyproject.toml (想定)
  - .git/ (想定)
  - .env, .env.local (任意)

---

## 注意事項 / 運用メモ

- DuckDB のデフォルトファイルパスは `data/kabusys.duckdb`（Settings.duckdb_path）。
- ETL は差分更新を基本としており、backfill_days による再取得で API の後出し修正を吸収します。
- J-Quants API のレート制限（120 req/min）に合わせてクライアント側でレート制御・リトライを実装しています。
- RSS 取得は SSRF 対策・圧縮解凍制限・XML Sec 対策（defusedxml）を行っています。
- 設計上、execution（実際の発注送信）ロジックと戦略ロジックは明確に分離されています。実取引に接続する場合は execution 層に適切なブリッジを実装してください。
- 本 README はコード注釈を元に作成しています。実運用前に DataSchema.md / StrategyModel.md / DataPlatform.md 等の設計ドキュメントも参照してください（実装中想定ドキュメント）。

---

## 貢献・開発

- コーディング規約、テスト、CI の設定はプロジェクト標準に従ってください。
- 自動 .env 読み込みはテスト時に影響を与えることがあるため、単体テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を推奨します。
- 大きな変更（スキーマ変更・互換性破壊）はマイグレーション方針と監査ログを考慮してください。

---

必要であれば README に次の内容も追加できます：
- 詳細な API リファレンス（各関数の引数・戻り値サンプル）
- 実運用時のデプロイ手順（systemd / cron / Airflow のジョブ例）
- 品質チェック（quality モジュール）とアラート通知の設定例

追加希望があれば教えてください。