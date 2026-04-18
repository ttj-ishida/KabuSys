README
======

概要
----
KabuSys は日本株向けの自動売買システム（分析・ポートフォリオ構築・発注・監視・運用支援ツール群）です。本リポジトリには以下を含む主要コンポーネントが実装されています。

- ExecutionEngine（発注エンジン、paper_trading（モック）と live（実口座）を切替可能）
- Monitoring（システム状態・注文ログ・リスク監視・Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI支援（ニュース NLP によるセンチメント評価・市場レジーム判定）
- 運用ユーティリティ（.env ウィザード / 設定検証 / Paper Trading レポート生成 等）

機能一覧
--------
主要な機能のハイライト：

- 環境管理
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 発注・実行
  - ExecutionEngine（実口座もしくはモック Broker）
  - 発注ログの永続化（SQLite）
  - Paper Trading 用に本番 DB と分離された専用 DB を使用
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - TradeMonitor: 注文の滞留・約定異常等の検出
  - RiskMonitor: ドローダウン・ポジション上限監視と Kill Switch（停止フラグ）
  - MonitoringEngine: これらを束ねてポーリング・アラート発行
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクベースのポジションサイズ計算
  - セクター集中制限・レジーム乗数
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）等の統計分析
- AI（OpenAI）
  - ニュース記事の銘柄別センチメント（news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（regime_detector）
- 運用ツール
  - Paper Trading の検証レポート生成スクリプト

前提条件 / 依存ライブラリ
------------------------
主な依存（一部は optional）:
- Python 3.10+
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- PyYAML（validate_config の YAML 検証を行う場合）

インストール例（仮想環境内）:
pip install duckdb psutil openai
（validate_config で YAML 検証をしたい場合は pip install pyyaml を追加）

セットアップ手順
----------------

1. リポジトリをクローンし、Python 仮想環境を作成して依存をインストールします。
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt  （requirements.txt がある場合）
     または: pip install duckdb psutil openai

2. .env ファイルの作成（対話式ウィザード推奨）
   - ウィザード実行:
     python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabu API パスワード、DB パス、KABUSYS_ENV 等を対話式で作成します。
   - 生成される .env は絶対に Git にコミットしないでください。

3. 設定検証
   - 作成後、設定を検証します:
     python -m kabusys.validate_config
   - 警告も失敗に含めたい場合:
     python -m kabusys.validate_config --strict

4. DB 初期化
   - 起動スクリプト（run_monitoring/run_execution）実行時に監視用テーブルは自動で作成されます（init_monitoring_db）。

主要な環境変数（抜粋）
--------------------
（config_setup で設定される項目を中心に）

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）

実行方法（使い方）
-----------------

- 環境セットアップ（例）
  export $(cat .env | xargs)  # 注意: セキュリティ上の注意を払って実行してください

- Monitoring の起動
  - 24/7 の監視ループを起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔（秒）を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 補足:
    - run_monitoring は Monitoring 用の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に関係なく本番パスを参照）。
    - 停止方法: プロジェクトルートの data/stop_requested.flag ファイルを作成するとループは安全に終了します。

- Execution（発注エンジン）の起動
  - 実行（フォアグラウンド、デーモン化は起動方法に応じて実装）:
    python -m kabusys.run_execution
  - Paper Trading（KABUSYS_ENV=paper_trading）の場合:
    - MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db） に格納され、本番 DB と分離されます。
  - 停止:
    - data/stop_requested.flag を作成するとエンジンを停止します。
    - Kill Switch（run_monitoring 内で評価）：条件を満たすと data/kill.flag が書き込まれ、実行エンジンに停止シグナルを送ります。
  - PID ファイル:
    - 実行時に data/execution.pid（設定次第）へ PID を書き込みます。

- Paper Trading 検証レポート
  - レポート生成:
    python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または api_key 引数で指定）
  - ai.score_news / ai.score_regime を呼んで DuckDB 接続と target_date を与えて実行します（スクリプト化して定期実行する想定）。

- .env ウィザード
  - 実行:
    python -m kabusys.config_setup

- 設定検証
  - 実行:
    python -m kabusys.validate_config

運用上の注意
------------
- ファイルベースの停止 / Kill Switch
  - stop_requested.flag: long-running スレッド/プロセス（monitoring / execution）が監視している停止フラグ。存在を検知すると安全に終了します。
  - kill.flag: Kill Switch により書き込まれる停止要求（重要なリスクが検知された際に運用者に代わって自動的に作成される）。存在する場合、ExecutionEngine の起動を抑止できます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なのでデフォルト 0 を推奨します。

- ロギング
  - ログは stdout と日次ローテーションされるログファイル（logs/<app_name>.log）に出力されます。
  - ログディレクトリは LOG_DIR 環境変数で変更可能。作成に失敗した場合はコンソール出力のみになります。

プロジェクト構成（主要ファイル）
------------------------------
以下はソースツリーの抜粋（主要モジュール）です。プロジェクトルートを想定しています。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py       — 監視用 SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py       — （trade 監視実装）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py       —（通知管理）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
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
    - tools/
      - paper_verification_report.py

- data/                      — デフォルトの DB / フラグファイル置き場（生成される）
- logs/                      — ログディレクトリ（デフォルト）

開発者向けメモ
--------------
- DuckDB を使って分析用テーブル（prices_daily, raw_financials, raw_news 等）を準備すると research / ai モジュールの機能をローカルで検証できます。
- unit テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。
- OpenAI 呼び出し周りは外部 API を叩くため、テスト時は各モジュール内の _call_openai_api をモックしてください。

ライセンス / バージョン
----------------------
パッケージバージョンは kabusys.__version__ に定義されています（例: 0.1.0）。ライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。

お問い合わせ / 参照
------------------
実装や運用フローに関する詳細はリポジトリ内のコードコメントとドキュメント（もしあれば）を参照してください。README に含めてほしい追加情報があれば教えてください。