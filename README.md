README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なシステムです。  
このリポジトリには、実行エンジン（ExecutionEngine）の起動スクリプト、監視（Monitoring）系コンポーネント、ポートフォリオ構築・ポジションサイジング、ファクター計算・研究用ユーティリティ、AI（OpenAI）を使ったニュースセンチメント評価などの主要ロジックが含まれます。

主な特徴
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番/ペーパートレード（KABUSYS_ENV）を切り替え可能
  - ペーパートレード時は MockBrokerClient を使用し、data/paper_trading.db に分離して記録
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文ログ、リスク（ドローダウン・保有上限）を定期チェック
  - Kill Switch（data/kill.flag）を使って ExecutionEngine に停止シグナルを送信
  - アラート機能とログ永続化（SQLite）
- Portfolio モジュール
  - 候補銘柄選定、重み計算（等金額・スコア重み）、ポジション決定ロジック（リスクベース / 等配分）
  - セクター上限の適用、レジーム乗数
- Research モジュール（duckdb を想定）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI モジュール（OpenAI）
  - ニュースによる銘柄センチメント評価（news_nlp.score_news）
  - マクロニュースとETF MA を組み合わせた市場レジーム判定（regime_detector.score_regime）
- ツール
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定関連ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
- 共通ユーティリティ
  - 統一的なログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity の設定（utils/process_priority.py）
  - SQLite / DuckDB 接続の想定

必要条件
-------
- Python 3.10+
- 推奨パッケージ（主要な依存）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config の YAML 検証を行う場合）
- 注意: 実行時に必要な追加パッケージは環境によって異なります。requirements.txt がない場合は上記を pip install してください。

環境変数（主なもの）
-------------------
必須（起動前に設定するか .env を用意してください）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- LOG_DIR: ログファイル格納ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI を使う場合
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード挙動）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" または "1"）

設定ファイルの自動読み込み
- プロジェクトルートに .env または .env.local があると、自動で環境変数に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効）。

セットアップ手順
--------------
1. Python と依存パッケージをインストール
   - 例:
     - python -m pip install "duckdb" "psutil" "openai" "PyYAML"
2. プロジェクトルートに移動（pyproject.toml または .git があるディレクトリ）
3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も致命的に扱う場合（CI 等）:
     - python -m kabusys.validate_config --strict
5. データディレクトリの準備（必要に応じて）
   - data/（SQLite ファイル、PID/flag ファイル用）
   - logs/（ログファイル用、logging_setup が自動作成を試みます）

基本的な使い方
--------------
起動スクリプト
- ExecutionEngine（発注エンジン）を起動:
  - python -m kabusys.run_execution
  - 動作中は data/execution.pid に PID を書き、data/stop_requested.flag が作られると終了します。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB とは分離）。
- Monitoring（監視ループ）を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path を使い DB に永続化します（環境に依らず）。

設定関連
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 起動前チェック:
  - python -m kabusys.validate_config

ツール
- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI 機能
- news_nlp.score_news や regime_detector.score_regime を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しは失敗時にフォールバック（多くのケースでゼロやスキップ）するよう実装されていますが、APIキーの設定が必須です。

Kill Switch / 停止制御
- Kill Switch：
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch はリスク検知（ドローダウンやポジション上限）によりトリガーされます。
- 停止フラグ:
  - run_execution.py / run_monitoring.py はプロジェクトの data/stop_requested.flag を監視して停止します。
- PID ファイル:
  - 実行時に data/execution.pid（デフォルト）などの PID ファイルが用いられます。

監視 DB（SQLite）
- init_monitoring_db により以下のテーブルが作成されます（冪等）:
  - system_status, trade_logs, positions, risk_logs, dashboard
- run_monitoring や MonitoringDB を通じてこれらに記録されます。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数/設定管理（Settings クラス）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py             — ニュースセンチメント評価（OpenAI）
  - regime_detector.py      — 市場レジーム判定（ETF + マクロセンチメント）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（schema 初期化・CRUD）
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — （発注ログ等の監視、存在）
  - risk_monitor.py         — ドローダウン・ポジション数監視
  - kill_switch.py          — kill.flag 書き込みロジック
  - monitoring_engine.py    — 各 Monitor の統合ループ
  - alert_manager.py        — （アラート送信管理。存在想定）
- execution/
  - broker_factory.py       — ブローカークライアント生成
  - execution_engine.py     — ExecutionEngine（発注ロジック）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py        — 共通ログ設定
  - process_priority.py     — プロセス優先度 / CPU affinity
- monitoring/                — 監視関連（上記）
- data/                      — 実行時に生成される想定のディレクトリ（DB / PID / flag）

（注）上記はリポジトリ内の主要ファイルを抜粋したものです。実際の運用では execution パッケージの詳細実装や broker 実装、data パイプライン、strategy 実装などが必要です。

開発・運用の注意点
------------------
- KABUSYS_ENV が live の場合は本番運用になります。LINE 通知や kill flag の設定などを慎重に確認してください（validate_config は live 時に追加警告を出します）。
- .env を絶対にバージョン管理にコミットしないでください（config_setup でもヘッダに注意書きがあります）。
- DuckDB/SQLite のファイルパスは .env または環境変数で上書きできます。ペーパートレード時は paper_sqlite_path を分離しておくことを推奨します。
- OpenAI 使用時は API コストが発生します。batch サイズやトークン上限、リトライポリシーがコード内で設定されていますが、実運用では監視を行ってください。

例: よく使うコマンドまとめ
-------------------------
- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動
  - python -m kabusys.run_execution
- Monitoring 起動（デフォルト 60 秒間隔）
  - python -m kabusys.run_monitoring
  - 短くしたい場合: MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
この README はコードベースの主要な用途・ファイル配置・実行方法の概略を示しています。詳細な設計や仕様（PortfolioConstruction.md、StrategyModel.md 等）はリポジトリ内のドキュメントや仕様書を参照してください。

問題があれば、どのコマンドやどのモジュールについて詳しく知りたいかを教えてください。追加でサンプル .env テンプレートや起動手順のデバッグ手順も提示できます。