# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants からの市場データ収集、DuckDB によるデータ保管・前処理、ファクター計算、特徴量生成、シグナル生成、RSS ベースのニュース収集、マーケットカレンダー管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（主要 API 例）
- 環境変数（設定）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の自動売買システムに必要な以下の機能群をモジュール化した Python ライブラリです。

- J-Quants API クライアント（データ取得・リトライ・レート制御・トークン自動更新）
- DuckDB によるデータスキーマ（Raw / Processed / Feature / Execution 層）と初期化
- ETL パイプライン（差分取得・保存・品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブル書き込み）
- シグナル生成（features + ai_scores を統合して BUY/SELL を生成）
- ニュース収集（RSS 取得・前処理・記事保存・銘柄抽出）
- マーケットカレンダー管理（営業日判定・次/前営業日取得・夜間更新ジョブ）
- 監査ログ（発注〜約定のトレース用テーブル群）

設計方針として「ルックアヘッドバイアスの排除」「冪等性（ON CONFLICT）」「外部 API をラップして安全に扱う（SSRF/サイズ制限等）」が組み込まれています。

---

## 主な機能一覧
- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レート制限・再試行・トークン自動刷新
- data.schema
  - DuckDB テーブル定義・初期化（init_schema / get_connection）
- data.pipeline
  - 日次 ETL 実行（run_daily_etl）、個別ジョブ（run_prices_etl 等）
- data.news_collector
  - RSS 取得（fetch_rss）、raw_news への保存、銘柄抽出、統合実行（run_news_collection）
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
- research.factor_research
  - calc_momentum / calc_volatility / calc_value
- research.feature_exploration
  - calc_forward_returns / calc_ic / factor_summary / rank
- strategy.feature_engineering
  - build_features（Z スコア正規化・ユニバースフィルタ・features テーブル UPSERT）
- strategy.signal_generator
  - generate_signals（final_score 計算・BUY/SELL 生成・signals テーブル UPSERT）
- data.stats
  - zscore_normalize（クロスセクション Z スコア）

---

## セットアップ手順

1. Python と仮想環境を用意
   - Python 3.9+ を推奨（実装は typing の新記法などを含むため）
   - 仮想環境（venv / pyenv / conda 等）を作成・有効化

2. パッケージ依存のインストール
   - 必須: duckdb
   - 追加（RSS XML パースに安全な実装を使うため）: defusedxml
   - 例:
     - pip を使う場合:
       pip install duckdb defusedxml

   - （開発用）ローカルパッケージとして使う場合:
     - プロジェクトルートに移動して:
       pip install -e .

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成することで自動読み込みされます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB データベース初期化
   - Python REPL やスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定するとインメモリ DB を使用できます（テスト用途）。

---

## 簡単な使い方（主要 API 例）

- 環境変数の読み取り（設定アクセス）
  from kabusys.config import settings
  token = settings.jquants_refresh_token

- スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants からの差分取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 特徴量構築（features テーブルに書き込む）
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date(2024, 1, 31))
  print(f"features upserted: {count}")

- シグナル生成（features / ai_scores / positions を参照して signals を更新）
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 31))
  print(f"signals written: {total}")

- ニュース収集ジョブ（RSS 取得→保存→銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # 適宜銘柄コードセットを用意
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- J-Quants の直接利用例（トークン取得・fetch）
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  idt = get_id_token()
  quotes = fetch_daily_quotes(id_token=idt, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意: これらの関数は DuckDB の接続を受け取り、テーブルの存在を前提に動作する部分があります。初回は init_schema() を実行してください。

---

## 環境変数（設定）
Settings モジュールで参照される主要な環境変数は以下です。

必須（アプリ稼働に必須）:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン。get_id_token の元になります。
- KABU_API_PASSWORD
  - kabuステーション API（発注）用のパスワード
- SLACK_BOT_TOKEN
  - Slack 通知用 Bot トークン（必要な場合）
- SLACK_CHANNEL_ID
  - Slack 送信先チャンネル ID

オプション / デフォルトあり:
- KABUSYS_ENV
  - 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env 自動ロードを無効化

.env ファイルのパースはシェルライクな簡易パーサを実装しており、`export KEY=val`、シングル/ダブルクォート、行末コメントなどに対応します。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主要モジュールとその概要です。

- src/kabusys/__init__.py
  - パッケージ定義、公開モジュール群

- src/kabusys/config.py
  - 環境変数 / 設定管理（.env 自動ロード、Settings クラス）

- src/kabusys/data/
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py
    - RSS ニュース取得・前処理・保存・銘柄抽出
  - schema.py
    - DuckDB スキーマ定義と init_schema/get_connection
  - stats.py
    - 汎用統計ユーティリティ（zscore_normalize 等）
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）
  - calendar_management.py
    - マーケットカレンダー管理（営業日判定・更新ジョブ）
  - audit.py
    - 発注〜約定の監査ログ（signal_events, order_requests, executions 等）

- src/kabusys/research/
  - factor_research.py
    - モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py
    - 将来リターン計算・IC・統計サマリー
  - __init__.py
    - re-export（研究用ユーティリティ）

- src/kabusys/strategy/
  - feature_engineering.py
    - 生ファクターを正規化・合成して features テーブルへ保存
  - signal_generator.py
    - features + ai_scores から final_score を計算し signals を出力
  - __init__.py
    - build_features / generate_signals を公開

- src/kabusys/execution/
  - （発注実行関連のコードを配置するためのパッケージ / 今回は空 __init__）

---

## 運用上の注意
- データの冪等性: save_* 関数や schema の DDL は冪等性を考慮して作られています。複数回実行しても重複データが残らないよう ON CONFLICT 等で制御しています。
- ルックアヘッドバイアス対策: ファクター計算やシグナル生成は target_date 時点までのデータのみを使用するよう設計されています。
- ネットワーク安全: RSS 取得は SSRF を防ぐためスキーム検査・ホスト判定・最大レスポンスサイズ制限・Gzip 解凍サイズチェックを行います。
- J-Quants API のレート制限: 内部で固定間隔スロットリングを行っています（120 req/min の想定）。
- テスト: id_token 注入・HTTP 呼び出しの差し替えが可能な設計になっているのでユニットテストやモックによる検証が容易です。

---

## 例: 開発ワークフロー（概略）
1. DuckDB スキーマ初期化:
   conn = init_schema("data/kabusys.duckdb")

2. カレンダー更新（夜間ジョブ）:
   calendar_update_job(conn)

3. 日次 ETL（市場データの差分取得）:
   result = run_daily_etl(conn)

4. 研究環境でファクターを確認 / 調整:
   from kabusys.research import calc_momentum, calc_volatility
   mom = calc_momentum(conn, date(2024,1,31))

5. 特徴量構築 & シグナル生成:
   build_features(conn, date(2024,1,31))
   generate_signals(conn, date(2024,1,31))

6. 必要に応じて execution 層で発注処理を実装・接続

---

もし README に追記したい実行スクリプトのテンプレート、`.env.example` の具体例、あるいは CI / デプロイ手順（Dockerfile / systemd ジョブ等）を追加したい場合は、必要な情報（環境、運用要件）を教えてください。