KabuSys — 日本株自動売買システム
================================

本リポジトリは日本株向けの自動売買・研究ツール群（KabuSys）の一部実装です。
ここに含まれるモジュールは、発注エンジン（Execution）、監視（Monitoring）、
ポートフォリオ構築、リサーチ（DuckDB を用いたファクター計算）、および
LLM を使ったニュース NLP / レジーム判定などを想定しています。

この README はコードベースの主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
- 発注エンジン（ExecutionEngine）とその補助コンポーネント（OrderManager / RiskManager / Reconciler 等）。
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）による定期チェックと Kill Switch。
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ計算、セクター制限等）。
- 研究モジュール（DuckDB 接続を受け取ってファクター計算・特徴量探索を実行）。
- AI 関連モジュール：ニュース NLP（OpenAI を使ったセンチメント評価）・市場レジーム判定。
- CLI ツール：.env 設定ウィザード、設定検証、Paper Trading 検証レポート生成 など。

主な機能一覧
-------------
- 環境設定ウィザード（kabusys.config_setup.run_wizard）
  - 対話式に .env を生成・更新できます。
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数、YAML 設定ファイル、DB パス等を事前検証します。
- Execution 起動スクリプト（src/kabusys/run_execution.py）
  - KABUSYS_ENV に応じて MockBroker（paper_trading）または実ブローカーを使用。
  - paper_trading は data/paper_trading.db に分離して記録します。
- Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
  - System / Trade / Risk の各監視をポーリングして監視ログ（SQLite）へ記録。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
- MonitoringDB（SQLite）API（kabusys.monitoring.monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard 等の永続化。
- Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - 運用ログを解析して PASS/FAIL 判定（稼働率・注文成功率・レイテンシ等）。
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重・スコア重み、リスクベースのポジションサイズ計算など。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news: OpenAI を用いてニュースを銘柄ごとにスコアリング。
  - regime_detector.score_regime: マクロニュース + ETF MA200 を合成してレジーム判定。

セットアップ手順
----------------

1. Python と依存パッケージのインストール
   - Python 3.9+ を推奨（duckdb や psutil が必要）
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai (OpenAI Python SDK)
     - PyYAML (config/*.yaml のパース検証を行う場合)
   - 例（pip）:
     - pip install duckdb psutil openai PyYAML

2. プロジェクトルートへ移動
   - この README と同階層に src/ や config/ が存在する想定です。

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照してください）。
   - 最低限設定すべき環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - OPENAI_API_KEY（AI 機能を使うなら必須）
   - その他任意/運用変数:
     - PAPER_FILL_MODE（paper_trading 用、instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）
     - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする strict モード:
     - python -m kabusys.validate_config --strict

5. 初期データディレクトリ
   - デフォルトの DB は data/ 以下に作成されます。必要に応じてディレクトリを作成してください。
   - 一部スクリプトは起動時にディレクトリを自動作成します。

使い方（主なコマンド）
--------------------

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 動作中に停止させたい場合:
    - data/stop_requested.flag を作成すると実行スレッドが検出して停止します。
    - Execution 側は data/execution.pid を作成して PID を管理します。
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録されます（本番 DB と完全分離）。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を指定可能（秒）。
  - 監視は常に（環境に関係なく）本番 sqlite_path を使用して監視ログに書き込みます。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能。

- AI 機能（プログラムから呼ぶ）
  - ニュース NLP:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - どちらも API キーは引数または環境変数 OPENAI_API_KEY を参照します。

停止 / Kill Switch
------------------
- 手動で Execution を停止したい場合:
  - data/stop_requested.flag を作成すると run_execution のポーリングループが検知して停止します（run_monitoring も同様に検知）。
- Kill Switch（監視側が危険と判断した場合）:
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にして自動クリアを無効にすることを推奨します。

重要な環境変数一覧（抜粋）
---------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — execution 環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI API キー（AI 機能に必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視関連設定
- PAPER_FILL_MODE — paper_trading の注文約定モード（instant|partial|never|reject）

ディレクトリ構成（主要ファイル）
------------------------------
以下はコードベースの主要モジュールと概略です（src/kabusys 以下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env 自動読み込み・Settings 定義
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前の設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py             — OpenAI を使ったニューススコアリング
      - regime_detector.py      — レジーム判定
      - __init__.py
    - monitoring/
      - monitoring_db.py        — SQLite スキーマ & DB ヘルパー
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py        — （未完、アラート送信の入り口）
      - kill_switch.py
    - execution/                — (発注周りの実装がある想定)
      - order_manager.py
      - order_repository.py
      - execution_engine.py
      - ... (その他)
    - data/                     — データ処理 / pipeline モジュール（DuckDB 連携）
    - utils/
      - process_priority.py     — プロセス優先度 / CPU affinity ヘルパ
      - __init__.py
    - monitoring/               — 上記監視関連

注意事項 / 運用上のヒント
-----------------------
- paper_trading モードは本番 DB と完全分離するよう設計されています。必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI を呼ぶ処理は外部 API に依存するため、API キー・レート制限・コストに注意してください。news_nlp と regime_detector はリトライ・フォールバックロジックを備えていますが、運用設計で考慮してください。
- Monitoring は常に本番 sqlite_path を使用して監視ログを書き込みます。監視ルーチンは MONITOR_POLL_INTERVAL に従って定期実行されます。
- ローカル開発時は KABUSYS_ENV=development に設定し、発注処理が行われないことを確認してください。
- .env を絶対にリポジトリにコミットしないでください（秘密情報が含まれます）。

ライセンス / 貢献
-----------------
（ここにライセンスや貢献方法を追記してください。例: MIT, Contributor License Agreement 等）

最後に
------
この README はコードから読み取れる機能を要約したものです。実際の運用・展開にあたっては config/*.yaml（プロジェクト固有設定）や本番ブローカーの実装、セキュリティ運用手順を十分に整備してください。質問や補足があればお知らせください。