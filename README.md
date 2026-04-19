KabuSys — 日本株自動売買システム
================================

このリポジトリは「KabuSys」と呼ばれる日本株向けの自動売買／リサーチ基盤の一部実装です。
モジュール設計は発注エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュースNLP／レジーム判定）などで構成されており、
実運用を想定したフェイルセーフ（kill flag／paper trading分離）やログ管理が組み込まれています。

主な特徴
-------
- 発注エンジン（ExecutionEngine）と監視プロセス（Monitoring）を分離。
- Paper Trading（KABUSYS_ENV=paper_trading）時に本番 DB と分離してテスト可能。
- SQLite（監視ログ） + DuckDB（分析用データ）を併用。
- Kill Switch（データベース＋フラグファイル）で安全にエンジンを停止可能。
- ニュースを LLM（OpenAI）で評価して銘柄別スコアを算出する AI モジュール。
- ポートフォリオ構築（候補選定・重み付け・単元丸め・リスク調整）用の純粋関数群。
- ログはコンソール（stdout）と日次ローテートファイル（logs/<app>.log）へ出力。

機能一覧
-------
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、OS環境変数優先）
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config（--strict オプションあり）
- 実行（Execution）
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - Paper Trading 用の MockBroker との分離（PAPER_TRADING_SQLITE_PATH）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 起動スクリプト: python -m kabusys.run_monitoring
  - 監視ログは SQLite（init_monitoring_db でテーブル作成）
- AI / リサーチ
  - ニュース NLP によるセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - ファクター計算／特徴量解析（kabusys.research）
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ユーティリティ
  - ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）

セットアップ手順
--------------
1. 必要な Python バージョン
   - Python 3.10 以上を推奨（型注釈で | 演算子を使用）

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   例:
     pip install duckdb psutil openai PyYAML

   - sqlite3 は標準ライブラリ（別途インストール不要）

3. プロジェクトルートに移動して .env を用意
   - 対話式で作成:
       python -m kabusys.config_setup
   - 生成後、設定を検証:
       python -m kabusys.validate_config
     --strict を付けると警告も失敗として扱います。

4. ディレクトリ／ファイルの確認
   - デフォルトでは data/ 下に SQLite / PID / フラグファイル等を作成します。
   - logs/ はログ出力先（設定により変更可）。

主要な環境変数（抜粋）
-------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用し data/paper_trading.db を使用
    - live: 本番

- データベース / ファイル
  - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH など（デフォルトは data/ 以下）

- ログ / 設定
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（"1"=有効。productionでは推奨しない）

- Paper Trading / AI
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - OPENAI_API_KEY: OpenAI を利用する場合に設定

実行方法（代表例）
-----------------
- 設定ウィザード:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視プロセス起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60秒）。
  - 監視は production sqlite_path を使用（KABUSYS_ENV に依らず）。

- 発注エンジン（Execution）起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し専用 DB に記録します。
  - 停止: data/stop_requested.flag を作成すると起動中ループを検知して安全に停止します。
  - 実行時は data/execution.pid に PID を書き込みます。

- Paper Trading 検証レポート:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で上書き可能）

- AI スコアリング（コード API）
  - ニューススコア付与:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="...")

  （上記はライブラリ API 呼び出し例。CLI は用意されていません）

停止・Kill Switch
----------------
- 手動停止（全成分）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して安全に終了します。
- Kill Switch（自動停止指示）:
  - RiskMonitor 等が条件を満たすと monitoring 層が data/kill.flag を書き込み、ExecutionEngine 側で検出すると停止を試みます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動で消す動作になります（本番では推奨しない）。

ディレクトリ構成（抜粋）
---------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py        — （実装ファイルは同ディレクトリにある想定）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        —（アラート実装想定）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（エンジン設定等）
    - broker_factory.py
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
    - logging_setup.py
    - process_priority.py

補足（運用上の注意）
-----------------
- .env は絶対にリポジトリへコミットしないこと（config_setup もその旨を注意喚起します）。
- KABUSYS_ENV=live の場合は特に LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や Kill Switch の設定を慎重に行ってください。
- DuckDB / SQLite のパスは設定でカスタマイズ可能です。Paper Trading は本番 DB と完全に分離することを想定しています。
- OpenAI API を使う機能は API キーが必要で、料金・レート制限に注意してください。API エラー時はフェイルセーフで処理を継続する実装方針です。

貢献・拡張案
-----------
- モニタ／アラートを外部サービス（Slack / PagerDuty）へ連携する alert_manager の実装強化
- BrokerClient の実装追加（実ブローカー接続）
- 単元数（lot_size）を銘柄毎に持たせる拡張
- テストカバレッジの追加（ユニット・統合テスト）
- Docker / systemd ユニットによる運用化

ライセンス・バージョン
--------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

---

この README はソース内のコメント・実装から主要点を抜粋してまとめたものです。実運用前に python -m kabusys.validate_config で設定を検証し、.env を適切に構成してください。必要であれば README をプロジェクト固有の手順に合わせて更新してください。