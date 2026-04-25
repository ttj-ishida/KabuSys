README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。  
主な機能は以下のとおりです:

- 発注エンジン（ExecutionEngine）による注文管理・リスク制御
- 監視コンポーネント（System / Trade / Risk）による稼働監視と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制限）
- リサーチ（ファクター計算、特徴量解析、IC 計算）
- AI モジュール（ニュースセンチメント、レジーム判定：OpenAI を使用）
- 開発用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート）
- ログ出力（コンソール + 日次ローテーションファイル）

機能一覧
--------
主要コンポーネントと機能の概略:

- execution
  - ExecutionEngine：発注・セッション実行、OrderManager、RiskManager、Reconciler
  - BrokerClientFactory：本番/ペーパートレードでブローカクライアントを切替
- monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス稼働、データ鮮度チェック
  - TradeMonitor：注文滞留や約定異常の検出（コード内に実装あり）
  - RiskMonitor：ドローダウン・ポジション上限監視、リスクイベント記録
  - KillSwitch：条件に応じて data/kill.flag を書き実行を停止
  - MonitoringEngine：各 Monitor を束ねてポーリング
  - monitoring_db：監視用 SQLite スキーマ / 永続化 API
- portfolio
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes：複数手法に基づく株数算出、単元株丸め、集約キャップ調整
  - apply_sector_cap / calc_regime_multiplier：セクター制限・レジーム乗数
- research
  - calc_momentum / calc_volatility / calc_value：DuckDB を用いたファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量探索用ユーティリティ
- ai
  - news_nlp.score_news：ニュースを OpenAI へ送り銘柄ごとにセンチメントを算出・保存
  - regime_detector.score_regime：MA と LLM を組み合わせた市場レジーム判定
- tools
  - config_setup.py：.env の対話式生成・更新ウィザード
  - validate_config.py：環境変数・config/*.yaml の検証 CLI
  - paper_verification_report.py：ペーパートレード DB から検証レポート生成
- utils
  - logging_setup.setup_logging：stdout + 日次ローテーションログ設定
  - process_priority.set_process_priority / set_cpu_affinity：優先度／CPU 固定ユーティリティ

前提・依存
----------
最低限の依存（主要なもの）:
- Python 3.9+（コードの型注釈を参照）
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（設定ファイル YAML 検証に任意で使用）

（実際の requirements.txt がある場合はそちらを参照してください）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo_url>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
     （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）
4. 環境変数の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
     → 対話形式で .env を生成します（.env は Git にコミットしないでください）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
     --strict を付けると警告も失敗扱いになります

主要な環境変数（主なもの）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading の場合、発注はモック化され paper 用 SQLite に記録されます
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要（ai/news_nlp, ai/regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング秒（run_monitoring で上書き可）

使い方（起動・ツール）
--------------------

※ 実行はプロジェクトルート（pyproject.toml/.git があるディレクトリ）で行ってください。

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（注文エンジン）起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用しデータは data/paper_trading.db に書き込まれます
    - 起動時に data/stop_requested.flag が既に存在する場合は起動しません
    - 実行中に data/stop_requested.flag が作られると Engine を停止します
    - 実行中は data/execution.pid に PID が書かれます
    - 起動前に .env の KILL_FLAG_CLEAR_ON_START が 1 なら kill.flag を自動クリアする挙動があります（本番では注意）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
    - デフォルトは 60 秒ポーリング（環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能）
    - 監視は常に production の sqlite_path を使って monitoring DB を初期化します
    - data/stop_requested.flag が存在するとループを終了します

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ統計、最終判定 PASS/FAIL

- AI 系（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定して以下の関数を呼び出します（スクリプトとしての CLI はなし）
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 内部で OpenAI API を呼ぶため API キーと利用制限に注意してください
  - エラー耐性が組み込まれており、API 失敗時はフェイルセーフなフォールバックを行います

停止フラグ・Kill Switch
----------------------
- 停止フラグ（run_execution / run_monitoring が参照）
  - data/stop_requested.flag: このファイルが存在すると run_execution/run_monitoring のループが終了します（daemon 停止）
- Kill Switch（監視からの自動停止）
  - KillSwitch は重大なリスク条件（例: ドローダウン超過やポジション上限）を検出すると data/kill.flag を書き込みます
  - ExecutionEngine は起動時や定期チェックでこの kill.flag を確認し、検出時に安全に停止します
  - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアします（本番では推奨しません）

ログ
---
- ログは stdout（コンソール）とログファイルの両方に出力されます
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: execution.log, monitoring.log）、日次ローテーション・30日保持

データベース
-----------
- DuckDB（分析向け）: data/kabusys.duckdb（DUCKDB_PATH）
- SQLite（監視 DB）: data/monitoring.db（SQLITE_PATH）
- ペーパートレード用 SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- monitoring_db.init_monitoring_db() はスキーマを冪等に作成し、マイグレーション処理も行います

ディレクトリ構成
----------------
下記は主要ファイル/モジュールの概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定読み込み・Settings クラス
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - execution/                — 発注エンジン関連（BrokerFactory, Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ & 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

補足・運用上の注意
-----------------
- .env ファイルは絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- KABUSYS_ENV の設定によって実行モードが切替わるため（特に live は危険）、起動前の validate_config による確認を強く推奨します。
- OpenAI を利用する機能は料金が発生します。キーの管理・呼び出し頻度に注意してください。
- プロセス優先度設定や CPU affinity は OS によって制限を受ける可能性があり、権限不足時は警告を出してスキップします。
- 監視・発注の安全性のため、Kill Switch / stop_flag の挙動を理解した上で運用してください。

ライセンス・バージョン
----------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0
- ライセンス情報・貢献方法などはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上。README の内容について補足や特定箇所の詳細説明（例: ExecutionEngine の API、OrderRepository の仕様、AI プロンプトやリトライ方針など）が必要であれば教えてください。