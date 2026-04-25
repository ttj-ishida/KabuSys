# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注（実行エンジン）・監視・研究（DuckDBベースのファクター計算）・AIを用いたニュース解析などを含む自動売買システムのコア実装を含みます。

---

## プロジェクト概要

- DuckDB / SQLite をデータ層に用い、価格データや財務データ、ログ等を保持します。
- ExecutionEngine（発注エンジン）と Monitoring（監視）を別プロセスで運用できる構成。
- Paper Trading モードをサポートし、本番DBと分離された専用 SQLite に記録可能。
- ニュースセンチメント分析や市場レジーム判定のために OpenAI API を利用するモジュールを含む（オプション）。
- ログはコンソール出力 + 日次ローテートファイル（logs/*.log）で管理。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成支援）：kabusys.config_setup
- 設定ファイル検証 CLI（.env、config/*.yaml のチェック）：kabusys.validate_config
- 発注エンジン起動スクリプト：run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB に記録
  - プロセス優先度を高に設定し PID ファイルを出力
  - stop_requested.flag により安全に停止可能
- 監視ループ起動スクリプト：run_monitoring.py
  - システム状態、注文ログ、リスク（ドローダウン・ポジション数）などを定期チェック
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
  - 監視用 DB は環境にかかわらず本番 sqlite_path を使用
- 監視永続化層（MonitoringDB）：SQLite テーブル群（system_status, trade_logs, positions, risk_logs, dashboard）
- リスク監視（ドローダウンアラート・ポジション上限）
- Kill Switch（data/kill.flag）による ExecutionEngine 停止シグナル
- Paper Trading 検証レポート生成ツール：kabusys.tools.paper_verification_report
- ポートフォリオ構築（候補選定・重み付け・株数算出・セクター上限など）：kabusys.portfolio
- 研究用ファクター計算 / 特徴量解析（DuckDB 接続を受ける）：kabusys.research
- AI 関連
  - news_nlp: ニュースを LLM（OpenAI）でセンチメント解析し ai_scores に書き込み
  - regime_detector: ETF の MA 等とマクロニュースを合成して market_regime を判定

---

## セットアップ手順

前提:
- Python 3.9+（コードが型とモジュールを利用）
- 必要なライブラリ（例: duckdb, psutil, openai, PyYAML（任意）、など）をインストール

1. リポジトリをクローン / 展開
2. 必要なパッケージをインストール（例）
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は個別に duckdb, psutil, openai, PyYAML（検証用）などをインストール）
3. 初回設定（対話式ウィザード）:
   - python -m kabusys.config_setup
   - これによりプロジェクトルートに .env が作成されます（.env は絶対に Git にコミットしないでください）
4. 設定検証:
   - python -m kabusys.validate_config
   - 必須環境変数の未設定や config/*.yaml の簡易チェックを行います
   - --strict を付けると警告も失敗扱い（exit 1）
5. データディレクトリやログディレクトリの確認（通常は `data/`, `logs/` が必要）
   - .env の DUCKDB_PATH / SQLITE_PATH などはデフォルトで `data/` 以下に配置されます

重要な環境変数（代表）:
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: OpenAI API を利用する場合に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定モード、instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）が特定できる場合、起動時に .env / .env.local が自動読み込みされます。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主なコマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 発注エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度を high に設定します
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH にデータを記録します
    - 停止をトリガするにはプロジェクトの data/stop_requested.flag を作成するか、Kill Switch を用いた kill.flag を使用します
    - PID ファイル: data/execution.pid（デフォルト）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に（環境にかかわらず）本番 sqlite_path を使用して監視 DB を初期化します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 関連（プログラム API）
  - ニュースセンチメント付与: kabusys.ai.score_news（DuckDB 接続と target_date を渡す）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（DuckDB 接続と target_date を渡す）
  - これらは OpenAI API キー（OPENAI_API_KEY）を必要とします

ログ:
- setup_logging() が提供され、すべての起動スクリプトで共通の設定を使用。
- ログは stdout と logs/<app_name>.log に日次ローテート（30日分）で保存されます。

停止・Kill の仕組み:
- data/stop_requested.flag を作成するとメインループが検知してプロセスを停止します（run_execution / run_monitoring で参照）。
- KillSwitch は data/kill.flag に理由を記述して ExecutionEngine を停止させる仕組みです。
- 実運用では KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番では 0 推奨）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（.env 自動読み込み）
  - config_setup.py          — .env 生成ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — 監視 DB スキーマ・永続化 API
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （trade モニタ実装）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の読み書きロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信ロジック）
  - execution/
    - execution_engine.py    — 実行エンジンコア（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — モメンタム / ボラティリティ / バリュー等の計算
    - feature_exploration.py — IC 計算など
  - utils/
    - logging_setup.py       — 共通ロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

data/ と logs/ はプロジェクトルートに配置（デフォルト）。config/*.yaml は追加の設定ファイル群（検証対象）。

---

## 参考・運用上の注意

- .env は機密情報（API トークン・パスワード）を含むため、絶対にバージョン管理に含めないでください。
- 本番運用（KABUSYS_ENV=live）の場合は、LINE 通知設定や kill flag の扱いなどを必ず確認してください（validate_config による警告あり）。
- Paper Trading モードは本番 DB と完全に分離されるよう設計されています。PAPER_TRADING_SQLITE_PATH を必ず確認してください。
- OpenAI 等外部 API を使うモジュールは API クォータやコストに注意して運用してください。
- ローカルで起動する場合、psutil によるプロセス優先度設定や CPU affinity の操作で権限不足が発生することがあります。その場合はログの警告を確認してください。

---

必要に応じて README を拡張します。README に追加したい具体的な利用例（起動スクリプトの systemd / supervisor 用ユニット例、Dockerfile、CI 設定など）があれば教えてください。