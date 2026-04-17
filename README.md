KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
トレード ExecutionEngine、常時監視（Monitoring）、ポートフォリオ構築、ファクター研究、ニュース NLP（OpenAI）などのコンポーネントを含み、実運用（live）／ペーパートレード（paper_trading）／開発（development）モードを切り替えて実行できます。

主な特徴
--------
- ExecutionEngine（発注・注文管理・リスク管理・照合）
- Monitoring（CPU/メモリ/Disk、プロセス死活、データ鮮度、滞留注文・約定異常、リスク監視）
- Kill Switch（条件に応じて execution を停止するフラグ機構）
- Portfolio construction（候補選定・重み付け・株数決定・セクター制限）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール（ニュースのセンチメント分析、レジーム判定、OpenAI を使用）
- Paper Trading 用分析ツール（paper_verification_report）
- 環境設定ウィザード（.env 自動生成）と設定検証 CLI

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 記法を利用）
- システムに合わせて DB（DuckDB/SQLite）はローカルファイル利用

依存パッケージ（例）
- duckdb
- psutil
- openai
- requests
- PyYAML（config YAML 検証を行う場合）

インストール例
- 仮想環境を作成して有効化した上で:
  - pip install duckdb psutil openai requests pyyaml

プロジェクトルートの初期化
- data ディレクトリ等は必要時に自動作成されますが、手動で準備しておいても良いです。

.env の作成（推奨）
1. 対話式ウィザードを実行して .env を作成:
   - python -m kabusys.config_setup
2. 生成後、設定を検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

重要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用モード
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- データベース
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- ログ・プロセス管理
  - LOG_LEVEL (DEBUG|INFO|...)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0|1) — 本番では 0 を推奨
- OpenAI（AI モジュールを使う場合）
  - OPENAI_API_KEY

使い方
------

基本コマンド
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を参照（KABUSYS_ENV にかかわらず）。
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH、なければ data/paper_trading.db

停止・Kill スイッチ
- ExecutionEngine を外部から停止したい場合:
  - data/kill.flag に文字列を書き込む（KillSwitch が検出して ExecutionEngine を停止）
- 監視ループを停止するためのフラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します
- 注意:
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動でクリアしますが、本番では危険なので 0 を推奨します。

AI（OpenAI）関連
- ニューススコア／レジーム判定のために OPENAI_API_KEY が必要です。
- 課金が発生するため、本番運用時はキー管理と呼び出し回数に注意してください。

実運用注意事項
- KABUSYS_ENV=live は本番動作です。設定値・トークン・LINE通知先などを慎重に確認してください。
- paper_trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- プロセス優先度設定（高優先: set_process_priority("high")）を試みますが、権限によって失敗する場合があります（ログに警告が出ます）。
- OpenAI 呼び出しや外部 API の失敗はフェイルセーフ（多くは内部でログ・フォールバック）ですが運用時は監視を強めてください。

主要モジュール・機能一覧
-----------------------
- run_execution.py — ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 環境・設定ファイル検証 CLI
- monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル初期化・CRUD
  - system_monitor.py — CPU/メモリ/Disk・プロセス・データ鮮度監視
  - trade_monitor.py — 滞留注文・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor の統合実行
  - kill_switch.py — kill.flag 書き込み・管理
  - alert_manager.py — LINE Push 通知（クールダウン機能あり）
- execution/ (注文管理・ブローカークライアントなど) — ExecutionEngine を構成
- portfolio/ — 候補選定・重み計算・ポジションサイジング・リスク調整
- research/ — ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py — raw_news を OpenAI に送りセンチメントを ai_scores に書込む
  - regime_detector.py — ETF ma200 とマクロニュースでレジーム判定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
- config/*.yaml — 各種設定ファイル（system/data/strategy/risk/execution/monitoring）
- .env / .env.local — 環境変数（プロジェクトルートに配置、.env は Git 管理外推奨）

ディレクトリ構成（主要部分）
---------------------------
src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- execution/              (エンジン・ブローカー等の実装)
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
- utils/
  - process_priority.py

補足・運用ヒント
----------------
- DB をローカルで確認するには SQLite クライアント（monitoring.db / paper_trading.db）や DuckDB の CLI を活用してください。
- monitoring のログや risk_logs を見てしきい値・閾値をチューニングしてください（config/monitoring_config.yaml などを用意して運用する想定）。
- OpenAI を利用する機能は API 呼び出しの失敗に備えたフォールバック（無視・0.0）を組み込んでいますが、API エラーやレート制限を監視することを推奨します。
- 本 README はコードベースの主要な使い方をまとめたものです。詳細な設計（PortfolioConstruction.md、StrategyModel.md 等）や追加設定はリポジトリ内のドキュメントに従ってください。

ライセンス / バージョン
----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス表記はリポジトリルートの LICENSE を参照してください（存在する場合）。

お問い合わせ
-----------
- 開発者向け: コード内コメント・ドキュメントを参照してください。
- 運用時のトラブルはログ（標準出力 / monitoring DB / risk_logs）を確認の上、設定と環境変数を点検してください。

以上。必要であれば README に含めるサンプル .env テンプレートや起動スクリプトの systemd サンプルユニットファイルなども作成します。どの情報を追加しますか？