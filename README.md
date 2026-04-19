README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための小規模なプロジェクトです。本リポジトリには以下の主要機能を提供するモジュール群が含まれます。

- 注文実行エンジン（ExecutionEngine）とブローカー抽象化（本番 / ペーパートレード切替）
- 監視サブシステム（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（銘柄選定・配分・位置サイズ計算・セクター制約など）
- リサーチ（ファクター計算、特徴量探索、IC計算など）
- AI（ニュース NLP によるセンチメント分析・レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度、設定ウィザード・検証ツール 等）
- ツール：ペーパートレードの検証レポート生成スクリプト

主な設計方針として、実行ロジックと永続化（SQLite / DuckDB）を明確に分離し、ペーパートレード時は本番 DB と完全分離するようになっています。また、AI 関連機能は OpenAI API を使用します（API キー必須）。

機能一覧
--------
- 実行:
  - ExecutionEngine（run_execution 起動スクリプト）
  - ブローカー切替（KABUSYS_ENV=paper_trading で MockBrokerClient を使用）
  - ペーパートレード用 DB: data/paper_trading.db（分離）
- 監視:
  - SystemMonitor, TradeMonitor, RiskMonitor（run_monitoring 起動スクリプト）
  - kill.flag による安全停止（Kill Switch）
  - 監視ログ永続化（SQLite monitoring DB）
- ポートフォリオ構築:
  - 候補選定、重み付け（等金額 / スコア加重）
  - 位置サイズ計算（リスクベース / 等配分 / スコアベース）
  - セクターキャップ適用、レジーム乗数
- リサーチ:
  - Momentum/Value/Volatility ファクター、将来リターン計算、IC（Spearman）など
  - DuckDB を使用したテーブル参照ベースの計算
- AI:
  - ニュースを LLM（gpt-4o-mini）でスコアリングして ai_scores に書き込み
  - 市場レジーム判定（ETF + マクロニュース + LLM）
  - OpenAI SDK の例外処理・リトライ・レスポンス検証を実装
- ツール:
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 必要パッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証時に推奨）
   - 例: pip install duckdb psutil openai pyyaml

3. .env の用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 自動読み込み:
     - パッケージ起動時、プロジェクトルート（.git か pyproject.toml）を基点に .env と .env.local を自動読み込みします。
     - 自動ロードを無効化する場合:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗にする）:
     - python -m kabusys.validate_config --strict

5. ディレクトリ作成（logs / data 等）
   - 通常はコード実行時に自動作成されますが、権限等で失敗することがあるため手動作成しておくと安全:
     - mkdir -p data logs

主要な環境変数（抜粋）
---------------------
- 必須（実行する機能に応じて）
  - JQUANTS_REFRESH_TOKEN — J-Quants API
  - KABU_API_PASSWORD — kabuステーション API パスワード
- システム設定
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア (0/1)
- DB パス（デフォルト）
  - DUCKDB_PATH — data/kabusys.duckdb
  - SQLITE_PATH — data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（paper_trading 環境で上書き）
- OpenAI
  - OPENAI_API_KEY — AI 機能（news_nlp / regime_detector）
- 監視
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- その他
  - LOG_DIR — ログ保存先ディレクトリ（デフォルト logs/）
  - PID_FILE_PATH — 実行エンジンの pid ファイル（デフォルト data/execution.pid）

使い方（実行例）
----------------

- .env を作成し設定を確認したら以下を実行できます（src を PYTHONPATH に含めるかパッケージとしてインストールして実行）。

1) 監視ループを起動
   - デフォルトポーリング 60 秒:
     - python -m kabusys.run_monitoring
   - ポーリングを短くする（例: 30 秒）:
     - export MONITOR_POLL_INTERVAL=30
     - python -m kabusys.run_monitoring
   - 実行時にはプロセス優先度が "high" に設定され、監視ログは SQLite（settings.sqlite_path）へ記録されます。
   - 監視中にプロジェクトルート/data/stop_requested.flag が作成されるとループは終了します。

