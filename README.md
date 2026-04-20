README
=====

概要
----
KabuSys は日本株向けの自動売買システムのライブラリ／運用スクリプト群です。本リポジトリは以下の機能群を含みます:

- 注文実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注・注文管理・リコンシリエーションを行う
- 監視（Monitoring）: システム稼働状況・注文ログ・リスク（ドローダウン、保有上限）を定期チェックし、Kill Switch を発動可能
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ決定・セクター制約などの純粋関数実装
- リサーチ: ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン、IC 計算、統計サマリ等
- AI モジュール: ニュースに基づく銘柄センチメント（OpenAI）や市場レジーム判定（OpenAI + ETF MA）
- ユーティリティ: 設定読み込み、.env ウィザード、設定検証、ロギング設定、プロセス優先度設定 など
- 運用ツール: ペーパートレードの検証レポート生成スクリプト など

主な設計方針:
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数 KABUSYS_ENV で切替可能
- Paper Trading は本番 DB と分離（data/paper_trading.db を使用）
- .env 自動読み込み（プロジェクトルートの .env / .env.local）をサポート（無効化可能）
- 多くの機能は副作用なしの純粋関数（テスト容易性重視）

機能一覧
--------
- run_execution: ExecutionEngine を起動 → 発注フロー・リスク管理・order_repository 等と連携
- run_monitoring: SystemMonitor をポーリングして system_status 等を永続化しアラート判定
- config_setup: 対話式ウィザードで .env を生成・更新
- validate_config: .env と config/*.yaml の存在・妥当性チェック CLI（--strict 対応）
- tools.paper_verification_report: ペーパートレード DB から運用検証レポートを生成
- portfolio.*: 候補選定・重み計算・位置決め（単元丸め・資金制約）・セクター制限・レジーム乗数
- research.*: DuckDB を使ったファクター計算（momentum/value/volatility）・将来リターン・IC 等
- ai.news_nlp: raw_news を LLM（OpenAI）でスコアリングし ai_scores へ格納
- ai.regime_detector: ETF とマクロニュースでレジーム（bull/neutral/bear）を判定し書き込み
- monitoring.*: MonitoringDB（SQLite）の永続化層、SystemMonitor/TradeMonitor/RiskMonitor、KillSwitch、MonitoringEngine
- utils.logging_setup: 統一的なログ設定（コンソール stdout + 日次ローテートログ）
- utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
前提: Python 3.9+（コードは型アノテーションや一部の機能で 3.9+ を想定）

1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd your-repo

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - 必要パッケージ例:
     - duckdb
     - psutil
     - openai
     - pyyaml（config ファイル検証用、任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 初期設定ファイル (.env) を作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に以下の必須環境変数を設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - そのほかの主な環境変数:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_DIR / LOG_LEVEL
   - .env の自動読み込みはデフォルトで有効。無効化する場合 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成
   - logs/ および data/ が自動作成されますが、必要に応じて手動で準備してください。

使い方
------
主要な実行コマンド（プロジェクトルートから）:

- ExecutionEngine を起動（常用）
  - python -m kabusys.run_execution
  - 動作:
    - Settings に基づき DB 接続
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了

- Monitoring を起動（監視プロセス）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

- .env を対話で作成 / 更新
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコアリング / レジーム判定（Python API）
  - DuckDB 接続を作り、関数を呼び出す例:
    - from datetime import date
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect('data/kabusys.duckdb')
    - score_news(conn, date(2026, 4, 10), api_key='sk-...')

  - レジーム:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026,4,10), api_key='sk-...')

注意事項 / 運用メモ
- Paper Trading と Live の DB は分離してください（デフォルトで分離されます）。
- ログ: kabusys.utils.logging_setup.setup_logging により logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能。
- Kill Switch:
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止信号を送ります。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に自動クリアされますが、本番では 0 を推奨します。
- 停止 / 停止要求:
  - run_monitoring と run_execution は data/stop_requested.flag の存在を監視しています。停止を要求するには該当ファイルを作成してください。
- モニタリング DB のスキーマは init_monitoring_db() で自動作成・マイグレーションされます（冪等）。
- OpenAI API を使う機能は API キーと通信障害対策（リトライ）が組込まれていますが、API コストと呼び出し回数は運用計画に注意してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - config.py                  — Settings / .env 自動ロード / 環境変数解決
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - execution/                 — 実行エンジン関連（broker, engine, order_manager, risk_manager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
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
    - news_nlp.py               — ニュースセンチメント（OpenAI）
    - regime_detector.py        — レジーム判定（ETF + マクロ）
  - data/                      — 既定のデータ格納場所（logs/, data/ は実行時に作成される）
  - tools/
    - paper_verification_report.py

（上記以外に config/*.yaml やドキュメントファイルが存在する可能性があります）

よくある操作例（早見）
---------------------
- .env を作って検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視を起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動（ペーパートレード）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
- config/*.yaml の内容検証は PyYAML があれば行われます（インストールがない場合は警告が表示されます）。
- DB スキーマやログの仕様はコード中の docstring とコメントを参照してください。
- テストや CI のために自動環境変数読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

お問い合わせ / 貢献
------------------
バグ報告や機能追加は Issue / PR にて受け付けます。コードスタイルやテストカバレッジに配慮した PR を歓迎します。