KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした Python パッケージです。
主要機能は戦略用ファクター計算、ポートフォリオ構築と株数算出、ペーパートレード用検証、
システム監視・アラート・Kill Switch、LLM を使ったニュースセンチメント・レジーム判定などを含みます。

設計方針の要点
- 分析用データは DuckDB（files: data/kabusys.duckdb）で扱う
- 監視・取引ログ等は SQLite（data/monitoring.db、ペーパートレード時は data/paper_trading.db）へ保存
- 環境設定は .env を利用（自動読み込みあり）。CLI でウィザード・検証が可能
- OpenAI（gpt-4o-mini 等）を使ったニュース NLP / レジーム判定をオプションで搭載
- 実行スクリプトはプロセス優先度設定・ログ出力設定が統一的に行われる

主な機能
- ExecutionEngine / Broker クライアント（本番・ペーパートレード切替）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、ペーパートレード用 DB に記録
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/Disk、プロセス死活、データ鮮度の監視
  - TradeMonitor / RiskMonitor：滞留注文、約定異常、ドローダウンやポジション上限監視
  - KillSwitch：条件を満たすと data/kill.flag を書き込んで ExecutionEngine を停止
  - MonitoringEngine：上記を周期的に実行、アラート発火
- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算・IC（Information Coefficient）等の解析ユーティリティ
- ポートフォリオ構築（Portfolio）
  - 候補選定、等配分／スコア配分、リスクに基づく position sizing、セクター上限など
- AI モジュール（オプション）
  - news_nlp: raw_news を LLM でセンチメント化して ai_scores へ保存
  - regime_detector: マクロセンチメント＋ETF MA 乖離から市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを作成
- 設定管理・ユーティリティ
  - .env ウィザード（kabusys.config_setup）
  - 起動前設定検証（kabusys.validate_config）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティ など

前提条件 / 必要パッケージ
- Python 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, など
- 外部依存（主なもの）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML （config/*.yaml の中身検証を行う場合、無くても動作）
- 上記は requirements.txt 等で管理してください（本リポジトリに同梱されていない場合は手動で pip install）

セットアップ手順
1. リポジトリをクローン / 展開
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトで requirements.txt があればそれを使う）
4. データ・ログディレクトリを作成
   - mkdir -p data logs
5. .env を作成
   - 推奨: python -m kabusys.config_setup
   - または手動で data/kabusys.duckdb, data/monitoring.db 等のパスを設定
6. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

主要な環境変数
- 必須（運用時）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
- データベース
  - DUCKDB_PATH (default data/kabusys.duckdb)
  - SQLITE_PATH (default data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 専用 DB)
- ログ / プロセス
  - LOG_LEVEL (default INFO)
  - LOG_DIR (default logs/)
  - PID_FILE_PATH (ExecutionEngine の PID ファイル path, default data/execution.pid)
  - KILL_FLAG_PATH (kill.flag path, default data/kill.flag)
- AI
  - OPENAI_API_KEY （news_nlp / regime_detector で必要）
- 監視調整
  - MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒, default 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（閾値）

使い方（実行）
- 環境変数設定（.env を読み込むか事前 export）
- .env 作成（対話式ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能
  - 停止方法: Ctrl+C またはプロジェクトルート/data/stop_requested.flag を作成（ファイルを置く）
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB に記録され、本番 DB と分離されます
  - 起動時に data/stop_requested.flag が存在すると起動を中止します
- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 日付期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要
  - ニューススコア付け: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を用いる
  - これらは DuckDB 接続を引数に取る（研究・バッチ処理向け）

運用上のファイル / フラグ
- data/stop_requested.flag : スクリプトの外部停止要求（run_*.py が検知）
- data/kill.flag : Kill Switch による ExecutionEngine 停止トリガ（監視が書き込む）
- data/execution.pid : ExecutionEngine の PID 管理
- logs/<app_name>.log : 日次ローテーションでログ保存（app_name 例: execution, monitoring）

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ一元設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（テーブル作成 / CRUD）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （滞留注文等の監視）※実装参照
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - kill_switch.py         — Kill Switch 実装（flag 書込）
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — （アラート送信）※実装参照
  - execution/
    - execution_engine.py    — ExecutionEngine 実装（セッション管理）
    - broker_factory.py      — Broker クライアント生成（本番 / Mock 切替）
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
  - ai/
    - news_nlp.py            — OpenAI を使ったニュースセンチメント
    - regime_detector.py     — レジーム判定
  - tools/
    - paper_verification_report.py
  - data/                   — （実行時に使用するファイル・DB の既定パス）
  - logs/                   — デフォルトのログ出力先

補足・運用上の注意
- 本番運用前に必ず python -m kabusys.validate_config を実行して設定を確認してください。
- KABUSYS_ENV=live のときは LINE 通知等の設定を確認してください（validate_config が警告を出します）。
- OpenAI を用いる機能は API 利用料がかかります。稼働頻度・バッチサイズを運用ポリシーに合わせて調整してください。
- プロセス優先度は起動時に "high" を設定しますが、OS 権限やプラットフォームによっては設定に失敗する場合があります（ログに警告が出ます）。
- monitoring は本番 sqlite_path を参照します。ペーパートレード時に monitoring が誤って本番 DB を参照しないよう環境設定に注意してください（run_monitoring の設計上は本番 sqlite_path を使用します）。

トラブルシューティング（よくある質問）
- ログが出力されない / ファイルが作れない:
  - 環境変数 LOG_DIR を確認、logs ディレクトリの権限を確認してください。ログディレクトリ作成に失敗した場合は標準出力のみで継続します。
- DB ファイルが見つからない:
  - .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を確認してください。validate_config でもチェック可能です。
- AI 呼び出しでエラーが出る:
  - OPENAI_API_KEY が設定されているか、ネットワーク/レート制限を確認してください。news_nlp/regime_detector ではリトライとフォールバックロジックを備えています。

開発・拡張メモ
- research モジュールは DuckDB 接続を受け取り SQL で計算する設計です。データ準備（prices_daily / raw_financials 等）が必要です。
- position_sizing 等は純粋関数として設計されており、ユニットテストが書きやすくなっています。
- AI 関連は外部 API に依存するため、テスト時はネットワークリクエストをモックすることを推奨します（既に各所で _call_openai_api を差し替え可能にしています）。

ライセンス・バージョン
- パッケージバージョン: __version__ = "0.1.0"
- ライセンスはリポジトリの LICENSE ファイルを参照してください（存在しない場合は運用ポリシーに従ってください）。

以上がリポジトリの README です。必要であれば .env のサンプルテンプレートや具体的な systemd / supervisor 用の起動スクリプト例、requirements.txt の候補を追記できます。どの情報を補足しますか？