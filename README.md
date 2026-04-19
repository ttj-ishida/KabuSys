README
======

概要
----
KabuSys は日本株自動売買システムのライブラリ群および起動スクリプト群です。本リポジトリは以下の機能を提供します。

- 実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）を分離して運用できる設計
- Paper Trading（モックブローカー）と Live（実ブローカー）を環境変数で切替可能
- DuckDB / SQLite を使ったデータ分析・監視ログ保存
- ニュースを用いた AI スコアリング（OpenAI）と市場レジーム判定
- ポートフォリオ構築・ポジションサイジング・リスク調整の純粋関数群
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証ツール）
- Paper Trading の検証レポート生成ツール

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db を使用
  - run_monitoring.py — SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔上書き可）
- 設定管理
  - config_setup.py — 対話式 .env 作成・更新ウィザード
  - validate_config.py — .env と config/*.yaml の検証 CLI（--strict オプションあり）
- モニタリング
  - monitoring/：SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、監視用 DB レイヤ
  - kill.flag / stop_requested.flag による安全停止機構
- 研究・ポートフォリオ
  - research/：ファクター計算、特徴量探索、IC 等
  - portfolio/：候補選定、重み算出、ポジションサイズ計算、セクター上限・レジーム調整
- AI（OpenAI）
  - ai/news_nlp.py — ニュースを OpenAI でセンチメント評価し ai_scores に書き込む
  - ai/regime_detector.py — マクロセンチメントと ETF MA を使った市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレードの検証レポート生成
- ユーティリティ
  - utils/logging_setup.py — 統一ログ設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py — Windows / POSIX を吸収したプロセス優先度 / CPU affinity

セットアップ手順
----------------
前提
- Python 3.9+（コードは型ヒントに Python 3.9+ 機能を想定）
- 仮想環境（venv）を推奨

例: 仮想環境作成・有効化
- Unix/macOS:
  python3 -m venv .venv
  source .venv/bin/activate
- Windows:
  python -m venv .venv
  .\.venv\Scripts\activate

依存パッケージのインストール（最低限）
- 必要な主要パッケージ:
  pip install duckdb psutil openai

- 任意（設定ファイルの YAML 検証など）:
  pip install pyyaml

（プロジェクトに requirements.txt があればそちらを利用してください）

初期設定
1. 対話式ウィザードで .env を作成:
   python -m kabusys.config_setup
   - このウィザードは .env を生成します。生成後は .env を絶対にリポジトリにコミットしないでください。

2. 設定検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

データディレクトリの準備
- デフォルトでは以下ファイルパスが使用されます（.env で上書き可能）
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
- 実行前に data/ ディレクトリを作成しておくか、スクリプトが自動で作成します（場合によりパーミッションに注意）。

重要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (監視)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant / partial / never / reject、デフォルト: instant）
- OPENAI_API_KEY — OpenAI を使う場合に必要（ai.news_nlp, ai.regime_detector）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（開発時のみ 1 を推奨、 production より慎重に）

使い方
------
エントリポイント（モジュール実行を想定）
- 監視プロセスを起動:
  python -m kabusys.run_monitoring
  - 動作: process priority を "high" に設定、監視 DB に接続して SystemMonitor のループをポーリング。MONITOR_POLL_INTERVAL 環境変数で間隔変更可（デフォルト 60 秒）。停止は data/stop_requested.flag の作成で行います。

- 実行エンジンを起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い Paper Trading DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 実行中は data/execution.pid を使いプロセス管理・停止監視を行い、data/stop_requested.flag があれば停止します。

- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で指定可）
  - レポートは稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL を判定します。

AI 機能
- news_nlp.score_news / regime_detector.score_regime は OpenAI API キーを必要とします（OPENAI_API_KEY または引数で渡す）。
- OpenAI 呼び出しはリトライ・バックオフやレスポンス検証を備えていますが、API 失敗時はフェイルセーフ（0 相当など）で続行する設計です。

停止・Kill Switch
- 実行エンジン（ExecutionEngine）や監視プロセスには次のフラグが使われます:
  - data/stop_requested.flag — 監視・実行スクリプトの即時停止用（外部で作成するとループが終了）
  - data/kill.flag — KillSwitch が書き込むファイル。KillSwitch はリスクルール（ドローダウン、ポジション上限等）に基づき ExecutionEngine の停止を要求します。kill.flag が存在すると ExecutionEngine は起動を中止または停止します。
- 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤ってクリアされると危険）。

ログ
- logging_setup.setup_logging により stdout（コンソール）と日次ローテートファイルを root ロガーに設定します。
- デフォルトログディレクトリ: logs/
- 例: logs/execution.log, logs/monitoring.log

ディレクトリ構成（主要ファイル）
-----------------------------
以下はコードベースの主要なディレクトリとファイルです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / .env 自動ロードと Settings
    - config_setup.py           — 対話式 .env ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py         — （実装参照: トレード監視）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py        — （アラート送信ロジック）
      - monitoring_engine.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/                      — 実行時生成される想定ディレクトリ
      - kabusys.duckdb
      - monitoring.db
      - paper_trading.db
      - execution.pid
      - kill.flag
      - stop_requested.flag

設計上の注意点 / 運用上の注意
-----------------------------
- KABUSYS_ENV を適切に設定してください。live（本番）モードでは特に注意が必要です（validate_config が警告を出します）。
- .env は機密情報（API トークン・パスワード）を含むため、絶対にバージョン管理にコミットしないでください。
- OpenAI を使用する機能は API キーとコスト管理に注意してください。AI 呼び出しはバッチ化・リトライを備えていますが、運用時は呼び出し回数の監視が必要です。
- monitoring は監視 DB（sqlite_path）を本番 DB として常に参照します。ExecutionEngine は paper_trading 時は paper_sqlite_path を使い本番 DB とは分離します。
- ログディレクトリ作成に失敗した場合はコンソールログのみとなるため、ディスク容量やアクセス権限に注意してください。
- process priority / cpu affinity の設定には管理者権限が必要な場合があります。権限不足時は警告が出て処理を継続します。

開発者向けメモ
--------------
- pure 関数群（portfolio/*, research/*）は DB に依存せず単体テストが容易です。
- monitoring/monitoring_db.py は SQLite に対するマイグレーションロジック（カラム追加）を内蔵しています。既存 DB の互換性に配慮しています。
- OpenAI 呼び出し部分はテストのために _call_openai_api を monkeypatch / patch して差し替え可能です。

問い合わせ / 貢献
-----------------
バグ報告や改善提案は pull request / issue を通してください。重大な運用上の変更（特に live 環境に影響するもの）は事前に議論してください。

以上。README に不足している点や具体的な運用手順（systemd でのサービス化、Docker 化、CI 設定など）を追加したい場合は要望を教えてください。