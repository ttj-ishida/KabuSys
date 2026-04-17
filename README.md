# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。  
このリポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントを含みます。

---

## 概要

- 実運用を想定したモジュール設計（Execution / Monitoring / Portfolio / Research / AI）。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数 `KABUSYS_ENV` で切り替え可能。
- SQLite（監視ログ等）と DuckDB（分析用）を使用。
- OpenAI を利用したニュースNLP / レジーム判定機能を実装（APIキーを環境変数で指定）。
- .env ベースの設定ウィザード、起動前設定検証ツールを提供。

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して注文処理を行う（本番は実際発注、paper_trading では MockBrokerClient を使用して専用DBへ記録）。
  - リスク管理（RiskManager）、注文管理（OrderManager / OrderRepository）、整合処理（Reconciler）などを内包。

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス状態・データ鮮度を監視しログへ記録。
  - TradeMonitor: 滞留注文・約定異常価格を検出してリスクログを記録。
  - RiskMonitor: ドローダウン・ポジション上限の監視と kill switch トリガー。
  - MonitoringEngine: 上記モニタを束ねてポーリング実行、必要に応じてアラート・kill.flag 書込み。

- Portfolio construction
  - 候補選定・重み付け（等金額 / スコア加重）、セクター制限、ポジションサイズ計算（lot 整数化・集約キャップ適用）を提供。

- Research
  - ファクター計算（Momentum / Volatility / Value）や将来リターン計算、IC（Information Coefficient）などの分析ユーティリティ（DuckDB を利用）。

- AI
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント算出・ai_scores への書き込み。
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースセンチメントを合成して市況レジーム判定を行い DB へ書き込み。

- ツール
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
2. 必要なパッケージをインストール
   - 主要依存: duckdb, psutil, openai
   - 任意: PyYAML（config YAML 検証のため）
   - 例:
     pip install -r requirements.txt
     （requirements.txt が無い場合は上のパッケージ群を個別にインストール）

3. .env の作成（対話式ウィザード推奨）
   - ウィザードを実行:
     python -m kabusys.config_setup
   - デフォルト値の例（.env に保存される主なキー・デフォルト）:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=（必須）
     - KABU_API_PASSWORD=（必須）
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

4. 設定検証（起動前に必ず実施推奨）
   - 基本実行:
     python -m kabusys.validate_config
   - 警告も失敗扱いにする（厳密モード）:
     python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / flag は `data/` 下を使用します。自動的に作成される場合もありますが、権限等に注意してください。

6. OpenAI を使う機能を利用する場合
   - 環境変数 `OPENAI_API_KEY` を設定してください（news_nlp / regime_detector の API 呼び出しで使用）。
   - API の利用はコスト発生・レート制限に注意。

---

## 使い方

- 実行エンジン起動（Execution）
  - 通常起動:
    python -m kabusys.run_execution
  - ペーパートレード（KABUSYS_ENV=paper_trading）では MockBroker を利用し、データは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH で上書き可）へ記録されます。
  - 実行時は `data/execution.pid`（デフォルト）に PID が書き込まれます。停止は `data/stop_requested.flag` を作成するか kill.flag により外部から停止トリガーされる場合があります。

- 監視プロセス起動（Monitoring）
  - 起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルトは 60 秒。
  - 監視は常にプロダクションの sqlite_path を参照します（KABUSYS_ENV に依存しない監視ログ）。

- Paper Trading 検証レポート
  - 実行:
    python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可能。

- 環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 db、デフォルト: data/paper_trading.db)
  - OPENAI_API_KEY (news_nlp / regime_detector)
  - LOG_LEVEL (DEBUG/INFO/...)
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔 秒、デフォルト: 60)
  - PAPER_FILL_MODE (paper_trading の MockBroker の fill 動作: instant | partial | never | reject)
  - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)

- Kill Switch / フラグファイル
  - kill.flag（デフォルト: data/kill.flag）: KillSwitch により作成されると ExecutionEngine の停止を促します。
  - stop_requested.flag（data/stop_requested.flag）: run_monitoring / run_execution の停止トリガーに使用。

- 設定の自動読み込み
  - ランタイム起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。必要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — .env 読み込みと Settings
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/              — Execution 関連モジュール（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py

（詳細はコードベースを参照してください）

---

## 注意事項 / 運用上のメモ

- 本番環境（KABUSYS_ENV=live）では LINE 通知などの設定が正しく行われていることを十分に確認してください（validate_config は live 環境向けの注意喚起を行います）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup も README に注記しています）。
- OpenAI API 呼び出しを行うモジュールは外部APIの失敗に対してフェイルセーフ機構（リトライ・フォールバック）を持ちますが、API 利用料・レート制限には注意してください。
- run_execution / run_monitoring は stop_requested.flag / stop フラグファイルを見てシャットダウンします。自動化スクリプトからはフラグファイルの作成で制御できます。

---

この README はコードベースの主要機能と運用手順を概説したものです。実際の運用前に `python -m kabusys.validate_config` を実行して設定を検証してください。追加のドキュメント（例えば PortfolioConstruction.md や StrategyModel.md）がある場合はそれらも参照してください。