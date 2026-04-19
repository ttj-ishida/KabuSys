# KabuSys — README (日本語)

概要
----
KabuSys は日本株向けの自動売買システム（研究・ペーパートレード・本番運用を想定）です。  
主に以下の責務を持つコンポーネントで構成されています。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン
- Monitoring：システム状態、注文状況、リスク指標を定期的に監視・ログ化
- Research / Portfolio：ファクター計算、特徴量解析、ポートフォリオ構築ロジック
- AI モジュール：ニュース文章を LLM でスコアリング（OpenAI）して regime / sentiment を判定
- Tools：ペーパートレード検証レポート生成などのユーティリティ

主な機能
--------
- 実行環境切替（development / paper_trading / live）
- Paper Trading モード（MockBroker を用いた本番 DB とは分離された SQLite）
- システム監視（CPU/メモリ/ディスク、Execution プロセス稼働検出、データ鮮度監視）
- リスク監視（ドローダウン検出、ポジション上限監視、Kill Switch による停止）
- 発注ログ・ポジション管理（SQLite）
- DuckDB を用いたファクター・リサーチ処理（prices_daily / raw_financials を参照）
- ニュースセンチメント評価（OpenAI を利用）と市場レジーム判定
- ペーパートレード検証レポート生成（期間指定可）

前提・依存
-----------
推奨 Python バージョン: 3.10 以上（型ヒント表記に依存）  
主な外部ライブラリ（最低限）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合に推奨）

インストール例（仮）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージを pip でインストール
  - pip install duckdb psutil openai pyyaml

セットアップ手順
--------------
1. リポジトリをクローンしてルートに移動（プロジェクトルートには .git / pyproject.toml が存在する想定）。
2. Python 仮想環境を用意して依存ライブラリをインストール（上記参照）。
3. 環境変数設定（.env を作成）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
     - ウィザードが .env を生成します（.env は絶対に Git にコミットしないでください）
   - もしくは直接環境変数を設定する（CI / systemd / Docker 等）
4. 設定の検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
5. DB の初期化は各起動スクリプトが自動的に行います（monitoring 用テーブル生成など）。

重要な環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / オプション:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
  - LOG_DIR: ログ出力先（デフォルト: logs/）
  - OPENAI_API_KEY: OpenAI を使う場合は必須
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

起動・使い方
------------

- 環境セットアップ（例）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ExecutionEngine の起動
  - 本番・開発・ペーパーを env で切り替え:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 特徴:
    - paper_trading の場合、MockBrokerClient を用い data/paper_trading.db に記録（本番 DB と完全分離）
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 実行中は data/execution.pid に PID を記録
    - 停止は stop_requested.flag を作成するか、Kill Switch による data/kill.flag により停止指示が出されます

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60秒）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数引数）
  - プログラムから呼び出す例:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="xxx")
  - 注意: API 呼び出しはリトライやフェイルセーフを備えていますが、API レート制限や鍵の管理には注意してください

停止方法（運用）
- 実行中の ExecutionEngine を即座に停止したい場合:
  - data/stop_requested.flag を作成すると run_execution のループが終了します
  - KillSwitch が評価されると data/kill.flag が書き込まれ、ExecutionEngine 側で適切に停止処理されます（設定により起動時に kill.flag を消すかどうか制御できます）

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging により統一されています
- デフォルトのログ出力先: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30日保持）
- コンソールログは stdout に出力されます（cron 等からのリダイレクトを想定）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数読み込み / Settings
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 起動前チェック CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — Monitoring 起動スクリプト

サブパッケージ（主な箇所）
- ai/
  - news_nlp.py           — ニュース NLU / OpenAI 呼び出し、ai_scores への書込み
  - regime_detector.py    — 市場レジーム判定ロジック
- monitoring/
  - monitoring_db.py      — SQLite 監視 DB スキーマ/永続化層
  - system_monitor.py     — システム / データ鮮度監視
  - risk_monitor.py       — ドローダウン等のリスク監視
  - trade_monitor.py      — （注文監視・ログ）※省略部あり
  - monitoring_engine.py  — 各 monitor を束ねるループ
  - kill_switch.py        — kill.flag の生成 / 管理
  - alert_manager.py      —（通知管理: LINE 等）※該当ファイル参照
- execution/
  - execution_engine.py   — 実行エンジン（EngineConfig / run_session 等）
  - broker_factory.py     — ブローカークライアント生成（Mock / 実ブローカー）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

運用上の注意
------------
- .env ファイルは機密情報を含むため Git にコミットしないでください。
- KABUSYS_ENV を `live` にする場合は特に慎重に（validate_config で追加警告が出ます）。
- OpenAI キーや API の利用はコストが発生します。AI 機能は設定と鍵の管理を行った上で利用してください。
- モジュール群の多くは DB スキーマや外部サービス前提（prices_daily / raw_financials / raw_news 等）に依存します。データ供給（ETL）を確保してください。

開発者向けメモ
---------------
- .env 自動ロードは config.py に実装されており、プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- logging_setup.setup_logging はアプリケーションごとのログファイル名（app_name）を受け取り統一したログ管理を行います。
- 多くの処理はフェイルセーフ設計（例: API 失敗時は 0.0 フォールバック、DB マイグレーションを冪等に実行）になっています。

サンプルコマンドまとめ
--------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコアリング（プログラムから呼び出す）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, date(2026,4,10), api_key="sk-...")

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

補足
----
この README はコードベースの現状ファイルに基づく概要・運用手順をまとめたものです。詳細な実行エンジンやブローカ実装（実取引用のインターフェース）については execution/ 下の各実装を参照してください。