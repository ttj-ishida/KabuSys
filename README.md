KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買システムのコアライブラリ群です。戦略の研究・ファクター計算、ポートフォリオ構成、発注エンジン（ExecutionEngine）、および監視（Monitoring）周りのユーティリティを含みます。本 README はコードベース（src/kabusys 以下）を基に、概要・機能・セットアップ手順・主要な使い方・ディレクトリ構成を日本語でまとめたものです。

要点
- Python パッケージ名: kabusys
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 実行スクリプトはモジュールとして起動（python -m kabusys.<module>）
- 設定は .env（または環境変数）で管理。対話式ウィザードあり。

プロジェクト概要
----------------
KabuSys は、以下の主要機能を持つ自動売買プラットフォームのコアライブラリです。
- 研究（research）: ファクター計算（モメンタム、ボラティリティ、バリュー等）、特徴量解析、IC計算など（DuckDB を用いた分析）。
- ポートフォリオ構築（portfolio）: 候補選定、重み算出、ポジションサイズ計算、セクター制限やレジーム乗数適用。
- 発注（execution）: ExecutionEngine・OrderManager・RiskManager 等による発注制御（本番 / ペーパートレード切替）。
- 監視（monitoring）: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine による定期監視、監視ログは SQLite に永続化。
- AI 支援（ai）: ニュース NLP によるセンチメントスコアリング、レジーム判定（OpenAI API を利用）。
- ツール群: .env ウィザード、設定検証、Paper Trading の検証レポート等。

主な機能一覧
------------
- 環境設定
  - 対話式ウィザード: python -m kabusys.config_setup（.env 作成/更新）
  - 設定検証 CLI: python -m kabusys.validate_config（必須環境変数・ファイル・パス等をチェック）
- 発注エンジン
  - run_execution スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録（本番 DB と分離）
- 監視エンジン
  - run_monitoring スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、必要に応じて kill.flag を書き込み ExecutionEngine を停止させる
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 研究・解析
  - DuckDB を参照してファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン・IC 計算・統計サマリー（feature_exploration）
- ポートフォリオ構築
  - 候補選定（select_candidates）、等配分 / スコア配分、リスクベースサイズ計算（calc_position_sizes）
  - セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
- AI / ニュース
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存（ai.news_nlp.score_news）
  - マクロニュース＋ETF MA を用いたレジーム判定（ai.regime_detector.score_regime）
- ユーティリティ
  - 統一的なログ設定（kabusys.utils.logging_setup.setup_logging）
  - プロセス優先度設定（kabusys.utils.process_priority）

セットアップ手順（開発環境）
-------------------------
前提:
- Python 3.10+（型注釈に依存するため推奨）
- Git クローン済み（プロジェクトルートに src/ がある構成を想定）

1. リポジトリをクローン
   - git clone <repo>
   - cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML をパースする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（ルート直下）
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（デフォルトは括弧内）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - その他は src/kabusys/config.py を参照

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

初回起動時の注意
- run_execution は KABUSYS_ENV が paper_trading の場合、paper_trading 用の sqlite を使用して本番 DB と分離します。
- monitoring は本番 sqlite_path（SQLITE_PATH）を常に使用する設計になっている箇所があります（run_monitoring の実装参照）。
- kill.flag / stop flag / pid ファイル:
  - data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine は起動時にクリア設定があれば抑制）
  - data/stop_requested.flag: 起動中のループを止める手動フラグ（run_execution/run_monitoring が参照）
  - data/execution.pid: ExecutionEngine の PID ファイル

使い方（主要スクリプト）
------------------------

1) 設定ウィザード（.env 作成）:
   - python -m kabusys.config_setup

2) 設定検証:
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict

3) ExecutionEngine 起動（本番/ペーパー切替は KABUSYS_ENV）:
   - python -m kabusys.run_execution
   - ペーパートレードで起動したい場合:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 実行中に data/stop_requested.flag を作るとエンジンに停止信号を送ります（run_execution はこのフラグを監視してエンジンを停止します）。

4) Monitoring 起動:
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変更したい場合:
     - export MONITOR_POLL_INTERVAL=30  # 単位: 秒
   - run_monitoring は data/stop_requested.flag を検出すると監視ループを終了します。

5) Paper Trading 検証レポート（ツール）:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH や --db で指定可能）

6) AI 機能（ライブラリ呼び出し）:
   - ニュース NLP（例、Python REPL から）
     from kabusys.ai.news_nlp import score_news
     score_news(conn, target_date, api_key="...")

   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     score_regime(conn, target_date, api_key="...")

ログ出力
-------
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。
- デフォルトでは logs/<app_name>.log に日次ローテーション（30 日保持）で出力され、コンソール（stdout）にも出力されます。
- app_name は起動スクリプトごとに "execution" / "monitoring" 等で呼ばれます。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 配下の主要モジュール一覧（抜粋）と役割です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py     — 候補選定、重み算出
    - position_sizing.py       — 発注株数計算・集約キャップ対応
    - risk_adjustment.py       — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum, volatility, value）
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（ETF + マクロニュース）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py        — システム状態・データ鮮度監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - trade_monitor.py         — （トレード監視：滞留注文等の検出）
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各 monitor を束ねる実行ループ
    - alert_manager.py         — （アラート送信管理、外部通知用）
  - execution/
    - execution_engine.py      — 発注エンジン本体
    - order_manager.py         — 発注管理
    - order_repository.py      — 注文 DB 操作
    - reconciler.py            — ブローカーとローカルの整合処理
    - broker_factory.py        — 本番 / モック ブローカーの生成
    - risk_manager.py          — 発注前のリスク制御
  - monitoring/                — 上記の監視関連
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度・CPU affinity 設定に関するユーティリティ

（注）一部補助モジュール（例: AlertManager の実装、TradeMonitor の全実装など）は抜粋省略されています。実際の通知先実装や BrokerClient 実装などは本プロジェクトの別モジュール/設定に依存します。

運用上の注意
------------
- KABUSYS_ENV=live の場合は本番環境です。必須トークンや LINE 通知設定等を十分に確認してください（validate_config の live チェックを参照）。
- kill.flag を自動的にクリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です（デフォルト 0 を推奨）。
- run_monitoring は monitoring 用 DB（SQLITE_PATH）を使用して監視ログを保存します。監視は本番 DB と同じ sqlite_path を参照するよう設計されている点に留意してください。
- OpenAI API 等外部サービスを利用する機能は API キーやレート制限に注意して運用してください。API 呼び出しはリトライやフォールバックを備えていますが、費用や遅延リスクは別途管理してください。

開発・テスト
-------------
- 多くの関数は純粋関数（副作用を持たない）で実装されており、ユニットテストが容易です（例えば portfolio や research の関数群）。
- AI API を使う関数は内部の API 呼び出しをラップしており、ユニットテスト時は該当関数をモックして差し替える設計になっています（例: _call_openai_api の差し替え）。

参考: よくあるコマンドまとめ
---------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

最後に
-----
この README は src/kabusys のコードを元に作成しています。実運用に移す場合は config/*.yaml（存在する場合）や、実際の Broker クライアント、AlertManager 実装、デプロイ方法（systemd / Docker / Supervisor 等）に合わせた追加設定・安全対策を推奨します。必要であれば、各モジュールの API 仕様（関数引数・戻り値）や運用手順書も別途作成します。必要な箇所を指定してください。