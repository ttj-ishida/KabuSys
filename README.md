KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視ツール群を含む Python パッケージです。本リポジトリは以下の機能を持ち、実運用（live）・ペーパートレード（paper_trading）・開発（development）いずれのモードでも動作するよう設計されています。

主な特徴
--------
- ExecutionEngine: 発注フロー（ブローカークライアント、注文管理、リスク管理、整合処理）
- Monitoring: システム稼働・データ鮮度・注文状況・リスクの継続監視、Kill Switch によるプロセス停止
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- Research: DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）、特徴量解析ツール
- AI 補助機能: ニュースセンチメント評価（OpenAI）、市場レジーム判定（MA + LLM）
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード・検証 CLI、検証レポート生成ツール

セットアップ
-----------
前提
- Python 3.10+
- SQLite（標準ライブラリ）
- ネットワーク接続（API を使用する場合）
- OS: Linux / macOS / Windows（ただしプロセス優先度や CPU affinity はプラットフォーム差に依存）

必須 Python パッケージ（例）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の構文チェック用・任意）

インストール例
- 仮想環境を作成して依存をインストールする例:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  - pip install --upgrade pip
  - pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を利用してください。）

環境設定 (.env)
- プロジェクトルートに .env を置くか、環境変数で設定します。
- 用意されている CLI で対話的に .env を作成できます:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

主な環境変数（Settings に定義）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB のデフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 時に使用）。デフォルト data/paper_trading.db
- PAPER_FILL_MODE: paper_trading 時のマッチングモード（instant, partial, never, reject）。デフォルト instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能で使用

使い方（コマンド / ランタイム）
-----------------------------

1) 実行エンジン（ExecutionEngine）
- 起動:
  - python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db）へ記録します。本番 DB と分離されます。
  - 実行中に "data/stop_requested.flag" 等の停止フラグを検出すると graceful に停止します。
  - プロセス起動時に優先度が "high" に設定されます（可能な環境で）。

2) 監視ループ（Monitoring）
- 起動:
  - python -m kabusys.run_monitoring
- 挙動:
  - Settings に基づく sqlite (monitoring.db) と DuckDB に接続し、SystemMonitor をポーリングします。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は環境に関わらず本番 sqlite_path を使用します（monitoring 用 DB は共有想定）。
  - 監視結果に応じて KillSwitch を書き込み、ExecutionEngine に停止シグナルを送ることができます。

3) 設定ウィザード / 検証
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

ライブラリとしての利用例
- ai モジュール:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=...)
- research モジュール:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- portfolio モジュール:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

監視 / Kill Switch の動作（補足）
- KillSwitch は risk の条件（ドローダウン閾値、ポジション上限等）で data/kill.flag を書き込みます。
- ExecutionEngine は起動時および実行中に stop flag（data/stop_requested.flag 等）をチェックして停止します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging で統一されます。
- デフォルトで stdout に出力し、logs/<app_name>.log に日次ローテーションでファイル出力（30日保持）を行います。
- LOG_DIR 環境変数でログディレクトリを変更できます。

ディレクトリ構成（主要ファイル）
-----------------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・資金配分
    - risk_adjustment.py      — セクター制約・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum, volatility, value）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル定義 / CRUD）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文/約定の監視（存在）
    - risk_monitor.py         — ドローダウン・ポジション監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各 Monitor を束ねるループ
    - alert_manager.py        — アラート送信（LINE 等、実装箇所）
  - execution/
    - execution_engine.py     — 実行エンジン（セッション管理）
    - broker_factory.py       — BrokerClient 作成
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文永続化（SQLite 等）
    - reconciler.py           — ブローカ状態との整合処理
    - risk_manager.py         — 発注前リスク評価
  - monitoring/monitoring_db.py (DB 初期化等)
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/                     — デフォルトの DB / フラグファイル置き場（運用時に作成）
    - monitoring.db (デフォルト)
    - paper_trading.db (paper mode)
    - kill.flag, execution.pid, stop_requested.flag など

開発上の注意
-------------
- DuckDB を使った分析機能は prices_daily / raw_financials / raw_news 等のテーブルを前提とします。データ投入が必要です。
- AI 機能は OpenAI API キー（OPENAI_API_KEY）が必要です。キー未設定時は ValueError を投げます（score_news, score_regime 等）。
- validate_config.py は PyYAML が無ければ YAML 検証をスキップします（警告）。
- Settings はプロジェクトルートを .git / pyproject.toml を基準に自動検出し .env をロードします（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

トラブルシューティング / よくある質問
------------------------------------
- ログディレクトリ作成に失敗するとコンソール出力のみで継続します。権限やパスを確認してください。
- psutil によるプロセス優先度設定は権限が必要な場合があります（AccessDenied が出ることがある）。
- DuckDB executemany に空リストを渡すと例外になるバージョンがあるため、コード内で空チェックを行っています。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報や貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上が本コードベースの概要・セットアップ・使い方・ディレクトリ構成です。README に追加してほしい詳細（例: requirements.txt の具体的内容、実運用チェックリスト、サンプル .env テンプレート等）があれば指示してください。