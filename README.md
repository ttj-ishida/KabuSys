# KabuSys — 日本株自動売買システム

簡潔な説明:
KabuSys は日本株向けのデータパイプライン、特徴量生成、シグナル生成、ニュース収集、監査/実行層のスキーマを備えた自動売買（バックテスト/運用支援）向けのライブラリ群です。DuckDB をデータ層に使い、J-Quants API など外部データソースから差分取得・保存し、戦略向けの特徴量や売買シグナルを生成します。

---

目次
- プロジェクト概要
- 主な機能一覧
- 要件
- セットアップ手順
- 環境変数（.env）
- 使い方（例）
- ディレクトリ構成（主要ファイル説明）
- 補足・運用上の注意

---

## プロジェクト概要

このライブラリは以下の役割を持ちます。

- J-Quants 等の API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- raw → processed → feature → execution の多層データスキーマ（冪等性・監査対応）
- 研究用のファクター計算（Momentum / Volatility / Value 等）と特徴量正規化
- 特徴量と AI スコアを統合した売買シグナル生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- 市場カレンダー管理・営業日判定ロジック
- 発注 / 監査ログ用のスキーマ（監査性の担保）

設計思想としては、
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等性（DB への INSERT は ON CONFLICT 等で重複を防止）
- 外部 API 呼び出しは data 層に限定、strategy 層は発注層へ直接依存しない
が採用されています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants から日足・財務情報・市場カレンダーを差分取得（ページネーション・レート制限・再試行ロジック）
  - raw_prices / raw_financials / market_calendar 等へ冪等保存

- ETL パイプライン
  - 日次差分 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック

- スキーマ管理
  - DuckDB のスキーマ初期化（init_schema）: raw / processed / feature / execution 層を作成

- 研究（research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - ファクター探索: calc_forward_returns, calc_ic, factor_summary, rank
  - Z スコア正規化ユーティリティ

- 戦略（strategy）
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）: final_score 計算・BUY/SELL 出力・signals テーブル格納

- ニュース収集
  - RSS 取得、正規化、raw_news 保存、銘柄抽出と news_symbols への紐付け

- カレンダー管理
  - 営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job

- 監査（audit）
  - シグナル→発注→約定を UUID で連鎖しトレース可能にするテーブル群

---

## 要件

- Python 3.10 以上（型ヒントに | を使用）
- 必要なパッケージ（最低限）:
  - duckdb
  - defusedxml

（pip 用例は下記）

---

## セットアップ手順

1. リポジトリをクローン／取得
   - 例: git clone <リポジトリURL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトがパッケージ化済みの場合）pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（詳細は下段参照）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - :memory: を渡せばインメモリ DB を使えます（テスト用途）。

---

## 環境変数（.env）

自動読み込みの優先順位: OS 環境変数 > .env.local > .env
自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主に利用される変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（execution 層で利用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（必要に応じて）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live"), デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", ...)

設定取得は kabusys.config.settings を通じて行うことができます。

---

## 使い方（主要な操作例）

以下は Python スクリプトや REPL での利用例です。

- DuckDB スキーマ初期化（初回のみ）

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 既存 DB へ接続（スキーマ初期化済み）

  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants から差分取得して保存）

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量（features）構築

  from datetime import date
  from kabusys.strategy import build_features
  n = build_features(conn, target_date=date(2025, 1, 31))
  print(f"features upserted: {n}")

- シグナル生成

  from datetime import date
  from kabusys.strategy import generate_signals
  n_signals = generate_signals(conn, target_date=date(2025, 1, 31))
  print(f"signals written: {n_signals}")

  - カスタム重みや閾値を与えることもできます:
    generate_signals(conn, target_date, threshold=0.65, weights={"momentum":0.5, "value":0.2, ...})

- ニュース収集ジョブ

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)

- カレンダー更新ジョブ（夜間バッチ想定）

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- 監査／発注関連は data.audit のスキーマと API を参照してください。

---

## 品質チェック・ユーティリティ

ETL 実行後に品質チェックモジュール（quality）を呼び出して欠損・スパイク等を検出できます（pipeline.run_daily_etl はデフォルトで品質チェックを実行します）。品質問題は ETL の致命エラーに直結せず、検出結果は ETLResult.quality_issues に集約されます。

---

## ディレクトリ構成（主要ファイルの説明）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージメタ（__version__ 等）とエクスポート定義

- config.py
  - .env / 環境変数の読み込みと Settings クラス（settings）を提供

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（認証・ページング・レート制御・保存関数）
  - news_collector.py — RSS ベースのニュース収集・前処理・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - calendar_management.py — market_calendar 管理（営業日判定・更新ジョブ）
  - audit.py — 監査ログ用の DDL / 初期化補助（監査関連テーブル）
  - features.py — zscore_normalize の再エクスポート

- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank（研究用）

- strategy/
  - __init__.py — build_features / generate_signals をエクスポート
  - feature_engineering.py — 研究で計算した raw factor を統合・正規化して features テーブルへ保存
  - signal_generator.py — features と ai_scores を統合して final_score を計算、signals テーブルへ書き込む

- execution/
  - （現時点ではパッケージのみ。ただし発注層実装を想定したスキーマが schema.py に定義されています）

---

## 補足・運用上の注意

- 環境分離
  - KABUSYS_ENV により is_live / is_paper / is_dev のフラグが取得できます。実運用時は設定に注意してください。

- シークレット管理
  - J-Quants や Slack 等のトークンは .env に保存するか安全なシークレットストアを利用してください。Settings._require は未設定時に ValueError を投げます。

- 冪等性
  - API から取得したデータは save_* 関数で ON CONFLICT を使って冪等保存されます。重複挿入対策不要ですが、初期化やスキーマ変更時は注意してください。

- テスト
  - 各モジュールは id_token の注入や _urlopen のモックを想定しており、テスト可能な設計です。
  - 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 依存ライブラリ
  - ネットワークアクセスは urllib を用いて実装されています。HTTP/HTTPS のみを許可し、RSS 収集では SSRF 対策を実施しています。
  - defusedxml を利用して XML パースのセキュリティ対策を行っています。

---

この README はコードベース（src/kabusys 以下）を元に作成しています。実際の運用や拡張時は StrategyModel.md / DataPlatform.md / DataSchema.md 等の設計ドキュメントを参照して下さい。必要であれば README.md に実行スクリプト例や CI/CD 設定、より詳細な環境変数一覧（.env.example）を追加します。必要な場合は指示ください。