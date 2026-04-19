README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine: 発注処理・注文管理・リスク管理を担うエンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働・注文状況・リスクを定期監視し、Kill Switch を発動する仕組み
- Research / Portfolio: ファクター計算、シグナル選定、ポジションサイジング等のポートフォリオ構築ロジック
- AI モジュール: OpenAI を使ったニュースセンチメント、レジーム検出
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度設定など
- 各種ツール: ペーパートレードの検証レポート生成など

主な設計方針
- 環境変数 / .env による設定管理
- DuckDB / SQLite を使ったデータ格納（分析用・監視用で分離）
- 本番とペーパートレードのデータ分離（PAPER_TRADING 用 DB）
- 外部 API（OpenAI 等）は必要に応じて明示的に設定（フェイルセーフ設計）

機能一覧
--------
- 環境設定ウィザード（kabusys.config_setup）
  - .env の対話的作成・更新
- 設定検証ツール（kabusys.validate_config）
  - .env と config/*.yaml の事前チェック
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV に応じて本番/ペーパートレード切り替え
  - 停止フラグによる graceful shutdown（data/stop_requested.flag）
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor を定期ポーリングしてログ保存・アラート判定
  - MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60秒）
- MonitoringDB（SQLite）操作ユーティリティ（monitoring/monitoring_db）
- RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch / AlertManager による監視・Kill 判定
- Research（kabusys.research）
  - モメンタム、バリュー、ボラティリティ等のファクター計算、IC 計算
- Portfolio（kabusys.portfolio）
  - 候補選定、重み算出、ポジションサイズ計算、セクターキャップ、レジーム乗数
- AI（kabusys.ai）
  - news_nlp: OpenAI でニュースをスコアリングして ai_scores に書き込み
  - regime_detector: マクロ＋ETF MA200 で市場レジーム判定・保存
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポート生成

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - 本リポジトリに requirements.txt がない場合は主に以下が必要です:
     - duckdb, psutil, openai（AI 機能を使う場合）, PyYAML（validate_config の YAML 検証を使う場合）

4. .env の作成
   - 対話的ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で作成
   - 注意: .env を Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL としたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - デフォルトで以下のファイル／ディレクトリを想定します:
     - data/ (SQLite / PID / flag 等)
     - logs/ (ログ出力)
   - ログディレクトリは環境変数 LOG_DIR で変更可能

環境変数（主なもの）
-------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。既定: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（既定: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）のパス（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（PAPER_TRADING 環境で使用）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、既定 60）
- PAPER_FILL_MODE: ペーパートレードの fill モード（instant/partial/never/reject）

使い方（コマンド例）
-------------------
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成するとエンジンへ停止シグナルを送れます（graceful shutdown）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を上書きできます（例: export MONITOR_POLL_INTERVAL=30）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を与えて呼び出します。
  - OPENAI_API_KEY を設定して実行してください（環境変数または引数で渡す）。

停止・Kill フラグ
-----------------
- data/stop_requested.flag
  - run_monitoring と run_execution が監視している「停止要求ファイル」。存在すると起動中のループが終了します（運用者が作成）。
- data/kill.flag
  - KillSwitch が状態に応じて書き込むファイル。ExecutionEngine 停止をトリガーする目的で使用します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 推奨）。

ログ
---
- ログは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。
- setup_logging でログディレクトリを自動作成します。作成に失敗した場合はコンソール出力のみになります。

ディレクトリ構成（主なファイル）
--------------------------------
(src/kabusys 以下をルートとした重要ファイル一覧)
- __init__.py
- config.py
- config_setup.py         — .env ウィザード
- validate_config.py      — 設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — Monitoring 起動スクリプト

パッケージ別
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py
- monitoring/
  - monitoring_db.py, monitoring_engine.py, system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py, __init__.py
- research/
  - factor_research.py, feature_exploration.py, __init__.py
- ai/
  - news_nlp.py, regime_detector.py, __init__.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py, process_priority.py, __init__.py

注意事項 / 運用上のポイント
---------------------------
- .env は秘匿情報を含むため Git 管理しないでください。
- 本番では KABUSYS_ENV=live を用いると全体に影響する設定が走るため慎重に。validate_config は本番チェックに有用です。
- OpenAI 利用部分は API キーやコスト、レート制限に注意してください。API 呼び出しはリトライ等の考慮が組み込まれていますが、失敗時は安全にフォールバックします（多くはスコア 0.0 等）。
- ログディレクトリ権限や SQLite / DuckDB ファイルの書き込み権限に注意してください。

開発者向け補足
---------------
- Settings クラス（kabusys.config）を通じて設定値を取得します。自動で .env をロードする機能があり、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして抑制できます。
- MonitoringDB.init_monitoring_db は既存 DB に対するマイグレーション（カラム追加）を行います。初回起動時にテーブルが自動作成されます。
- process_priority.set_process_priority で起動時にプロセスの優先度を高く設定しています（プラットフォーム依存で失敗してもログ出力して継続します）。
- DuckDB 接続は主に research / ai / regime 機能で使用します。大規模な分析用途に最適化されています。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンスはリポジトリに同梱されている LICENSE 等を参照してください（この README 内には明示していません）。

お問い合わせ・貢献
-----------------
バグ報告、機能提案、プルリクエストはリポジトリの Issue/PR でお寄せください。README に不足や誤記があればお知らせください。