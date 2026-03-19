# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants API 等から市場データ・財務データ・ニュースを取得して ETL → 特徴量生成 → 研究 / 戦略 実行までを想定したユーティリティを提供します。

## 主な特徴
- データ取得
  - J-Quants API クライアント（株価日足・財務データ・マーケットカレンダー）
  - RSS ベースのニュース収集（トラッキングパラメータ除去・SSRF 対策・gzip 対応）
- ETL / データ品質管理
  - 差分取得／バックフィル対応 ETL（市場カレンダー・株価・財務）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- スキーマ管理
  - DuckDB 用のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 研究支援（Research）
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z-score 正規化ユーティリティ
- 実行・監査基盤（設計されているが実装はモジュール構成に依存）
  - 発注・実行・監査用スキーマとユーティリティ群（audit / execution 等）

## サポート環境
- Python 3.10+
- 必要主要ライブラリ（例）
  - duckdb
  - defusedxml
（環境に応じて requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン、あるいはパッケージをインストール
   - 開発時（editable インストール想定）
     - python -m pip install -e .
2. 必要な依存パッケージをインストール
   - pip install duckdb defusedxml
   - その他プロジェクトで必要なパッケージがあれば追加でインストールしてください
3. 環境変数（.env）を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（config.Settings を参照）
     - JQUANTS_REFRESH_TOKEN  -- J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      -- kabuステーション API のパスワード
     - SLACK_BOT_TOKEN        -- Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID       -- Slack の投稿先チャンネル ID
   - 任意／デフォルト
     - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH / SQLITE_PATH — データベースファイルパス（デフォルト: data/kabusys.duckdb, data/monitoring.db）
4. DuckDB スキーマ初期化
   - Python から以下を実行して DB ファイルとテーブルを作成します（親ディレクトリがなければ自動作成）。
     - from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")

---

## 使い方（代表的な例）

以下はライブラリの代表的な利用例です。実行前に必ず環境変数と DuckDB の初期化を済ませてください。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（J-Quants から差分取得し保存・品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

- ニュース収集（RSS）ジョブ
  - from kabusys.data.news_collector import run_news_collection
    # known_codes: 銘柄コードセット（抽出用）
    res = run_news_collection(conn, known_codes={"7203", "6758", "9984"})
    print(res)

- J-Quants から直接データ取得・保存
  - from kabusys.data import jquants_client as jq
    records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    jq.save_daily_quotes(conn, records)

- 研究用ファクター計算 / 評価
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
    m = calc_momentum(conn, date(2025,1,31))
    fwd = calc_forward_returns(conn, date(2025,1,31))
    ic = calc_ic(m, fwd, factor_col="mom_1m", return_col="fwd_1d")
    summary = factor_summary(m, ["mom_1m", "mom_3m", "ma200_dev"])
    znorm = zscore_normalize(m, ["mom_1m", "ma200_dev"])

注意点:
- J-Quants API 周りはレート制限やリトライ・トークン自動更新を内蔵していますが、実行前に JQUANTS_REFRESH_TOKEN を設定してください。
- ニュース収集は外部リクエストを行います。RSS のスキームは http/https のみ許可されています。

---

## 主要モジュール概要（機能一覧）
- kabusys.config
  - .env および環境変数管理、自動ロード（.env, .env.local）
  - Settings クラス: アプリ設定の集中管理
- kabusys.data.jquants_client
  - J-Quants API クライアント（取得・保存ユーティリティ）
  - レートリミット、リトライ、トークン更新ロジックを内包
- kabusys.data.news_collector
  - RSS 取得、テキスト前処理、DuckDB への冪等保存、銘柄抽出
  - SSRF 対策・XML 抜け攻撃対策（defusedxml）
- kabusys.data.schema
  - DuckDB スキーマ定義と init_schema
  - Raw / Processed / Feature / Execution / Audit 層のテーブルを作成
- kabusys.data.pipeline
  - ETL パイプライン（差分取得・保存・品質チェック）
  - run_daily_etl を中心としたワークフロー
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合チェック
  - QualityIssue を返すことで呼び出し元での対処を容易にする
- kabusys.data.calendar_management
  - 市場カレンダー管理（営業日判定・prev/next 営業日・更新ジョブ）
- kabusys.research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）用DDL と初期化
- kabusys.execution, kabusys.strategy, kabusys.monitoring
  - 発注・戦略・監視関連モジュールの名前空間（詳細は各実装に依存）

---

## ディレクトリ構成

（主要ファイルを抜粋）

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
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - etl.py
      - quality.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py

各モジュールは概ね責務ごとに整理されており、data/* がデータ取得・保存・品質・スキーマ、research/* が分析・ファクター計算を担います。

---

## 環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読込を無効化

.env の読み込みルール:
- OS 環境変数 > .env.local > .env の順で適用
- .env のパースはシェル風（export KEY=val、クォート、コメント）に対応

---

## 開発・運用上の注意
- DuckDB に対する DDL 実行は冪等（IF NOT EXISTS）で記述されていますが、監査スキーマなど一部は transactional フラグに注意して初期化してください。
- J-Quants API のレート制限（120 req/min）を遵守する仕組みが組み込まれていますが、大量同時要求などの運用は避けてください。
- ニュース収集時の外部アクセスには SSRF / XML BOM / Gzip Bomb 等への防御ロジックがあります。テスト時はネットワーク呼び出しを適切にモックしてください。
- research モジュールは外部ライブラリに依存しない実装（標準ライブラリ + duckdb）を心掛けています。大量データ処理では DuckDB クエリ最適化を検討してください。

---

必要であれば README に含めるサンプル .env.example や CI / デプロイ手順、より具体的な API 使用例（kabu ステーション発注フローや Slack 通知の実装例）も追記します。どの情報を優先して追加しましょうか？