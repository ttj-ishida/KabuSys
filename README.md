KabuSys — 日本株自動売買システム
=================================

このドキュメントはリポジトリ内のコードベースに基づく簡易 README です。運用開始前に必ず環境変数や設定ファイルを確認してください。

プロジェクト概要
--------------
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python 製システムです。主なコンポーネントは以下です。

- ExecutionEngine：発注・注文管理・リスク管理の実行エンジン（本番／ペーパートレード対応）
- Monitoring：システム稼働状況・注文挙動・リスクを定期監視してアラートや Kill Switch を発動
- Research：DuckDB を使ったファクター計算・特徴量解析
- AI モジュール：ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI API 利用）
- Tools：ペーパートレード検証レポート等のユーティリティ

特徴（機能一覧）
--------------
- Execution:
  - 本番 / paper_trading モードを環境変数 KABUSYS_ENV で切替
  - paper_trading 時は専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離
  - 発注の管理・再整合（Reconciler）・リスク制御（RiskManager）

- Monitoring:
  - system_status, trade_logs, risk_logs, positions, dashboard を SQLite に記録
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - Kill Switch：閾値超過時に data/kill.flag を書き込み ExecutionEngine を停止可能

- Research:
  - DuckDB 上でファクター（Momentum、Volatility、Value 等）を計算
  - 将来リターン・IC（Information Coefficient）・ファクター統計の算出

- AI:
  - ニュース記事のセンチメントスコアリング（OpenAI）
  - マクロニュースと ETF（1321）MA を合成した市場レジーム判定

- ツール:
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成スクリプト

前提・必要条件
--------------
- Python 3.9 以上（コードは型注釈等を使用）
- 必須 Python パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML（設定ファイル検証を行う場合、任意）
- OS によってはプロセス優先度設定や CPU affinity が制限されることがあります（権限に依存）。

セットアップ手順
--------------
1. リポジトリをクローン:
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境の作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）:
   - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合は pip install -r requirements.txt を推奨。

4. .env の作成:
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動で .env を作成（以下「環境変数」節を参照）

5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります（exit(1)）。

主要な環境変数（主な項目）
-------------------------
（多くは .env で定義可能。省略時はコード内のデフォルトが使われる場合があります）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / 主要:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を利用する機能で必要
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（起動・CLI）
-------------------

- .env を作成・検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
    - 成功すると 0 を返します。--strict で警告も失敗扱いに。

- ExecutionEngine を起動（本番 / paper_trading を .env の KABUSYS_ENV で切替）:
  - python -m kabusys.run_execution
  - 起動時に data/execution.pid を利用／書き込みします。既に data/stop_requested.flag があれば起動せず終了します。
  - 停止は stop フラグの作成（data/stop_requested.flag）または kill.flag（data/kill.flag）で制御できます。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で調整可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用します（環境にかかわらず monitoring は本番 DB を参照）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- Research / AI 機能はライブラリ関数として利用:
  - 例: kabusys.research.calc_momentum(conn, target_date)
  - AI 機能（news_nlp / regime_detector）は OPENAI_API_KEY を設定して利用

停止・制御
----------
- 実行中の ExecutionEngine を外部から停止させる手段:
  - Kill Switch による自動停止（RiskMonitor が閾値を検出して data/kill.flag を書き込む）
  - 手動停止は data/stop_requested.flag を作成すると監視ループ / 実行スレッドが検出して安全終了します。

ログ
---
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで保存されます（logs/<app_name>.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

ディレクトリ構成
----------------
以下は主要ファイル／モジュールの一覧（リポジトリ内 src/kabusys を想定）。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定解決ロジック（自動 .env 読み込み等）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/  — 発注エンジン関連（Engine, OrderManager, RiskManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文ログ監視（stale / anomaly 検出）
    - risk_monitor.py — ドローダウン・ポジション数監視
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - kill_switch.py — kill.flag 操作ユーティリティ
    - alert_manager.py —（アラート通知を行う）※実装参照
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・投下資金スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - data/ （実行時に利用するファイル群）
    - monitoring.db（デフォルト SQLite）
    - paper_trading.db（paper_trading 用、デフォルト）
    - kill.flag / stop_requested.flag / execution.pid などの制御ファイル
  - logs/ — ログ保存先（デフォルト）

開発・運用上の注意
------------------
- 本番環境（KABUSYS_ENV=live）では kill_flag 等の挙動に注意してください（validate_config は live の場合に追加警告を出します）。
- OpenAI 等の外部 API を利用する機能は API キーとコスト管理に注意してください。API の失敗時はフォールバック実装で継続する設計になっていますが運用監視は必要です。
- データベースファイル（特に本番用）はバックアップやロックに注意して運用してください。
- process_priority や CPU affinity の設定はプラットフォーム（Windows / Linux / macOS）や権限に依存します。

よく使うコマンドまとめ
---------------------
- .env を作成する: python -m kabusys.config_setup
- 設定を検証する: python -m kabusys.validate_config [--strict]
- Execution を起動する: python -m kabusys.run_execution
- Monitoring を起動する: python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
この README はコード内ドキュメント（docstring）とソース構成に基づいて作成しています。実環境での運用前に .env の内容および config/*.yaml（存在する場合）を念入りに確認し、validate_config で問題が無いことを確かめてください。

問題報告・改善提案はリポジトリの Issue へお願いします。