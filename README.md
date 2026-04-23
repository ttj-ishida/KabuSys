KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコードベースです。  
本 README はコードベースに含まれる起動スクリプト・設定ユーティリティ・主要モジュールの使い方やセットアップ手順を簡潔にまとめたものです。

前提
----
- Python 3.10+ を想定（typing, match 等の利用を考慮）
- 必要な外部ライブラリ（例: duckdb, psutil, openai, PyYAML 等）は requirements.txt 等で管理する想定
  - 実行に最低限必要なライブラリ: duckdb, psutil
  - AI 機能を使う場合: openai
  - config/*.yaml の検証を行う場合: PyYAML

プロジェクト概要
--------------
KabuSys は次のような責務をもつコンポーネント群で構成されています。
- ExecutionEngine: 発注やリスク管理を行うエンジン（run_execution.py）
- Monitoring: システム稼働監視・注文監視・リスク監視・Kill Switch（run_monitoring.py / monitoring/*）
- Research & Feature: ファクター計算・特徴量探索（research/*）
- Portfolio construction: 候補選定・重み算出・株数決定・リスク調整（portfolio/*）
- AI モジュール: ニュース NLP によるセンチメント評価、レジーム判定（ai/*）
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度など（utils/*）
- ツール: ペーパートレード検証レポート生成など（tools/*）

主な機能一覧
--------------
- 実行環境切替（KABUSYS_ENV: development / paper_trading / live）
- ExecutionEngine の起動・停止（PID / stop フラグで制御）
- 監視ループ（CPU/メモリ/Disk、プロセス存在、データ鮮度、注文状況、ドローダウン等）
- Kill Switch：重大リスク検出時に ExecutionEngine 停止フラグを書き込む
- Paper Trading モード：Mock ブローカーを用い、paper_trading 用 DB に記録（本番 DB と完全分離）
- DuckDB を用いたリサーチ（ファクター計算、forward returns、IC、統計要約）
- OpenAI API と連携したニュースセンチメント評価、レジーム判定（gpt-4o-mini 想定）
- 設定ウィザード（.env 生成）と設定検証 CLI
- Paper Trading 検証レポート生成ツール

セットアップ（ローカル開発向け）
--------------------------------
1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合、少なくとも duckdb, psutil をインストールしてください）
     - pip install duckdb psutil

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants トークンや kabu API パスワード、DB パス、KABUSYS_ENV などを設定します
   - 自動ロード: .env/.env.local は起動時に自動で読み込まれます
     - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を含めて失敗扱いしたい場合: python -m kabusys.validate_config --strict

6. ディレクトリ / ファイル確認
   - data/ : DB ファイルやフラグ、PID を置くディレクトリ（起動時に自動作成されることが多い）
   - logs/ : ログファイル（setup_logging により生成）

主要環境変数（代表）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60） — run_monitoring.py で参照
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=そのまま）

使い方（主要スクリプト）
------------------------

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可（デフォルト: 60）
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を参照する（環境に依存しない）
    - デフォルトで logs/monitoring.log に日次ローテートされたログを出力

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録
    - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）
    - 停止フラグ: data/stop_requested.flag が存在すると停止処理を行う

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール呼び出し（プログラムからの利用）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)

停止 / Kill Switch / フラグ
-------------------------
- data/kill.flag
  - KillSwitch が検知した重大リスク（大幅ドローダウン等）を示すフラグ。存在すると ExecutionEngine 停止を促す設計。
  - 起動時に自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1（本番では 0 を推奨）

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が監視している「停止リクエスト」フラグ。存在するとスクリプトはループを抜けて終了します。

ログ
---
- 共通のログ初期化関数: kabusys.utils.logging_setup.setup_logging(app_name=...)
  - stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）を設定
  - LOG_DIR 環境変数でログディレクトリを変更可

ディレクトリ構成（抜粋）
-----------------------
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（DB 初期化 & CRUD ユーティリティ）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留や約定異常検出（ファイル内存在）
    - risk_monitor.py        — ドローダウン・ポジション上限チェック
    - kill_switch.py         — フラグ書き込みによる停止判定
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — （アラート送信用ユーティリティ）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py      — 実ブローカー / Mock ブローカー のファクトリ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — momentum/volatility/value の計算
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py  — Paper Trading レポート生成
  - utils/
    - logging_setup.py
    - process_priority.py
    - その他ユーティリティ

設計上の注意点 / 運用メモ
-------------------------
- .env は機密情報を含むため Git 管理しないこと（config_setup.py のヘッダにも明記あり）。
- Settings クラスは .env と環境変数を透過的に扱います。自動ロードはプロジェクトルート（.git or pyproject.toml を探索）を基準に行われます。
- run_execution / run_monitoring はプロセス優先度を高めに設定する処理を行います（psutil が必要）。
- Paper Trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 機能を有効にする場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フェイルセーフ（失敗時に代替値）を考慮した実装になっていますが、API コストやレート制限に注意してください。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等に作られており、既存カラムがない場合は ALTER TABLE で追加します。
- 監視周り（Monitoring）は監視結果のログ・アラート・Kill Switch を通じて実行系を安全に止められるようになっています。運用時は alert（LINE など）の設定を必ず確認してください（validate_config の live ガード参照）。

よくある操作例
---------------
- 監視をデフォルト間隔で起動（バックグラウンド例）
  - nohup python -m kabusys.run_monitoring &

- 実行エンジンを paper_trading モードで起動
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper 検証レポート（2026-04-01 から 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
- この README はコードベースの理解を助ける要約ドキュメントです。実運用前に必ず validate_config を実行し、.env の内容を確認してください。
- 貢献方法やライセンスはリポジトリのトップレベルにある LICENSE / CONTRIBUTING を参照してください（無い場合はプロジェクト管理者に確認）。

付録: 例 .env（最小）
-------------------
# KabuSys minimal .env (例)
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

以上。運用・開発上の不明点があれば、どのスクリプト／機能について深堀りしたいか教えてください。README の補足（実行フロー図、環境変数完全リスト、サンプル .env.example 生成等）も作成できます。