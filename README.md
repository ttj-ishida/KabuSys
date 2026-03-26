# KabuSys

日本株向けの自動売買 / 研究フレームワーク（バックテスト・データ収集・特徴量／シグナル生成を含む）。  
このリポジトリは、J-Quants API や RSS ニュース等を用いたデータ取得、ファクター計算、シグナル生成、ポートフォリオ構築、バックテストを行うためのモジュール群を提供します。

---

## 概要

KabuSys は以下の機能を持つモジュール群で構成されています。

- J-Quants API からの株価・財務データ取得（レート制御・リトライ・トークン自動更新対応）
- RSS ニュース収集と記事 → 銘柄紐付け（SSRF 対策・トラッキング除去）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量の正規化・保存（features テーブル）
- シグナル生成（AI スコア統合、ベア相場抑制、エグジット判定）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・セクター制限）
- バックテストエンジン（擬似約定・ポートフォリオシミュレータ・メトリクス）
- 各種ユーティリティ（DB スキーマ初期化、マーケットカレンダー管理 等）

設計上のポイント：
- できるだけ DB 参照を限定した純粋関数を使い、バックテストループは再現性を担保
- Look-ahead バイアスを避けるため「target_date 時点で利用可能なデータのみ」を原則
- DuckDB を中心としたデータ格納（ローカルファイル or in-memory）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レートリミット・トークン自動更新）
  - news_collector: RSS 収集、記事正規化、raw_news 保存、銘柄抽出
- research/
  - factor_research: momentum / volatility / value の計算
  - feature_exploration: IC 計算、将来リターン、統計サマリ
- strategy/
  - feature_engineering: 生ファクターの正規化・features への upsert
  - signal_generator: final_score 計算、BUY/SELL シグナル生成、signals への upsert
- portfolio/
  - portfolio_builder: 候補選定・重み計算
  - position_sizing: 発注株数計算（risk_based / equal / score）
  - risk_adjustment: セクターキャップ・レジーム乗数
- backtest/
  - engine: バックテストのメインループ（データのコピー / シグナル生成 / 発注ロジック）
  - simulator: 擬似約定とポートフォリオ管理
  - metrics: バックテスト評価指標の計算
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- その他
  - config: 環境変数・.env 自動ロードと Settings API
  - data.schema（スキーマ初期化；init_schema を使用）

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - defusedxml
  - そのほか依存パッケージ（requests 等は本コードで urllib を使用しているため不要な場合あり）
- J-Quants API のリフレッシュトークン等サービスアカウント情報

実際のインストールはプロジェクトの pyproject.toml / requirements.txt を参照してください（本 README はコードベースから主要パッケージを想定）。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成
   - git clone <repo>
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - pip install -e .   （プロジェクトを編集可能モードでインストールできる場合）

3. 環境変数（.env）の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（読み込み順: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

   主要な環境変数（必須は明記）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
   - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
   - KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

4. DuckDB スキーマの初期化
   - 本ライブラリでは schema 初期化用に init_schema 関数を提供している想定です（kabusys.data.schema.init_schema）。
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - バックテストに必要なテーブル群（例）
     - prices_daily / raw_prices / raw_financials / features / ai_scores / signals / positions / market_regime / market_calendar / stocks / raw_news / news_symbols など

   ※ 実運用ではデータ取得（J-Quants）→ save_* 関数で raw_xxx を埋め、ETL を回して features・ai_scores 等を用意してください。

---

## 使い方

### バックテスト（CLI）

DuckDB に必要なデータ（prices_daily, features, ai_scores, market_regime, market_calendar 等）が揃っている前提で実行します。

例:
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb \
  --allocation-method risk_based \
  --lot-size 100

主なオプション:
- --start / --end : バックテスト期間（YYYY-MM-DD）
- --cash : 初期資金（円）
- --db : DuckDB ファイルパス
- --allocation-method : equal | score | risk_based
- --slippage / --commission : スリッページ・手数料率
- --max-positions / --max-utilization / --risk-pct / --stop-loss-pct / --lot-size 等

実行後、標準出力に主要なメトリクス（CAGR, Sharpe, Max Drawdown 等）を表示します。

---

### ライブラリ API（一例）

- バックテストエンジンをプログラム的に呼ぶ
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  conn.close()

- 特徴量構築（features の upsert）
  from kabusys.strategy.feature_engineering import build_features
  # conn: DuckDB 接続
  count = build_features(conn, target_date)

- シグナル生成
  from kabusys.strategy.signal_generator import generate_signals
  total = generate_signals(conn, target_date)

- News 収集 & 保存
  from kabusys.data.news_collector import run_news_collection
  stats = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  # stats はソースごとの新規挿入数を返す

- J-Quants からのデータ取得
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  data = fetch_daily_quotes(date_from=..., date_to=...)
  saved = save_daily_quotes(conn, data)

各関数はドキュメントストリング（コード内コメント）で利用上の注意や引数仕様が明確に記載されています。特にシグナル生成・ポジションサイジングは多くのハイパーパラメータ（threshold, weights, risk_pct 等）を受け取りますのでドキュメントを参照してください。

---

## 注意事項 / 運用メモ

- Look-ahead バイアスに注意：
  - 各処理は target_date 時点で利用可能なデータのみを使う設計ですが、実運用パイプラインではデータ取得日時（fetched_at）や market_calendar の扱いに注意してください。
- .env 自動読み込み：
  - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に .env を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env を上書きする）
- バックテスト用 DB 構築：
  - run_backtest は本番 DB を直接変更しないために in-memory DuckDB に必要なテーブルをコピーして実行しますが、元の DB に features / ai_scores / market_regime 等の前処理済みデータが必要です。
- 単元株（lot）：
  - 日本株では通常 100 株単位。position_sizing/PortfolioSimulator に lot_size パラメータがあり丸め処理が入ります。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - jquants_client.py
  - news_collector.py
  - (schema.py 等が存在する想定)
- research/
  - factor_research.py
  - feature_exploration.py
- strategy/
  - feature_engineering.py
  - signal_generator.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- backtest/
  - engine.py
  - simulator.py
  - metrics.py
  - run.py
  - clock.py
- execution/  (パッケージ化されているが実装ファイルはここでは省略)
- monitoring/ (パッケージ化されているが実装詳細は省略)

（上記は本リポジトリに含まれる主要モジュールとその役割を簡潔に示しています。実際のファイルは src/kabusys 以下を参照してください。）

---

## 開発・貢献

- コードはドキュメントストリングとコメントを多用しているため、新しい指標やアルゴリズムを追加する際は既存の設計原則（ルックアヘッド回避、DB 参照の最小化、冪等性）に従ってください。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存の副作用を避けることを推奨します。

---

README はここまでです。必要であれば以下の情報も追加できます：
- .env.example のサンプル
- DB スキーマ（テーブル定義）
- CI / 開発用テストコマンド例
- 実運用（paper/live）向けの注意点（Slack 通知フロー、kabuAPI 連携方法など）