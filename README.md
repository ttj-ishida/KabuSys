README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームです。  
戦略のリサーチ（DuckDB を用いたファクター計算）、ポートフォリオ構築、注文執行（本番／ペーパートレード分離）、監視・アラート、LLM を使ったニュース NLP 等のコンポーネントを含みます。

主な特徴
--------
- 戦略リサーチ
  - DuckDB を使った prices_daily / raw_financials 参照のファクター計算（モメンタム、ボラティリティ、バリュー 等）
  - 将来リターンや IC（Spearman）計算、統計サマリー
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、セクター上限適用、レジーム乗数
  - 発注株数決定（リスクベース、等配分）および単元株丸め・aggregate cap
- 注文実行
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードを環境変数で切替（ペーパートレードは専用 DB に記録）
  - リスクマネージャ、オーダーマネージャ、リコンサイラ等を組み合わせた実行フロー
- 監視・アラート
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - SQLite に監視ログを永続化（monitoring_db）
  - Kill Switch（条件により data/kill.flag を書き、ExecutionEngine に停止を促す）
- LLM 統合
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai.news_nlp）と市場レジーム判定（ai.regime_detector）
  - API リトライ・レスポンス検証・部分書き込みなどのフェイルセーフ実装
- 運用補助ツール
  - .env の対話式初期作成（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）

セットアップ手順
----------------
前提:
- Python 3.10+ を推奨（typing 表記等を使用）
- system package: libsqlite3 は標準で必要
- (任意) 仮想環境の利用を推奨

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージインストール
   必要な主なパッケージ（プロジェクト内の使用を基に列挙）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config/*.yaml の検証を行う場合に必要）
   インストール例:
   - pip install duckdb psutil openai PyYAML

   （requirements.txt があればそれを使用してください）

4. 環境変数（.env）の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
     - ウィザードは .env を生成します（.env は Git にコミットしないでください）
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 警告も厳格に扱う場合は --strict を付ける

5. ディレクトリ準備
   - data/ と logs/ ディレクトリは自動作成されますが、アクセス権限により失敗する場合があります。必要に応じて手動で作成:
     - mkdir -p data logs

主な環境変数
--------------
（代表的なもの。詳細は kabusys.config.Settings を参照）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作環境:
  - KABUSYS_ENV: development | paper_trading | live
- DB / ログ:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB)
  - LOG_LEVEL (default: INFO)
  - LOG_DIR
- OpenAI:
  - OPENAI_API_KEY
- 監視/運用:
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、run_monitoring で使用）

使い方
------
基本的な起動方法:

- ExecutionEngine（注文実行）を起動:
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV による。paper_trading の場合、MockBrokerClient が使用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録されます。
  - 実行中、停止フラグ（data/stop_requested.flag）があると即時停止します。
  - 実行は内部で data/execution.pid を作成します。

- Monitoring（監視ループ）を起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - monitoring は環境にかかわらず本番の sqlite_path を使用して監視ログを記録します（Settings の sqlite_path）。

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- .env を対話的に作る/更新:
  - python -m kabusys.config_setup

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

運用上のポイント
----------------
- 停止 / Kill Switch:
  - run_execution と run_monitoring は project_root/data/stop_requested.flag を監視して停止します（run_execution は起動時に既にある場合は起動しない）。
  - KillSwitch（risk conditions）が発動すると data/kill.flag を作成し、ExecutionEngine 側で検出・停止を促します。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にして自動クリアを無効にすることを推奨します。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力（kabusys.utils.logging_setup.setup_logging を各スクリプトで使用）。
- AI（OpenAI）:
  - ai.news_nlp.score_news, ai.regime_detector.score_regime などは OPENAI_API_KEY を必要とします。API 呼び出しはリトライ/バックオフ・レスポンス検証を実装していますが、API の料金とレート制限に注意してください。
- ペーパートレードと本番 DB の分離:
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し本番 DB と完全に分離します。

主要ファイル・ディレクトリ構成
-----------------------------
（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 設定読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数算出
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — IC / forward returns / summary
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB の初期化・アクセス層
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （存在）取引ログ監視
    - risk_monitor.py         — ドローダウン／ポジション上限監視
    - monitoring_engine.py    — 各モニタの統合実行・アラート
    - kill_switch.py          — Kill Switch 実装
    - alert_manager.py        — （存在）アラート送信管理
  - execution/
    - execution_engine.py     — 実行エンジン（EngineConfig など）
    - broker_factory.py       — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py        — ロギング一元設定
    - process_priority.py     — プロセス優先度 / CPU affinity

注意点 / トラブルシューティング
------------------------------
- ログディレクトリの作成に失敗するとファイル出力が無効化され、コンソールのみの出力になります（警告が出ます）。権限を確認してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）に依存します。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはネットワークエラーや 429 を考慮してリトライしますが、API キーや料金制限に注意してください。
- run_monitoring は Monitoring 用 SQLite を使用します（環境に関わらず既定の sqlite_path を参照）。MonitoringDB のマイグレーション処理により既存 DB にカラム追加を行います。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください。

問い合わせ
----------
- 実装上の質問や不具合はリポジトリの issue に記載してください。ログ（logs/）と .env の設定（機密情報は除く）を添付すると調査が早くなります。

-----  
この README はコードベースのドキュメントを簡潔にまとめたものです。詳細や実装の仕様は各モジュールの docstring を参照してください。