# KabuSys

日本株自動売買システム（ライブラリ / 実行コンポーネント群）のリポジトリ。  
この README はコードベース（src/kabusys 以下）を元に作成しています。

## プロジェクト概要
KabuSys は以下の主要機能を持つ自動売買基盤のコンポーネント群です（トレード実行、監視、ポートフォリオ構築、リサーチ、AI を用いたニュース解析など）。  
- 実行エンジン（ExecutionEngine）による注文発行・状態管理・リスク管理
- 監視基盤（MonitoringEngine）によるプロセス・システム・注文・リスク監視と通知（LINE）
- ポートフォリオ構成/サイズ計算（等分配、スコア加重、リスクベース等）
- リサーチモジュール（ファクター計算、特徴量探索）
- AI モジュール（OpenAI を使ったニュースセンチメント、レジーム判定）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

## 主な機能一覧
- Execution
  - Broker クライアント層（本番 / モック切替）
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - Reconciler による再起動時の同期とポジション差分検出
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス生存確認、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視（kill.flag の発行）
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only 接続）
- Portfolio
  - 銘柄選定(select_candidates)、重み算出(calc_equal_weights / calc_score_weights)
  - ポジションサイズ計算(calc_position_sizes)、セクター制限、レジーム乗数
- Research
  - ファクター（Momentum / Volatility / Value）計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- AI
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄ごとにセンチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースで日次レジーム判定を行い market_regime に保存
- Utilities
  - process_priority: プラットフォーム依存を吸収したプロセス優先度／CPU affinity 設定
  - 環境変数ロード / Settings クラスによる一元管理

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして src を Python パッケージとしてインストールできるようにする（推奨は仮想環境）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```
2. 必要な依存パッケージをインストール（本リポジトリに requirements.txt がない場合、以下を参考にインストールしてください）
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
   - テスト/開発では追加パッケージが必要になる場合があります。
3. 環境変数（.env）を用意する  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は保護されます）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
4. 主要な環境変数の例（.env に記載）
   ```
   KABUSYS_ENV=development          # development | paper_trading | live
   SQLITE_PATH=data/monitoring.db  # 監視用 SQLite（monitoring）
   DUCKDB_PATH=data/kabusys.duckdb  # データ分析用 DuckDB
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  # paper_trading 時の専用 DB
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   LOG_LEVEL=INFO
   ```
   - `KABUSYS_ENV=paper_trading` の場合、ExecutionEngine は MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込みます。本番 DB と完全分離される設計です。

## 使い方（実行例）
- 監視ループ起動（monitoring）
  - デフォルトで production でも Settings.sqlite_path（data/monitoring.db）を使用して監視ログを保存します。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）。
  ```bash
  python -m kabusys.run_monitoring
  # または環境変数指定で
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 停止はプロジェクトルート `data/stop_requested.flag` を作成することで監視ループが検知して安全に停止します。

- 実行エンジン起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して paper_trading 用 DB（デフォルト data/paper_trading.db）へ記録します。
  - 実行中の強制停止は `data/stop_requested.flag` を作成することで検知され、Engine を停止します。
  - ExecutionEngine は起動時に `data/execution.pid` を作成します。

- Paper Trading 検証レポート（コマンドラインツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  - レポートは稼働率、注文成功率、送信率、レイテンシ等を計算して PASS/FAIL を表示します。

- Streamlit ダッシュボード（監視）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only 接続を試みます。監視エンジンが稼働していない場合は DB が存在しない旨を表示します。

- AI 関連（OpenAI）
  - news_nlp.score_news（DuckDB 接続を渡して呼び出す）
  - regime_detector.score_regime（DuckDB 接続を渡して呼び出す）
  - API キーは引数で渡すか、環境変数 `OPENAI_API_KEY` を利用
  - OpenAI へのリクエストはリトライ・バックオフ等のフェイルセーフ処理が入っていますが、API キー未設定時は例外になります。

## 設定（Settings）について
- 設定は `kabusys.config.Settings` クラスで環境変数から取得されます。主なプロパティ：
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須項目は未設定時に ValueError）
  - SQLITE_PATH（監視DB, default: data/monitoring.db）
  - DUCKDB_PATH（DuckDB, default: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, default: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH 等
  - PAPER_FILL_MODE（instant / partial / never / reject）
  - CPU/MEMORY/DISK 閾値など

- .env 読み込み
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出します。
  - 自動ロードの順序: OS 環境 > .env.local > .env
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

## 停止・キルフラグ
- 実行停止：
  - `data/stop_requested.flag`：run_monitoring / run_execution が監視しており、存在を検知すると安全に停止します（外部からの停止シグナル用）。
- Kill Switch（監視による強制停止）
  - リスク条件（ドローダウンやポジション上限）がトリガーされると `data/kill.flag` が書き込まれ、ExecutionEngine が停止対象として扱うことができます。
  - `kill.flag` はファイルとして書き込まれるため、解除はファイルを削除してください（例: rm data/kill.flag）。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/設定管理（Settings）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定、等重・スコア重み
    - position_sizing.py — 発注株数決定・上限・丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化レイヤ
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, ... — 注文関連の実装群
  - ai/
    - news_nlp.py — ニュースセンチメントスコア取得 (OpenAI)
    - regime_detector.py — レジーム判定（MA + マクロニュース + OpenAI）
  - research/
    - factor_research.py — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ (ランタイム生成想定)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb
    - execution.pid, stop_requested.flag, kill.flag

## 注意事項 / 運用メモ
- Paper Trading と本番データは明確に分離されます。KABUSYS_ENV=paper_trading のときは paper_sqlite_path を使用します。
- OpenAI API を利用する機能は外部ネットワークに依存します。API キーの管理と利用制限（レート）に注意してください。
- Monitoring は監視用 DB を常に使うため、監視コンポーネントの起動時は `init_monitoring_db()` によるテーブル作成を行います（冪等）。
- process_priority / set_cpu_affinity は OS 権限により動作しない場合があります（警告ログによりフォールバックします）。
- DuckDB を利用するリサーチ/AI モジュールは prices_daily / raw_financials / raw_news 等テーブルが整備されている前提です。

---

より詳細な設計やアルゴリズムの説明は各モジュールの docstring（src/kabusys 以下）に記載しています。必要に応じて各モジュールのドキュメント化（API リファレンス、設計ドキュメント）を追加してください。