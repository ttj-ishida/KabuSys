README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視/アラート（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み計算・株数算出）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI 補助（ニュースセンチメント、レジーム判定：OpenAI を利用）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）
- 小規模の永続化（DuckDB / SQLite を利用した分析・監視ログ）

この README はリポジトリ内の主要なモジュールの使い方・セットアップ手順をまとめたものです。

機能一覧
--------
主な機能（抜粋）:

- Execution 起動: run_execution.py — 実際の発注/ペーパートレード切替対応
- Monitoring 起動: run_monitoring.py — システム/プロセス/データ鮮度の定期監視
- 環境設定ウィザード: config_setup.py — 対話式に .env を生成/更新
- 設定検証 CLI: validate_config.py — .env と config/*.yaml の健全性チェック
- Paper Trading レポート: tools/paper_verification_report.py — ペーパートレードログの検証
- ポートフォリオ構築: portfolio/ — 候補選定、重み計算、株数決定、リスク調整
- 研究モジュール: research/ — ファクター計算、将来リターン、IC 計算など
- AI モジュール: ai/ — ニュースセンチメント（OpenAI）やレジーム判定
- 監視永続化層: monitoring/monitoring_db.py — SQLite で監視ログを管理
- ログ・プロセスユーティリティ: utils/ — ログ設定、プロセス優先度設定等

要件
----
- Python 3.10+
- SQLite（標準ライブラリ）
- 推奨/必要な Python パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - PyYAML（validate_config の YAML 検証を実行する場合）
- 端末のパーミッション: process priority を変更するために管理者権限が必要な場合があります。

インストール（開発環境）
--------------------
1. リポジトリをクローンしてルートへ移動:
   - git clone <repo>
   - cd <repo>

2. 仮想環境作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai pyyaml

（プロジェクトで requirements.txt がある場合はそれを利用してください）

環境変数 / .env の準備
---------------------
- 自動読み込み:
  - kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml がある場所）を探索し、
    デフォルトで .env（→上書き不可）と .env.local（→上書き可）を読み込みます。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 推奨の流れ（対話式ウィザード）:
  - python -m kabusys.config_setup
  - ウィザードが .env を作成/更新します。敏感情報はマスクされます。

- 主要な環境変数（抜粋）:
  - JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用
  - KABU_API_PASSWORD（必須） — kabuステーション API 用
  - KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
  - OPENAI_API_KEY — OpenAI を使う AI 機能向け
  - LOG_LEVEL / LOG_DIR — ログ設定
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

設定検証
--------
対話的に作成した .env や config/*.yaml の整合性を確認するには:

- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱い（exit 1）になります:
  - python -m kabusys.validate_config --strict

注意: PyYAML がインストールされていると config/*.yaml のパースチェックも行われます。

実行方法
-------

1) 監視プロセス（Monitoring）
- run_monitoring.py は SystemMonitor をポーリングします。
- 実行:
  - python -m kabusys.run_monitoring
- 設定:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
- 停止:
  - プロジェクトルートの data/stop_requested.flag が存在するとループを終了します（run_monitoring はこれを監視）。
- ログ:
  - setup_logging により logs/monitoring.log に日次ローテーションで出力されます（LOG_DIR を別途指定可）。

2) 実行エンジン（ExecutionEngine）
- run_execution.py が ExecutionEngine を起動します。
- 実行:
  - python -m kabusys.run_execution
- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
- 停止 / PID:
  - 起動中の停止は data/stop_requested.flag を作成することで行えます。実行中のエンジンは定期的にこのフラグをチェックして安全停止します。
  - 実行時には pid ファイル（デフォルト data/execution.pid）を作成します。

3) Paper Trading 検証レポート
- tools/paper_verification_report.py:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用されます。
  - 出力: 稼働率、注文成功率、送信率、レイテンシ統計、最終判定 (PASS/FAIL)

4) AI 機能
- kabusys.ai.news_nlp.score_news、kabusys.ai.regime_detector.score_regime:
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）。
  - ニュース記事集約→LLM 呼び出し→ai_scores / market_regime への書き込みを行います。
  - API 呼び出しはリトライ/バックオフの実装あり。失敗時はフォールバック（例: macro_sentiment=0.0）して処理継続します。

運用上の注意点
--------------
- データベース:
  - 監視用: data/monitoring.db（Settings.sqlite_path）
  - 分析用: data/kabusys.duckdb（Settings.duckdb_path）
  - ペーパートレード: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- kill.flag / stop_requested.flag:
  - KillSwitch（kill.flag）: RiskMonitor 等の条件により ExecutionEngine を停止させるために書き込まれるフラグ（data/kill.flag）。存在すると Execution による処理開始や継続に影響します。
  - stop_requested.flag: run_monitoring や run_execution が外部からの停止依頼を受けるためのフラグ（data/stop_requested.flag）。これを作成すると該当スクリプトが安全に終了します。
- ロギング:
  - すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出して統一的なログ出力を行います。LOG_DIR と LOG_LEVEL で出力先／レベルを調整可能。
- process priority:
  - 起動スクリプトは最初に set_process_priority("high") を実行します。権限が不足する場合は警告を出してスキップされます。
- セキュリティ:
  - .env は絶対に Git 等にコミットしないでください（config_setup もその旨の注意書きを生成します）。

ディレクトリ構成
----------------
（主だったファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env の読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — Monitor の統合ループ
    - ... (alert_manager, trade_monitor など)
  - portfolio/
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 株数計算、キャップ/スケーリング
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py      — momentum/value/volatility 等のファクター計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py             — ニュースのセンチメントスコア化（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ... その他モジュール

開発メモ / ベストプラクティス
-----------------------------
- 本番環境では KABUSYS_ENV=live を使用する前に validate_config で設定を厳密に確認してください。
- OpenAI を使用する処理は API 利用料がかかります。ローカル開発やテスト時はモック化（関数の patch）を推奨します。
- プロセス優先度や CPU affinity の変更はシステムポリシーに依存します。権限不足でエラーになる場合はログに警告が出ますが処理自体は継続します。
- DuckDB は分析処理向け、SQLite は軽量永続化向けに使い分けています。データの整合性・バックアップ方針を運用ポリシーに合わせてください。

よく使うコマンド一覧
-------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理されています（デフォルト 0.1.0）。
- ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（なければプロジェクトの方針に従って追加してください）。

フィードバック / 貢献
--------------------
バグ報告、改善提案、プルリクエストはリポジトリの Issue / Pull Request で受け付けます。コード変更時はユニットテストの追加・既存テストの更新をお願いします。

以上。必要であれば README に含めるコマンド例や .env のサンプル（敏感情報を除く）を追加します。どの程度の詳細（例: 各設定項目の説明やサンプル .env）を追記しましょうか？