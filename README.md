KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視のためのライブラリ／アプリ群です。  
主な目的は以下です。

- 株式戦略の研究（DuckDB を用いたファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイジング）
- ExecutionEngine による発注（本番 / ペーパートレードの分離）
- 監視（System / Trade / Risk モニタリング、Kill Switch）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 運用検証用ツール（ペーパートレード検証レポート等）

主要機能
--------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話式作成
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- MonitoringDB（SQLite）に system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理
- RiskMonitor / SystemMonitor / TradeMonitor を束ねた MonitoringEngine（アラート/kill 判定）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア化）と market regime 判定
- 研究用モジュール（ファクター計算、forward returns、IC 計算等）
- ポートフォリオ構築ユーティリティ（候補選定、等重・スコア重み、position sizing、セクター制約）
- ペーパートレード検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）

セットアップ手順（開発環境向け）
------------------------------
以下は一般的なセットアップ手順です。必要なパッケージはプロジェクト側の requirements.txt や pyproject.toml を参照してください（本リポジトリに合わせて適宜調整してください）。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 主要依存: duckdb, psutil, openai（AI 機能利用時）、PyYAML（validate_config の詳細検証用）

4. .env 作成（対話式推奨）
   - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL, LOG_DIR
     - OPENAI_API_KEY（AI 機能利用時）

5. 設定検証（必須項目が揃っているか確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）

基本的な使い方
---------------

1. ExecutionEngine の起動
   - 本番（あるいは .env に KABUSYS_ENV=live を設定した上で）
     - python -m kabusys.run_execution
   - ペーパートレード（.env に KABUSYS_ENV=paper_trading）
     - python -m kabusys.run_execution
     - ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます。
   - 起動時、プロセス優先度を high に設定します。
   - 実行時に data/stop_requested.flag が存在すると起動を中止または停止します。
   - 実行中は data/execution.pid に PID ファイルが書かれます。

2. Monitoring の起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: export MONITOR_POLL_INTERVAL=30）
   - Monitoring は常に本番 sqlite_path（settings.sqlite_path）を使用して監視ログを記録します。
   - 停止フラグは data/stop_requested.flag（存在するとループを終了）を参照します。

3. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）

4. AI（ニュース NLP / レジーム判定）
   - ai.score_news（kabusys.ai.score_news）や ai.regime_detector.score_regime を直接呼び出し可能（DuckDB コネクションと target_date を渡す）
   - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で指定
   - API 呼び出しは再試行ロジックを備え、失敗時はフェイルセーフなデフォールバックを行います

主な注意点 / 運用上のポイント
--------------------------------
- .env は機密情報を含むため、絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- KABUSYS_ENV によって DB の使い分け・発注挙動が変化します。特に live 設定時は本番発注となるため十分注意してください。
- Kill Switch: リスク条件（ドローダウンやポジション上限）到達で data/kill.flag が書き込まれ、ExecutionEngine の停止シグナルとなります。手動で解除する場合は該当ファイルを削除してください。
- ログ: デフォルトで logs/ ディレクトリに日次ローテーションでログが出力されます（kab u s y s.utils.logging_setup）。
- DuckDB / SQLite ファイルのデフォルト場所:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
- MONITOR_POLL_INTERVAL は 0 以下や非数値が与えられた場合デフォルト 60 秒にフォールバックします。

ディレクトリ構成（抜粋）
------------------------
以下はソースツリー（src/kabusys）のおもなファイルと役割の一覧です。リポジトリ直下に pyproject.toml / requirements.txt などがある想定です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定ラッパ（Settings クラス）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py      — マクロ＋MA で市場レジーム判定
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility ファクター計算
    - feature_exploration.py  — forward returns / IC / 統計サマリ
  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定・重み
    - position_sizing.py      — 発注株数計算（単元丸め・aggregate cap 等）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル初期化・CRUD）
    - monitoring_engine.py    — 各モニタの束ね処理（Polling）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 発注ログ・約定監視（実装あり）
    - risk_monitor.py         — ドローダウン／ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — アラート通知（LINE 等を想定）
  - execution/
    - execution_engine.py     — ExecutionEngine（セッション管理・発注ループ）
    - broker_factory.py       — BrokerClient の生成（実ブローカ or Mock）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/
    - (data パイプライン / DuckDB 用ユーティリティ等)
  - utils/
    - __init__.py
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
    - その他ユーティリティ

その他
-----
- validate_config.py / config_setup.py は CLI 用に用意されています。まず .env を生成し、validate_config で整合性を確認するワークフローを推奨します。
- AI 機能を使う際は OPENAI_API_KEY を設定してください。API 呼び出しはコストがかかりますので注意してください。
- DuckDB や SQLite のファイルパスは Settings 経由で上書き可能です。運用環境では適切なディレクトリに配置してください。

貢献
----
バグ報告・改善提案は Issue を立ててください。コード規約やテストカバレッジのガイドラインがあれば合わせて PR をお願いします。

ライセンス
--------
（ここにプロジェクトのライセンスを記載してください。例: MIT）

以上がこのコードベースの概要と基本的な使い方です。特定の機能（例: ExecutionEngine の設定、TradeMonitor の詳細、AI モジュールのテスト方法）について詳しいドキュメントが必要であれば、その箇所に絞って追記します。