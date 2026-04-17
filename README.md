# KabuSys

日本株向け自動売買システムのコアライブラリ群および運用用スクリプト群。  
本リポジトリはトレード実行、監視、ポートフォリオ構築、リサーチ、LLM ベースのニュース解析などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は以下の機能を備えたモジュール型の自動売買基盤です。

- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード切替対応）
- 監視サブシステム（System / Trade / Risk Monitor）と Kill Switch による安全停止
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制約）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）と特徴量解析ツール
- OpenAI を使ったニュース NLP によるセンチメント評価・市場レジーム判定
- 運用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗は局所的フォールバック）」を重視しています。

---

## 主な機能一覧

- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper_trading モード対応）
  - BrokerClientFactory 経由で本番ブローカー / MockBroker を切替

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB: SQLite ベースの監視ログ永続化（schema/migration 自動化）
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine に停止シグナルを送信

- ポートフォリオ
  - 銘柄選定（select_candidates）
  - 重み計算（等分配 / スコア重み）
  - ポジションサイズ決定（risk_based / equal / score）
  - セクターキャップ / レジーム乗数

- リサーチ
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン、IC 計算、統計サマリー

- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime: MA とマクロニュースの LLM 評価を合成して market_regime に保存

- ツール
  - config_setup.py: .env 作成・更新の対話式ウィザード
  - validate_config.py: 環境変数 / config/*.yaml の起動前検証 CLI
  - tools/paper_verification_report.py: ペーパートレード DB を用いた検証レポート生成

---

## セットアップ手順（ローカル開発用）

前提: Python 3.9+ を想定（duckdb / psutil / openai 等が必要）。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml

   ※ requirements.txt があればそれを利用してください。

4. .env ファイル作成（対話式ウィザードを推奨）
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリ（デフォルト）:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper trading DB: data/paper_trading.db

   環境変数で上書きできます（下記参照）。

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用 / 設定
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 時）
  - LOG_LEVEL: DEBUG/INFO/...
  - OPENAI_API_KEY: OpenAI を使う機能で必要

- 監視制御
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_PATH: KillSwitch が書き込む flag（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効、デフォルト 0）
  - PID_FILE_PATH: ExecutionEngine の pid ファイルパス（デフォルト data/execution.pid）

- 自動 .env 読み込み
  - .env / .env.local は Settings モジュールで自動読み込みされます（プロジェクトルートが検出可能な場合）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

## 使い方（主要コマンド）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（本番/ペーパーは KABUSYS_ENV で切替）
  - python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 実行中は data/execution.pid に PID を書込。停止は data/stop_requested.flag や kill.flag による。

- 監視起動
  - python -m kabusys.run_monitoring

  挙動:
  - MONITOR_POLL_INTERVAL で指定した間隔で SystemMonitor.check_once() を呼び出します（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（環境に関係なく本番監視 DB に書き込む実装）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で PAPER_TRADING_SQLITE_PATH を上書き可能。

- AI 関連（スクリプトや REPL から呼び出し）
  - ニューススコアリング（例: Python REPL）
    - from datetime import date
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")

  注意: OPENAI_API_KEY を環境変数に設定しておくと api_key 引数は不要です。

---

## 運用上の注意 / 実装上の特徴

- 起動時にプロセス優先度を high に設定する試みが行われます（set_process_priority）。権限不足などで失敗した場合は警告でスキップされます。
- run_execution / run_monitoring は data/stop_requested.flag の検出でループを終了します（運用時の安全停止）。
- KillSwitch はリスクルール（ドローダウン・ポジション上限）に基づき data/kill.flag を書き込み、ExecutionEngine が検知して停止する仕組みです。
- Paper trading は本番 DB と完全分離するように設計されています（データが混ざらないよう配慮）。
- 設定検証ツールは PyYAML がない場合に YAML ファイル検証をスキップします（警告表示）。
- MonitoringDB.init_monitoring_db は既存 DB に対する軽微なマイグレーション（カラム追加など）を行います。

---

## ディレクトリ構成

主要ファイル・ディレクトリの一覧（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py              — 環境変数・.env の読み込み・Settings
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP スコアリング
    - regime_detector.py    — 市場レジーム判定
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ & MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py      — （注: 末尾の実装ファイルがまだ続く場合あり）
    - monitoring_engine.py
  - execution/              — Execution 系（OrderManager, Reconciler 等: 実装省略箇所あり）
  - data/                   — データ処理パイプライン（prices_daily など、別モジュール）
  - utils/
    - __init__.py
    - process_priority.py   — process priority / CPU affinity ユーティリティ

データファイル（デフォルト位置）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag

---

## 追加情報 / トラブルシューティング

- .env をコミットしないでください（機密情報が含まれます）。
- KABUSYS_ENV=live を設定する場合は LINE 通知設定や kill フラグ設定等を慎重に確認してください（validate_config で警告が出ます）。
- OpenAI を使う機能は API 呼び出しの失敗をフェイルセーフ（0.0 などのフォールバック）で扱いますが、APIキー未設定時は呼び出し側で ValueError が発生します。
- MONITOR_POLL_INTERVAL に 0 や負の値を設定するとデフォルト（60 秒）にフォールバックされます。

---

この README はコードベースの関数・スクリプトを元に作成しています。実際の運用では環境変数、DB パス、外部 API キーの設定を確認の上で起動してください。必要があれば導入手順や各モジュールの詳細ドキュメントを別途作成します。