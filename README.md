# KabuSys

日本株向けの自動売買／リサーチ基盤ライブラリ & 実行スクリプト群です。  
本リポジトリは発注エンジン、監視・アラート、リサーチ（ファクター計算・特徴量解析）、AI を用いたニュース NLP などのコンポーネントを含みます。

以下はコードベースから抜粋した README です。

---

## プロジェクト概要

KabuSys は次のような機能を備えた日本株自動売買システムの基盤実装です。

- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化
- システム監視（SystemMonitor）・取引監視（TradeMonitor）・リスク監視（RiskMonitor）
- Kill Switch（条件を満たしたら発注エンジンを停止するフラグ）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチモジュール（ファクター計算、将来リターン、IC、統計サマリー）
- AI モジュール（OpenAI を使ったニュースセンチメント計算、市場レジーム判定）
- Paper Trading 用の検証レポート生成ツール

設計上の特徴：
- 環境変数／.env による設定（Settings クラス）
- DuckDB（時系列データ解析）と SQLite（監視・トレードログ）を併用
- 実行スクリプトはプロセス優先度設定・ログ設定を統一している
- Paper Trading（KABUSYS_ENV=paper_trading）では本番 DB と分離された専用 SQLite を使用

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードを切替）
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
  - MonitoringEngine: 各種 Monitor（System/Trade/Risk）を束ねて実行、Kill Switch 評価、アラート発行
- 設定関連
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: 起動前に .env / config/*.yaml の妥当性チェック
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成
- 研究／分析
  - research.factor_research: モメンタム/バリュー/ボラティリティ等のファクター算出（DuckDB 使用）
  - research.feature_exploration: 将来リターン計算、IC 計算、統計サマリー等
- AI 関連
  - ai.news_nlp: ニュース記事を OpenAI で評価して ai_scores に書き込み
  - ai.regime_detector: マクロ記事 + ETF MA を組み合わせて市場レジーム判定
- ポートフォリオ
  - portfolio: 候補選定、重み算出、ポジションサイズ計算、セクター上限適用など
- ユーティリティ
  - utils.logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

1. リポジトリを取得
   - git clone して作業ディレクトリに入る

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要なパッケージ例（requirements.txt がある場合はそちらを使う）
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の準備（対話式ウィザード）
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）

   自動的に .env を読み込む仕組み:
   - プロジェクトルート（.git または pyproject.toml がある場所）から .env / .env.local を自動読み込みします。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

6. 初期データベース（ディレクトリ作成）
   - デフォルトでは data/ 配下にファイルが作られます。必要に応じてディレクトリを作成してください（logging_setup も logs/ を作成します）。

注意: OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定してください。

---

## 使い方（主要コマンド例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で切替:
    - development: 開発（発注なし）
    - paper_trading: ペーパートレード（MockBrokerClient を使用、デフォルト DB: data/paper_trading.db）
    - live: 本番（実際に発注）
  - paper_trading 用の DB を上書きする場合:
    - export PAPER_TRADING_SQLITE_PATH=/path/to/paper_trading.db

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔（秒）を環境変数で上書き可能:
    - export MONITOR_POLL_INTERVAL=30
  - stop フラグ: data/stop_requested.flag を作成するとループが終了します
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）に接続します。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / リサーチ系はライブラリ関数として利用
  - 例: kabusys.ai.score_news, kabusys.ai.score_regime, kabusys.research.calc_momentum など
  - OpenAI を使う関数は OPENAI_API_KEY（もしくは引数）を必須にするものがあります

- ログ
  - デフォルトのログディレクトリ: logs/
  - 各アプリは logs/<app_name>.log（日次ローテート）に出力します
  - ログレベルは LOG_LEVEL 環境変数で制御可能（DEBUG/INFO/...）

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境 (development | paper_trading | live). デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を使う機能に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

その他の設定やデフォルト値は kabusys.config.Settings クラスのプロパティ説明を参照してください。

---

## 停止 / Kill Switch

- 実行スクリプト（run_execution/run_monitoring）はプロジェクト配下の data/stop_requested.flag を監視しています。停止させたい場合はこのフラグファイルを作成してください（自動的にループが終了します）。
- Execution の強制停止（Kill Switch）は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る仕組みがあります（KillSwitch の評価は monitoring 側で行われます）。
- run_execution は実行時に data/execution.pid を生成します（pid ファイルの場所は Settings.pid_file_path で変更可）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度ユーティリティ
  - execution/               — 実行エンジン関連（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — 監視 DB の初期化・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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
  - tools/
    - paper_verification_report.py

注: 上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。

---

## 開発・運用上の注意

- 本番（KABUSYS_ENV=live）では .env や config を慎重に管理してください。validate_config は本番向けの追加チェック（LINE 設定等）も行います。
- Paper Trading モードは本番 DB と完全に分離されるのが設計方針です（PAPER_TRADING_SQLITE_PATH を利用）。
- AI 呼び出しは外部 API（OpenAI）に依存します。API エラー系はリトライやフェイルセーフで扱われますが、API コストと制限に注意してください。
- logs/ や data/ のディスク容量、DuckDB/SQLite のパス、ログローテーション設定に注意し、運用環境に合わせて適切に設定してください。
- process_priority の設定は OS に依存して失敗することがあります（アクセス権限等）。失敗時は警告ログでスキップされます。

---

必要に応じて README を拡張します。特定のコマンドやモジュールの詳細な使い方（API シグネチャ、例）を追加したい場合は教えてください。