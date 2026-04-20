KabuSys — 日本株自動売買システム
=============================

このリポジトリは、日本株向けの自動売買システム（KabuSys）のコアライブラリおよび起動スクリプト群を含みます。戦略の研究・特徴量計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）・アラート、Paper Trading 用の検証ツール、LLM を用いたニュース解析などの機能を備えています。

この README はプロジェクト概要、主要機能、セットアップ手順、使い方（起動方法・主要 CLI）、およびディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
---------------
KabuSys は次の目的を想定した Python 製の自動売買フレームワークです。

- リサーチ層（DuckDB 上の時系列データへ SQL/Python でファクター計算）
- ポートフォリオ構築（候補選定・重み計算・株数算出・セクター制約）
- Execution 層（ブローカークライアントを抽象化し、発注/注文管理/リスク管理/再照合）
- Monitoring 層（システム稼働・注文状態・リスク監視、Kill Switch）
- Paper Trading サポート（本番 DB と分離された専用 sqlite を用いる）
- AI モジュール（OpenAI を使ったニュース NLP、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

主な機能一覧
--------------
- 環境設定管理
  - .env の自動読み込み（.env, .env.local、OS 環境変数優先）
  - 対話式ウィザードで .env を生成する CLI（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）で環境変数・設定ファイルをチェック

- Execution（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカ抽象化（paper_trading 時は Mock）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine による発注・監視・再照合
  - execution.pid / stop フラグでプロセス管理

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働/データ鮮度を監視
  - TradeMonitor: 発注ログや約定の異常検出（滞留注文・約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件（例: 大きなドローダウン）で data/kill.flag を書き込み Execution を停止
  - 監視用 SQLite（monitoring.db）への永続化（monitoring_db モジュール）

- Research / データ処理
  - DuckDB を用いたファクター計算（momentum/value/volatility 等）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
  - ポートフォリオ構築（候補選定、スコア加重、等重、ポジションサイズ算出、セクター制約）

- AI（OpenAI）
  - ニュース NLP（gpt-4o-mini を想定）により銘柄ごとにセンチメントスコア付与（ai_scores テーブルへ）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ・バックオフ等を処理し、フェイルセーフで進行

- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）
  - ログ: コンソール(stdout) と日単位ローテートファイル（logs/<app>.log）

セットアップ手順
-----------------

前提
- Python 3.10 以上（PEP 604 の型表記などを利用）
- システムにより必要なネイティブ依存があるパッケージあり（psutil 等）

依存パッケージ（例）
- duckdb
- psutil
- openai
- pyyaml （設定検証の YAML パース用）
- その他プロジェクトで利用するパッケージ

推奨インストール手順（仮想環境）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt）

3. プロジェクトルートに移動
   - cd <project_root>  （pyproject.toml または .git が存在するディレクトリ）

初期設定（.env）
1. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します（保存しない限り書き込まれません）

2. 作成した .env を確認・編集
   - .env は機密情報を含むため Git 管理にコミットしないでください（README/注意書きあり）

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

使い方（起動・CLI）
-------------------

主要エントリポイント（モジュール実行形式）
- Execution Engine を起動（本番 or paper_trading に応じ動作）
  - python -m kabusys.run_execution

  動作のポイント:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）へ記録して本番 DB と分離します。
  - 実行中は data/execution.pid を使用。停止は data/stop_requested.flag を作成して行います。

- Monitoring を起動
  - python -m kabusys.run_monitoring

  動作のポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path（settings.sqlite_path）を使用して監視ログを保存します。
  - data/stop_requested.flag が検知されると監視ループを終了します。

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（標準出力へ出力）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 sqlite（data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant, partial, never, reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト 60）

ログ
- setup_logging() が提供する統一ログ設定により、コンソール出力（stdout）と日次ローテートファイル出力（logs/<app_name>.log）を使用します。
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL または引数で制御可能。

運用上のファイル（data ディレクトリ）
- data/execution.pid: ExecutionEngine の PID（起動時に書かれる想定）
- data/kill.flag: Kill Switch による停止指示（書き込まれると Execution を停止させる）
- data/stop_requested.flag: run_execution / run_monitoring の外部停止フラグ（存在で停止）
- DB ファイル: data/monitoring.db（監視）, data/paper_trading.db（paper_trading デフォルト）

開発者向け API（主なモジュール）
- kabusys.config: 環境設定読み取りと Settings クラス（settings = Settings()）
- kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai: score_news（ニュース NLP）、regime_detector での LLM 利用
- kabusys.monitoring: MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、KillSwitch
- kabusys.utils: logging_setup、process_priority（優先度設定）

ディレクトリ構成
----------------
以下はリポジトリの主要ファイル／ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/Settings 管理、.env 自動読み込み
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し、ai_scores 更新）
    - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティ等の計算（DuckDB）
    - feature_exploration.py — 将来リターン/IC/統計サマリー
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数算出・スケーリング・lot 単位丸め
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化・読み書きラッパ
    - system_monitor.py      — システム稼働・データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（滞留注文等）
    - risk_monitor.py        — ドローダウン/ポジション上限監視
    - kill_switch.py         — kill.flag 書込ロジック
    - monitoring_engine.py   — 各モニタの束ね（Polling loop）
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory 等の実装群) — 発注関連
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/                    — 例: monitoring.db, paper_trading.db, pid/flag ファイル（運用時に生成）

運用上の注意点 / ベストプラクティス
-----------------------------------
- .env に API キー等の機密を含めるため、絶対に Git 等へコミットしないでください。
- 本番（KABUSYS_ENV=live）での起動前に python -m kabusys.validate_config を実行し、設定を慎重に確認してください。
- Kill Switch（data/kill.flag）の自動クリアは危険です。本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- Monitoring は監視対象 DB に対して書き込みを行います。monitoring は環境にかかわらず settings.sqlite_path（本番）を使用する点に注意してください。
- Paper Trading は paper 用 DB に完全分離されるため、テスト・検証時に実データを汚染するリスクが低減されます。
- OpenAI の呼び出しは API キー設定と料金管理が必要です。AI モジュールは失敗時にフェイルセーフとして処理を継続する設計です（スコア 0 等でフォールバック）。

最後に
-------
この README はコードベース内の主要な実装（スクリプト名・デフォルト値・動作）を元に作成しています。詳しい設計仕様や運用手順、追加の設定ファイル（config/*.yaml）などは別途ドキュメント（Design / Ops）を参照してください。

必要であれば、README に
- 起動例（systemd ユニット・cron / supervisor など）
- さらに詳しい環境変数一覧（全項目）
- サンプル .env.example
などを追記します。どの内容を拡張したいか教えてください。