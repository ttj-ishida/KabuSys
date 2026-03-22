# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（ミニマム実装）。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、バックテスト、擬似約定シミュレータ、ニュース収集などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するライブラリ群です。主な目的は次の通りです。

- J-Quants API からの市場データ・財務データ取得と DuckDB への保存（冪等）
- ニュース（RSS）収集と銘柄紐付け
- 研究用ファクター計算（momentum / volatility / value）および特徴量エンジニアリング
- 戦略シグナルの生成（features + AI スコア統合）
- バックテストフレームワーク（擬似約定・ポートフォリオ管理・メトリクス）
- ETL パイプラインの補助機能、データ品質チェック（quality モジュールと連携）

設計方針としては「ルックアヘッドバイアス回避」「冪等性」「テスト可能性」「外部依存を最小化（標準ライブラリ優先）」を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - news_collector: RSS 取得・前処理・DB 保存（SSRF 対策・トラッキング除去）
  - schema: DuckDB スキーマ初期化（raw / processed / feature / execution 層）
  - stats: zscore_normalize など統計ユーティリティ
  - pipeline: 差分 ETL の補助、ETLResult 管理
- research/
  - factor_research: momentum / volatility / value 計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering.build_features: 生ファクターの正規化・合成 → features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して signals テーブルへ保存
- backtest/
  - engine.run_backtest: 日次ループでシグナル生成 → 擬似約定 → パフォーマンス算出
  - simulator.PortfolioSimulator: 擬似約定ルール（スリッページ・手数料）・MTM
  - metrics.calc_metrics: CAGR, Sharpe, MaxDD, Win rate 等の計算
  - run: CLI からバックテスト実行用エントリポイント
- execution/ monitoring/ （拡張ポイント）

---

## セットアップ手順

1. Python バージョン
   - Python 3.9+ 推奨（コードは型アノテーション等を使用）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - このリポジトリには requirements.txt が含まれている想定です:
     - pip install -r requirements.txt
   - 主な依存例:
     - duckdb
     - defusedxml
   - （あるいはプロジェクトの pyproject.toml / setup を参照してインストール）

4. 環境変数設定（.env）
   - プロジェクトルート（.git または pyproject.toml のある階層）に `.env` と `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - オプション / デフォルト
     - KABUSYS_ENV=development | paper_trading | live  (default: development)
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
     - conn.close()
   - メモリDB の場合:
     - conn = init_schema(":memory:")

---

## 使い方（主要なユースケース）

- DuckDB スキーマを初期化する（1回だけ）
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- J-Quants からデータを取得して保存（ETL の一部）
  - J-Quants の認証トークン設定後、jquants_client.fetch_* → save_* を呼ぶ例:
    - from kabusys.data import jquants_client as jq
    - records = jq.fetch_daily_quotes(date_from=..., date_to=...)
    - saved = jq.save_daily_quotes(conn, records)

- ニュース収集ジョブ（RSS を取得して raw_news に保存）
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)

- 特徴量作成（features テーブルの生成）
  - from kabusys.strategy import build_features
  - build_features(conn, target_date)  # DuckDB 接続と日付を渡す

- シグナル生成（features + ai_scores → signals）
  - from kabusys.strategy import generate_signals
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

- バックテスト（CLI）
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  - オプション: --cash, --slippage, --commission, --max-position-pct

- バックテスト（Python API）
  - from kabusys.backtest.engine import run_backtest
  - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  - result.history, result.trades, result.metrics を参照

- ETL パイプライン補助
  - kabusys.data.pipeline には差分取得のロジックや run_prices_etl などの関数があります（差分開始日自動計算・バックフィル対応）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
- LOG_LEVEL — ログレベル（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

.env はプロジェクトルートの `.env`、`.env.local` を順に読み込みます（OS 環境変数を上書きしないのがデフォルト）。詳細は kabusys.config モジュールを参照。

---

## 開発向け例（Python スニペット）

- スキーマ作成 & バックテスト実行（簡単な例）
  - from kabusys.data.schema import init_schema
  - from kabusys.backtest.engine import run_backtest
  - conn = init_schema("data/kabusys.duckdb")
  - result = run_backtest(conn, date(2023,1,4), date(2023,12,29))
  - print(result.metrics)
  - conn.close()

- 特徴量とシグナル生成（手動実行）
  - from kabusys.strategy import build_features, generate_signals
  - build_features(conn, target_date=date(2023,12,01))
  - generate_signals(conn, target_date=date(2023,12,01))

---

## ディレクトリ構成

以下は主要ファイルを含むディレクトリ構成（src 以下）です。実際のツリーは多少前後する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - metrics.py
    - simulator.py
    - clock.py
    - run.py
  - execution/
  - monitoring/
  - backtest/run.py (CLI entrypoint)

主要ロジックは上記各モジュールに分割されています。データベーススキーマは data/schema.py に定義されています。

---

## 注意事項 / 運用メモ

- J-Quants API のレート制限やトークン管理は jquants_client で考慮していますが、運用時は API 利用規約を遵守してください。
- features / signals / positions テーブルは日付単位で「置換（DELETE + INSERT）」する設計です（冪等性確保）。
- NewsCollector は RSS の XML パースに defusedxml を使用し SSRF / XML bomb 対策を施していますが、外部ソースの信頼性には注意してください。
- 本リポジトリは発注（execution）層と監視（monitoring）を分離する設計です。実際の発注は kabuステーション等の実装・設定に依存します。
- 本番環境での運用（live）は十分な検証とモニタリングを行ってから行ってください（paper_trading 環境での検証を推奨）。

---

何か特定の使い方（ETL の自動化、バックテストのカスタム設定、ニュース紐付けロジックの改変など）について詳しい例や補足が必要でしたら教えてください。README に追記して整備します。