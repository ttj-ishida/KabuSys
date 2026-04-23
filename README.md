README
======

概要
----
KabuSys は日本株の自動売買システム向けユーティリティ群とランタイムコンポーネントを含む Python パッケージです。本リポジトリには以下を含みます。

- 実行エンジン起動スクリプト（ExecutionEngine の起動）
- システム監視ループ（Monitoring）
- 環境設定ウィザード (.env の生成)
- 設定検証 CLI
- ペーパートレード検証レポート生成ツール
- ポートフォリオ構築 / ポジションサイジング / リスク制御の純粋関数群
- 研究用ファクター計算・特徴量解析モジュール
- OpenAI を利用したニュース NLP / レジーム判定ユーティリティ
- ロギング / プロセス優先度設定等のユーティリティ

主要な設計方針:
- 本番用 DB とペーパートレード DB を分離
- ルックアヘッドバイアス防止（date.today() 等を直接使わない実装）
- フェイルセーフ: 外部 API 失敗時は安全なデフォールトで継続
- 冪等な DB 初期化 / 書き込みを意識した実装

機能一覧
--------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV により挙動が変わる）
  - python -m kabusys.run_monitoring : SystemMonitor をポーリング起動
- 環境設定 / 検証
  - python -m kabusys.config_setup : .env を対話式に作成・更新
  - python -m kabusys.validate_config : 環境変数 / config/*.yaml のチェック
- 監視関連
  - system_monitor, trade_monitor, risk_monitor を統合する MonitoringEngine
  - kill.flag による ExecutionEngine 停止シグナル、stop_requested.flag による外部停止
  - 監視ログ永続化（SQLite）
- Execution（発注）
  - paper_trading モード時は MockBroker を使い data/paper_trading.db に書き込む（本番 DB と分離）
  - リスク管理・注文管理・照合機構（Engine 起動時に組み立て）
- 研究・解析
  - ファクター計算: momentum / value / volatility
  - forward returns / IC 計算 / 統計サマリー
- AI
  - ニュースを OpenAI でスコアリングし ai_scores に保存（news_nlp）
  - マクロニュース + ETF MA を用いたレジーム判定（regime_detector）
- ツール
  - ペーパートレード検証レポート生成: python -m kabusys.tools.paper_verification_report

前提条件（主な依存ライブラリ）
------------------------------
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の内容検証を行う場合に任意）
（SQLite は標準ライブラリで扱います）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （config YAML 検証を利用するなら）pip install pyyaml

   ※ requirements.txt がない場合は上記を個別にインストールしてください。

4. 環境変数の初期設定（.env の作成）
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants / kabuAPI のトークンや KABUSYS_ENV（development / paper_trading / live）を設定します。
   - あるいは .env ファイルを直接作成して配置（プロジェクトルート）。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

基本的な環境変数（主なもの）
----------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し data/paper_trading.db に分離して記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE = instant | partial | never | reject（ペーパートレードの約定挙動）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- LOG_LEVEL（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START（"1" にすると起動時に kill_flag を自動クリアするフラグを許容設定）

起動・使い方
------------

ExecutionEngine の起動
- 本番／開発／ペーパートレードを環境変数で選択:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 通常: python -m kabusys.run_execution
- run_execution は起動時に PID ファイル（data/execution.pid）を扱い、data/stop_requested.flag の存在で起動を停止します。
- Paper trading の場合、専用 DB (PAPER_TRADING_SQLITE_PATH, default: data/paper_trading.db) に書き込みます（本番 DB と完全分離）。

Monitoring の起動
- python -m kabusys.run_monitoring
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
- 監視は Settings.sqlite_path（monitoring.db）を使用します（Monitoring は常に本番 sqlite_path を参照する実装）。
- 停止は data/stop_requested.flag ファイルを作成（存在を検出して安全にループを終了）。

Kill Switch / 停止フロー
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送る仕組みです。
- KillSwitch はリスク条件（ドローダウン・ポジション上限など）に応じて flag を作成します。
- 存在を確認するためのメソッドや clear() による削除が用意されています。
- run_execution/run_monitoring は stop_requested.flag を用いる点に注意（stop_requested.flag は外部からの「直ちに停止」用）。

ログ
- ログは logs/<app_name>.log に日次ローテーションで保存されます（デフォルト logs ディレクトリ）。
- setup_logging() が全スクリプトから呼ばれ、一貫したログ管理を行います。
- LOG_DIR 環境変数でログ保存先を指定可能。ファイル出力に失敗した場合はコンソール出力のみになります。

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

ライブラリ API（代表的な関数）
- ポートフォリオ関連（純粋関数、DB 参照なし）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- 研究 / ファクター計算（DuckDB 接続を受け取る）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- AI（ニューススコアリング）
  - from kabusys.ai.news_nlp import score_news  # score_news(conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime  # score_regime(conn, target_date, api_key=None)

データベース初期化 / マイグレーション
- monitoring_db.init_monitoring_db(conn) は必要なテーブルとインデックスを冪等に作成し、既存 DB に不足カラムがある場合は ALTER TABLE で追加する軽微なマイグレーションを行います。

トラブルシューティング（よくある注意点）
- OpenAI を使う機能は OPENAI_API_KEY を要求します。未設定だと ValueError を投げます（明示的にチェックがある）。
- PyYAML がインストールされていない場合、validate_config は YAML 検証をスキップします（警告）。
- run_monitoring はモニタリング DB（Settings.sqlite_path）を使います。設定が意図しない DB を参照しないよう .env を確認してください。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみの出力になります（setup_logging の挙動）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/
  kabusys/
    __init__.py                     # パッケージ定義とバージョン
    config.py                       # Settings クラス（環境変数の取得・検証・自動 .env ロード）
    config_setup.py                 # .env 対話式ウィザード
    validate_config.py              # 設定検証 CLI
    run_execution.py                # ExecutionEngine 起動スクリプト
    run_monitoring.py               # SystemMonitor ポーリング起動スクリプト

    ai/
      news_nlp.py                   # ニュース NLP スコアリング（OpenAI 連携）
      regime_detector.py            # レジーム判定（MA + マクロセンチメント）
    monitoring/
      monitoring_db.py              # SQLite に対する永続化層
      monitoring_engine.py          # 複数 Monitor を束ねる実行ループ
      system_monitor.py             # CPU/メモリ/ディスク/データ鮮度監視
      risk_monitor.py               # ドローダウン・ポジション上限監視
      trade_monitor.py              # （存在を想定）取引ロギング監視
      kill_switch.py                # kill.flag の制御
      alert_manager.py              # （存在を想定）通知管理
    execution/
      ...                           # ExecutionEngine, BrokerFactory, OrderManager 等（参照あり）
    portfolio/
      portfolio_builder.py          # 候補選定・重み計算
      position_sizing.py            # 発注株数計算
      risk_adjustment.py            # セクター制限・レジーム乗数
    research/
      factor_research.py            # momentum / value / volatility 計算
      feature_exploration.py        # forward returns / IC / summary
    tools/
      paper_verification_report.py  # ペーパートレード検証レポート生成スクリプト
    utils/
      logging_setup.py              # ロギング設定ユーティリティ
      process_priority.py           # プロセス優先度 / CPU affinity 設定
    data/ (runtime)
      *.db, stop_requested.flag, kill.flag, execution.pid  # 実行時に使用されるファイル群（デフォルト）

ライセンス・コントリビュート
----------------------------
- 本 README はコードベースの説明を目的としています。実際のライセンス表記・貢献ルールはリポジトリ上の LICENSE / CONTRIBUTING ファイルを参照してください。

最後に
------
まずは .env を生成し（python -m kabusys.config_setup）、設定検証（python -m kabusys.validate_config）を実行してから、モードに合わせて run_execution / run_monitoring を起動してください。開発時は KABUSYS_ENV=development を使うと安全です。

必要であれば、本 README をベースに「デプロイ手順」「監視ダッシュボード構成」や「ExecutionEngine のアーキテクチャ図」などの追加ドキュメントを作成できます。どの情報がさらに欲しいか教えてください。