2) ExecutionEngine（注文エンジン）を起動
   - 本番 / 開発 / ペーパーは KABUSYS_ENV で切り替え:
     - 本番（例）: export KABUSYS_ENV=live
     - ペーパートレード（MockBroker を使用）: export KABUSYS_ENV=paper_trading
       - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使って完全に分離された DB に記録されます。
   - 起動:
     - python -m kabusys.run_execution
   - ExecutionEngine はスレッドで実行され、stop flag（data/stop_requested.flag）を検知して安全に停止します。PID ファイル（data/execution.pid）を作成します。

3) 設定ウィザード / 検証
   - .env ウィザード:
     - python -m kabusys.config_setup
   - 設定検証:
     - python -m kabusys.validate_config
     - python -m kabusys.validate_config --strict

4) Paper Trading 検証レポート生成
   - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - または指定 DB:
       - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ロギング
--------
- setup_logging によりルートロガーが設定され、以下の出力が行われます:
  - コンソール (stdout)
  - 日次ローテーションされたファイル: logs/<app_name>.log（デフォルト logs/）
- LOG_LEVEL / LOG_DIR で制御可能。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。

プロセス制御 / フラグ
--------------------
- stop_requested.flag:
  - run_monitoring / run_execution でループを停止させるための開発用フラグファイル（プロジェクトルート/data/stop_requested.flag）。
- kill.flag:
  - KillSwitch が判定条件を満たしたときに data/kill.flag に書き込むことで ExecutionEngine に停止指示（ExecutionEngine はこれを参照して停止処理を行います）。
- PID ファイル:
  - 実行エンジンは data/execution.pid（設定により変更可）へ PID を書きます。

依存関係（主要）
----------------
- duckdb — リサーチ / AI でのデータ参照・処理用
- psutil — システム監視・プロセス優先度設定
- openai — ニュース NLP / レジーム検出に使用
- PyYAML（オプション）— validate_config で YAML 検証を行う場合に必要

ディレクトリ構成
----------------
（プロジェクトの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（ETF + マクロ NLU）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ & 永続化ラッパー
    - system_monitor.py
    - trade_monitor.py        — （ファイルには抜粋されていませんが存在前提）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信ロジックが実装されていれば）
  - execution/
    - broker_factory.py       — ブローカークライアント作成
    - execution_engine.py
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
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルの一覧。実際のプロジェクトにはさらに補助モジュールやデータ定義が含まれる場合があります）

注意事項 / 運用上のポイント
---------------------------
- KABUSYS_ENV が live の場合は本番リスクがあります。validate_config の警告を必ず確認してください。
- .env は決してリポジトリにコミットしないでください（config_setup でも警告が出ます）。
- AI 機能は OpenAI API キーを必要とします。API 呼び出しはレート制限やサーバエラーへ耐性（リトライ）を実装していますが、呼び出しコストに注意してください。
- 監視・実行コンポーネントはフラグファイル（kill.flag / stop_requested.flag）を利用して安全に停止できます。運用時はこれらのフラグの取り扱いに注意してください。
- DuckDB / SQLite のパスは環境変数で変更可能です。ペーパートレードでの DB 分離を忘れないでください。

ライセンス・バージョン
---------------------
- パッケージバージョン: 0.1.0 （src/kabusys/__init__.py の __version__）
- ライセンス情報はリポジトリに含めてください（この README に明示されていない場合はプロジェクトの LICENSE ファイルを参照）。

お問い合わせ / 貢献
------------------
- バグ報告、改善提案、プルリクエストはリポジトリの Issue / Pull Request を利用してください。
- 機能追加や運用自動化（systemd / cron / k8s 等）を行う場合は、ログ / フラグファイルの扱いと権限に注意してください。

以上。必要であれば README に「インストール要件一覧（requirements.txt）」や具体的な systemd ユニット / Dockerfile の例を追加できます。どの情報を優先して追記しますか？