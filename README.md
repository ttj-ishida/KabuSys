KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量なコードベースです。
主な機能は取引エンジン（ExecutionEngine）、監視（Monitoring）、
ポートフォリオ構築・ポジションサイズ計算、ファクター計算・リサーチ、
および AI ベースのニュースセンチメント評価（OpenAI）です。

設計上のポイント
- 環境変数 / .env による設定管理（config.py）
- DuckDB と SQLite を併用（分析用 DuckDB、監視/発注ログ用 SQLite）
- Paper trading と Live の切替対応（KABUSYS_ENV）
- ログは stdout と日次ローテートファイル（logs/<app>.log）に出力
- Kill Switch（data/kill.flag）による安全停止機能
- OpenAI を用いたニュース NLP / レジーム判定機能（API キー必要）

主な機能一覧
--------------
- 実行（ExecutionEngine）起動スクリプト:
  - run_execution.py — ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB に記録。
- 監視（Monitoring）:
  - run_monitoring.py — SystemMonitor をポーリングし system_status 等を記録、KillSwitch を評価。
  - MonitoringEngine, SystemMonitor, RiskMonitor, KillSwitch, MonitoringDB 等。
- 設定管理:
  - config_setup.py — 対話式 .env ウィザード（初期作成/更新）。
  - validate_config.py — .env と config/*.yaml の事前検証 CLI（--strict オプションあり）。
- 研究・分析:
  - research.factor_research — モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB ベース）。
  - research.feature_exploration — 将来リターン計算 / IC / 統計サマリ等。
- ポートフォリオ構築:
  - portfolio.portfolio_builder / position_sizing / risk_adjustment — 候補選定・重み・株数決定・セクター制約など。
- AI:
  - ai.news_nlp — raw_news を LLM に投げて ai_scores に書き込む（OpenAI）。
  - ai.regime_detector — MA とマクロニュースで市場レジーム判定。
- ツール:
  - tools.paper_verification_report.py — Paper Trading の検証レポート生成（稼働率、約定率、レイテンシ等）。

セットアップ手順
----------------
1. Python 環境の作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai
   - （オプション）PyYAML があると validate_config の YAML 検証が有効化される:
     pip install pyyaml

   ※ リポジトリに requirements.txt がある場合はそれを使用してください:
     pip install -r requirements.txt

3. プロジェクト配置・データディレクトリ作成
   - 作業ルートに `data/` と `logs/` が自動で作られますが、手動で作る場合:
     mkdir -p data logs

4. 環境変数の設定（.env）
   - 対話式ウィザードで作成する（推奨）:
     python -m kabusys.config_setup
   - または手動で .env を作成。最低必須:
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     KABUSYS_ENV=development  # development|paper_trading|live
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

   重要:
   - 実運用時は KABUSYS_ENV=live として設定する際に十分に注意してください。
   - OpenAI を使う機能は OPENAI_API_KEY を設定してください。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります:
     python -m kabusys.validate_config --strict

使い方（起動例）
----------------
- ExecutionEngine を起動（デフォルトは Settings に従う）
  - python -m kabusys.run_execution
  - 環境例（ペーパートレード）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止は data/stop_requested.flag を作ることで起動ループが検出して終了します。
  - 起動時に PID ファイル（data/execution.pid）を書き出します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き可能:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に「本番用」monitoring DB パス（Settings.sqlite_path）を使います。
  - 停止も data/stop_requested.flag を作成することで終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 別 DB を参照する場合:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（ニューススコアリング / レジーム判定）
  - OpenAI API キーを環境変数に設定（または関数呼び出し時に api_key を渡す）:
    export OPENAI_API_KEY=sk-...
  - DuckDB に raw_news, news_symbols, ai_scores 等のテーブルが存在することが前提です。
  - 関数として利用する例（Python REPL 内）:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

主要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live

- データパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db （paper_trading 用）

- ログ:
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LOG_DIR: logs/

- 監視:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

- Kill Switch / 停止フラグ:
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番は 0 推奨）

- OpenAI:
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）

ディレクトリ構成（主なファイル）
-------------------------------
リポジトリの主要な階層（src/kabusys を基準に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ・永続化層
    - system_monitor.py      — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - alert_manager.py       — （アラート送信機能; 実装参照）

  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager など — 発注ロジック)

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み算出
    - position_sizing.py      — 株数計算・スケールダウンロジック
    - risk_adjustment.py      — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py     — Momentum/Volatility/Value などの計算
    - feature_exploration.py — forward returns / IC / summary 等

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定

運用上の注意
------------
- 本番環境（KABUSYS_ENV=live）では設定ミスが致命的になる可能性があります。validate_config を必ず実行して確認してください。
- kill.flag / stop_requested.flag / PID ファイルの扱いに注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番では危険です。
- OpenAI を使う処理は API コストとレートリミットに注意し、API キーの管理は慎重に行ってください。
- ログディレクトリの権限やディスク使用量に注意し、ログローテーション（30日分保持）を確認してください。

貢献と拡張
------------
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）を準備することで研究・AI 機能を有効にできます。
- ExecutionEngine や BrokerClient の実装差し替えで実際のブローカ連携を行えます（kabuステーション 等）。
- config/*.yaml を用いたパラメタライズ（strategy / risk / execution）を追加で読み込む設計になっています。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

以上が README の概略です。必要であれば、.env.example のテンプレートや実際の起動例（systemd ユニット / supervisor / Docker Compose）などの運用ガイドを追加します。どの情報を詳しく追記しますか？