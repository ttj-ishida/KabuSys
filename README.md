# KabuSys

日本株自動売買システムの軽量ライブラリ群と起動スクリプト群。  
このリポジトリは戦略構築・バックテスト／リサーチ用ユーティリティ、発注実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、および AI を使ったニュース評価などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- ファクター算出・特徴量解析（research）
- ポートフォリオ組成・株数計算（portfolio）
- 発注管理・リスク管理・ExecutionEngine（execution）
- 実行系の稼働監視・アラート・Kill Switch（monitoring）
- ニュース NLP（OpenAI を利用したセンチメント評価）とレジーム判定（ai）
- 設定ウィザード・検証ツール（config_setup / validate_config）
- ペーパートレード検証レポート生成ツール（tools）

設計上の特徴：
- .env / 環境変数ベースの設定管理
- DuckDB（分析用）と SQLite（監視・発注履歴）を併用
- Paper Trading と Live を明確に分離（Paper は専用の SQLite を使用）
- OpenAI（gpt-4o-mini）を利用する AI 機能（API キー必須）

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI: news_nlp.score_news / regime_detector.score_regime（OpenAI API を利用）
- ポートフォリオ構築: 候補選定・重み付け・ポジションサイズ計算、セクター制約、レジーム乗数
- 監視 DB 層: monitoring_db.py（永続化および小さなマイグレーションを含む）
- ログ設定ユーティリティ: utils.logging_setup.setup_logging（console + 日次ローテーション）

---

## 要件

- Python 3.10+
- 必要な（代表的な）パッケージ:
  - duckdb
  - psutil
  - openai
  - (任意) pyyaml — config/*.yaml の構文チェックに使用

requirements.txt があればそれを使うのが簡単です。無ければ手動でインストールしてください:

pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン / checkout

2. 仮想環境を作成・有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール:
   pip install -r requirements.txt
   または
   pip install duckdb psutil openai pyyaml

4. .env の初期作成（対話式ウィザード推奨）:
   python -m kabusys.config_setup
   - ウィザードは .env を生成します（.env は絶対に Git にコミットしないでください）。

   最低限必要な環境変数:
   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD （必須）
   その他: OPENAI_API_KEY（AI 機能使用時）、KABUSYS_ENV、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等

   自動ロードについて:
   - 起動時にリポジトリルートの .env / .env.local を自動読み込みします。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定検証（起動前の推奨確認）:
   python -m kabusys.validate_config
   --strict を付けると警告も FAIL 扱いになります:
   python -m kabusys.validate_config --strict

6. ディレクトリ（data, logs 等）の作成はスクリプトが自動で行ったり、README の指示に従って手動作成してください。ログはデフォルトで `logs/`、DB は `data/` 下に作られます。

---

## 使い方

以下はよく使うコマンド例です。

- 環境ウィザード（.env作成／更新）
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid が作成されます（Settings.pid_file_path 参照）。

- Monitoring を起動（監視ループ）
  python -m kabusys.run_monitoring
  - デフォルトで 60 秒間隔で SystemMonitor.check_once() を実行します。
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（監視は環境に依らず本番 sqlite_path を使用する実装です）。
  - 停止は data/stop_requested.flag（存在検知）により検出して終了します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプションで --db を使い別ファイルを指定可能:
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

- AI 機能（プログラムから呼び出す）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で指定）
  - ニュース NLP（銘柄ごとセンチメント）:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key=None)

- ログ設定:
  各起動スクリプトは utils.logging_setup.setup_logging(app_name=...) を呼び出し、`logs/<app_name>.log` に日次ローテートで出力します。ログディレクトリは LOG_DIR 環境変数で変更可能。

---

## 停止・Kill Switch の扱い

- data/stop_requested.flag
  - run_monitoring.py と run_execution.py のループがこのファイルの存在を検知して安全に終了します（外部からプロセスを優雅に停止させたい場合に利用）。

- Kill Switch (data/kill.flag, Settings.kill_flag_path)
  - RiskMonitor / KillSwitch の評価により、致命的な状況（例: 大きなドローダウン、ポジション上限超過）が検出されると kill.flag が書き込まれます。
  - Kill Switch が書き込まれると ExecutionEngine の外側で検出して停止させるフローが期待されます（運用ルールに従ってください）。
  - Settings.kill_flag_clear_on_start が `1` の場合は起動時に kill.flag を自動クリアします（本番では `0` 推奨）。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- データベース / ファイル
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
  - PID_FILE_PATH (デフォルト data/execution.pid)
  - KILL_FLAG_PATH (デフォルト data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)

- ログ
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR

- OpenAI
  - OPENAI_API_KEY（AI 機能を使う場合必須）

- 監視
  - MONITOR_POLL_INTERVAL（run_monitoring の polling 秒数上書き）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理
- config_setup.py           — 対話式 .env ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- execution/
  - execution_engine.py
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
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- data/ (デフォルトで生成されることが期待される）
  - monitoring.db (SQLite)
  - paper_trading.db (paper トレード用 SQLite)
  - kabusys.duckdb (DuckDB)
- logs/ (ログファイル格納)

（この README はコードベースの主要ファイル群に基づいてまとめています。実際のリポジトリではさらに細かいモジュールやスクリプトが存在する場合があります）

---

## 運用上の注意

- .env は機密情報を含みます。絶対にリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）での起動前には validate_config の実行を必須としてください（LINE 通知設定や Kill Switch 関連の警告等を確認）。
- OpenAI 等の外部 API を利用する機能は失敗時にフォールバック処理を行うよう設計されていますが、API制限や費用に注意してください。
- run_execution は paper_trading モードと live モードで DB を分離しているため、誤って本番 DB に書き込むリスクは低くなっていますが、環境変数の設定ミスには注意してください。
- ログディレクトリの作成に失敗するとファイル出力が無効化されコンソールログのみになります。運用時は logs/ に書き込み権限があるか確認してください。

---

必要であれば、README に「API 仕様（主要関数・クラスの使い方）」「設定項目の詳細（.env 例）」「開発用のテスト手順」などを追加できます。どの追加情報が欲しいか教えてください。