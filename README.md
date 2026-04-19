README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量な Python パッケージです。
主要機能は以下の通りです:

- 注文実行エンジン（ExecutionEngine） — 本番/ペーパー取引に対応
- 監視プロセス（MonitoringEngine/SystemMonitor/TradeMonitor/RiskMonitor）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・セクター制限）
- 研究用モジュール（ファクター計算、将来リターン、IC、統計サマリ等）
- AI 補助機能（ニュースを LLM でスコアリング、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度、.env ウィザード、設定検証、レポート）

主要な設計方針:
- 本番データへのルックアヘッドを避ける（日時依存を避ける実装）
- 冪等性（DB マイグレーション、INSERT/DELETE の扱い等）
- フェイルセーフ（API 失敗時はフォールバックして継続）
- モジュール単位で CLI / ライブラリとして利用可能

機能一覧
--------
- 実行
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードで MockBroker を使用）
  - Paper Trading は本番 DB と分離（デフォルト: data/paper_trading.db）
- 監視
  - run_monitoring.py: SystemMonitor ポーリングループを起動（MONITOR_POLL_INTERVAL で間隔上書き可）
  - MonitoringEngine: System/Trade/Risk の定期チェック、Kill Switch 評価、アラート送信
  - MonitoringDB: SQLite ベースの永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重、リスクベースのポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究（research）
  - ファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Spearman ランク相関）等
- AI
  - news_nlp.score_news: raw_news を OpenAI に渡して銘柄単位のセンチメントを ai_scores に保存
  - regime_detector.score_regime: ma200 とマクロニュースを組み合わせて市場レジーム判定を行い保存
- ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の事前検証 CLI
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成
  - utils.logging_setup: 統一ログ設定（stdout + 日次ローテーションファイル）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定

セットアップ手順
----------------

前提
- Python 3.9+（ソース内の型注釈から推定。実際のプロジェクト要件に合わせてください）
- SQLite は標準ライブラリで利用可
- DuckDB, psutil, openai, PyYAML 等の外部依存があります

インストール（簡易）
1. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows では .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （他に要るパッケージがあれば requirements.txt があれば pip install -r requirements.txt を利用）

環境変数設定
1. 対話式ウィザードで .env を生成（プロジェクトルートに .env が作成されます）
   - python -m kabusys.config_setup
   - ウィザードは既存 .env を読み取り、Enter で既存値を再利用できます

2. 主要な必須環境変数
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）

3. 任意・重要な環境変数（例）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY: OpenAI を使う機能で必要
   - LOG_LEVEL, LOG_DIR など

自動 .env 読み込み
- 起動時、プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

検証
- 設定検証 CLI
  - python -m kabusys.validate_config
  - 警告も失敗扱いにするには --strict

使い方
------

実行（CLI）
- 実行エンジン（ExecutionEngine）を起動：
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
  - 起動前に kill.flag をクリアする設定 KILL_FLAG_CLEAR_ON_START=1 がありますが、本番では 0 推奨

- 監視ループを起動：
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL=30（秒）
  - 監視は環境にかかわらず production (settings.sqlite_path) を参照します

- 設定ウィザード：
  - python -m kabusys.config_setup

- 設定検証：
  - python -m kabusys.validate_config [--strict]

ツール
- Paper Trading 検証レポート：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI / 研究 API（プログラムから呼び出し）
- ニューススコアリング（プログラム例）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="sk-...")

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="sk-...")

- 研究モジュール呼び出し例
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(duckdb_conn, date(2026,4,1))

停止・Kill Switch
- 監視側が条件を満たした場合（ドローダウン超過等） data/kill.flag に理由を書き込み、ExecutionEngine は stop を受けます
- 手動停止フラグ（外部でエンジンを停止）:
  - run_execution/run_monitoring は data/stop_requested.flag や data/execution.pid を利用して停止検出を行います

ログ
- ログは stdout とファイル（日次ローテーション、logs/<app_name>.log）に出力されます
- ログレベルは .env の LOG_LEVEL または setup_logging の引数で制御

ディレクトリ構成
----------------

以下はパッケージ内部の主なファイル・モジュール構成（src/kabusys 以下）です。主要なファイルのみ抜粋。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env 読み込み）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込み
    - regime_detector.py      — MA200 + マクロニュースでレジーム判定

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py       — CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py        — （取引・注文監視）※本コードベースに実装あり
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - alert_manager.py        — （アラート送信管理）※実装参照

  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py       — ブローカクライアント生成（本番/Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py    — 候補選定、等重/スコア重み算出
    - position_sizing.py      — 株数決定、aggregate cap、lot 調整
    - risk_adjustment.py      — セクター制限、レジーム乗数

  - research/
    - factor_research.py      — Momentum/Value/Volatility ファクター
    - feature_exploration.py  — 将来リターン、IC、統計サマリ

  - data/                     — 実行時データ/ログ/DB（デフォルト）
    - monitoring.db (default SQLITE_PATH: data/monitoring.db)
    - kabusys.duckdb (default DUCKDB_PATH: data/kabusys.duckdb)
    - paper_trading.db (default PAPER_TRADING_SQLITE_PATH: data/paper_trading.db)
    - kill.flag, stop_requested.flag, execution.pid

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py        — setup_logging
    - process_priority.py     — set_process_priority / set_cpu_affinity

補足・運用上の注意
-----------------
- KABUSYS_ENV を live に設定する場合は必須情報（API トークン等）や Kill Switch の挙動を十分に確認してください
- .env は絶対にソース管理にコミットしないでください（config_setup.py のヘッダに警告あり）
- OpenAI 等外部 API 使用部分は API キーの管理・コスト・レート制限に注意してください
- DB マイグレーションは簡易的に実装されていますが、重要な変更がある場合はバックアップを推奨します
- プロダクションではプロセス優先度やログディレクトリの権限設定、監視外部化（systemd / supervisor 等）を検討してください

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ に定義（例: "0.1.0"）
- ライセンス情報はリポジトリに含めてください（本ファイルには含まれていません）

お問い合わせ
------------
実装や運用に関する質問、拡張については該当モジュールの docstring を参照してください。必要なら README を拡張して追加の運用手順やデプロイ手順を記載できます。