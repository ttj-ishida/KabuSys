README — KabuSys（日本株自動売買システム）
=====================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ／ツール群です。
主な目的は以下を含みます:
- シグナル → 注文発行を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働監視・アラート・Kill Switch を担う Monitoring コンポーネント
- ポートフォリオ構築（銘柄選定・重み付け・ポジション決定）
- 研究用ファクター計算・特徴量解析モジュール（DuckDB を使用）
- ニュース NLP / レジーム判定（OpenAI を用いたスコアリング）
- 環境設定ウィザード・設定検証・検証レポート生成ツール

重要な設計方針:
- ペーパートレード環境は本番 DB と分離（デフォルトで data/paper_trading.db を使用）
- ルックアヘッドバイアスを避けるため、日付参照は明示的に渡す実装が多い
- フェイルセーフ設計（API 失敗時のフォールバック、部分的な書き込み保護など）

主な機能一覧
--------------
- Execution
  - ExecutionEngine（発注ロジック、OrderManager、RiskManager、Reconciler）
  - ブローカークライアントを実行環境に応じて切替（paper_trading 用 MockBroker）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限検出
  - KillSwitch: しきい値超過で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニタのポーリング統合、アラート発行
  - monitoring_db: SQLite ベースの監視ログ永続化（テーブル作成 / マイグレーション機能含む）
- Portfolio construction
  - 候補選定（スコア順）、等金額 / スコア加重、リスクベースのポジションサイズ計算
  - セクター上限フィルタ、レジーム乗数
- Research
  - ファクター計算（momentum, volatility, value）: DuckDB を使用して prices_daily / raw_financials を参照
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- AI（OpenAI）
  - news_nlp: ニュース集合を LLM でセンチメント評価 → ai_scores へ書き込み
  - regime_detector: MA200 とマクロニュースで市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）: .env を対話式で作成
  - 設定検証（validate_config.py）: .env と config/*.yaml を検証
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）
  - ログ設定 / プロセス優先度設定ユーティリティ

セットアップ手順
----------------

1. リポジトリのクローン（想定）
   - ソースは src/kabusys 以下に配置されています。

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 基本的に以下をインストールしてください（pip 等で）:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML — config/*.yaml の検証を行う場合
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env を用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくはリポジトリルートに .env を作成して下記の環境変数を設定:
     - 必須:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 推奨 / 重要:
       - KABUSYS_ENV = development | paper_trading | live
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (ペーパー用 DB, デフォルト: data/paper_trading.db)
       - LOG_LEVEL (DEBUG/INFO/...)
       - OPENAI_API_KEY（AI 機能を使う場合）
   - 注意: .env は絶対に Git にコミットしないでください（config_setup.py も同様に注意書きあり）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. ディレクトリ
   - ログはデフォルト logs/、データは data/ に保存されます。logging_setup がディレクトリを自動作成しますが、権限等に注意してください。

使い方
-------

基本的なコマンド例を示します。すべてプロジェクトルート（pyproject.toml がある場所）で実行してください。

環境設定関連
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

ExecutionEngine 起動
- 本番 / ペーパーの切替は KABUSYS_ENV による:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、data/paper_trading.db に記録されます。
- 起動:
  - python -m kabusys.run_execution
- 停止制御:
  - Monitoring / KillSwitch によって data/kill.flag が書かれると ExecutionEngine は停止します。
  - run_execution は data/stop_requested.flag の存在も参照し、スレッドを終了します。

Monitoring 起動
- ポーリングループを開始:
  - python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）
  - export MONITOR_POLL_INTERVAL=30
- 注意: monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用します（監視ログは本番 DB に残る設計）

Paper Trading 検証レポート
- ペーパートレード DB を対象に検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

AI 機能（OpenAI）
- ニューススコアリング（例）:
  - Python から呼び出す:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="sk-...")
- 注意: OPENAI_API_KEY を環境変数に設定しておくか、関数呼び出し時に api_key を渡してください。API 呼び出しの失敗はフォールバック動作を取る設計ですが、キーが未設定だと例外になります。

停止フラグ / kill.flag
- run_execution / run_monitoring は data/stop_requested.flag を監視して終了します（手動停止用）。
- KillSwitch が発動すると data/kill.flag に理由が書き込まれ、ExecutionEngine はこれを検出して停止します。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動で kill.flag をクリアします（本番では推奨しません）。

ログ
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）へ出力されます。
- ログレベルは LOG_LEVEL または setup_logging の引数で指定できます。

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 以下の主要ファイル・モジュールの抜粋です:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py           — .env 作成ウィザード（対話式）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/
    - execution_engine.py     — ExecutionEngine や EngineConfig
    - broker_factory.py       — BrokerClientFactory（環境により Mock/実口座切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py        — SQLite テーブル作成・永続化 API（MonitoringDB）
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
  - tools/
    - paper_verification_report.py

付記 / 注意事項
---------------
- DB ファイル（DuckDB / SQLite）はデフォルトで data/ に置かれます。パスは環境変数で上書き可能です。
- .env の自動読み込みはプロジェクトルート（.git や pyproject.toml がある場所）を探索して行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を用いる機能は API 利用料金が発生します。テスト時はモック化（unittest.mock.patch）を利用することを推奨します。
- 本番運用時は KABUSYS_ENV=live に設定し、LOG_LEVEL・KillSwitch 設定・LINE 通知設定などを慎重に確認してください。validate_config の live 向けチェックが役立ちます。

ライセンス / バージョン
-----------------------
- __version__ = "0.1.0"（kabusys/__init__.py）

お問い合わせ / 開発メモ
----------------------
- コード内に多数の設計ノート・TODO コメントがあります。開発や運用にあたっては各モジュールの docstring を参照してください。
- 追加のセットアップ手順（kabuステーションの接続設定、J-Quants API の利用登録等）は別途ドキュメントにまとめてください。

以上。必要であれば、README に「依存関係の requirements.txt 例」「具体的な systemd ユニット / docker-compose 例」などの追記も行います。希望があれば教えてください。