README
=====

概要
----
KabuSys は日本株向けの自動売買（リサーチ・ポートフォリオ構築・発注・監視）を目的とした Python コードベースです。
本リポジトリには以下の主要機能が含まれます。

- データ解析 / ファクター計算（DuckDB を使用）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- ExecutionEngine（発注ロジック、ブローカークライアント抽象化、ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk の定期チェック、アラート・Kill Switch）
- AI を使ったニュース NLP（OpenAI を利用したセンチメントスコアリング）
- 各種 CLI ツール（環境ウィザード、設定検証、Paper Trading レポート生成）

主な特徴
--------
- 環境分離: KABUSYS_ENV による実行モード切替（development / paper_trading / live）。ペーパートレード時はブローカーをモックし、専用の SQLite DB に記録します。
- 冪等性を意識した DB 初期化 / マイグレーション（monitoring DB の init を提供）。
- DuckDB を分析レイヤに使用（prices_daily / raw_financials 等のテーブルを想定）。
- OpenAI（gpt-4o-mini）によるニュースセンチメント / レジーム判定機能（API キーで有効化、失敗時はフェイルセーフ）。
- シンプルな運用用フラグファイル（data/kill.flag、data/stop_requested.flag）でプロセス停止を実現。
- 統一ログ設定：stdout と 日次ローテートログ（logs/<app>.log）を使用。

前提 / 必要パッケージ
--------------------
（プロジェクトの requirements.txt がある場合はそちらを参照してください。以下は主要な依存例）
- Python 3.9+
- duckdb
- psutil
- openai (AI機能を使う場合)
- PyYAML（config/*.yaml の構文チェックを行いたい場合）

セットアップ手順
--------------
1. リポジトリをクローン / 配置
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai
   - （YAML検証を使う場合）pip install pyyaml
   - 実際のプロジェクトでは requirements.txt があれば pip install -r requirements.txt
4. 環境変数の準備
   - .env を作成する（手動または下記ウィザードで作成）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意（AI 機能）:
     - OPENAI_API_KEY
   - 主要なデフォルト値:
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO

環境設定ウィザード（対話式）
------------------------
.env を対話式に作成・更新するには config_setup を利用します。
- 実行例:
  - python -m kabusys.config_setup
  - オプションでファイルを指定: python -m kabusys.config_setup --env-file path/to/.env
- 自動で .env を生成／上書きします（.env は Git にコミットしないでください）。

設定検証
--------
起動前に設定不備をチェックする CLI が用意されています。
- 実行:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)
- 必須環境変数、KABUSYS_ENV 値、DB パスの親ディレクトリ存在、config/*.yaml のパース（PyYAML 必須）などを検証します。

主要な実行方法（使い方）
----------------------

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と分離します。
    - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
    - 実行中は data/stop_requested.flag を検知するとエンジンを停止します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings.sqlite_path（デフォルト data/monitoring.db）へ接続。Monitoring は環境にかかわらず本番 sqlite_path を使用します（監視履歴の一元化）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
    - data/stop_requested.flag が存在することでループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力: コンソールに統計と PASS/FAIL 判定を表示

ライブラリ・モジュールの使い方（概要）
------------------------------------
- kabusys.config.Settings
  - 環境変数をラップした設定クラス。プロジェクト内で settings = Settings() が提供されています。
  - 自動でプロジェクトルートの .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

- kabusys.portfolio
  - portfolio_builder.select_candidates / calc_equal_weights / calc_score_weights
  - position_sizing.calc_position_sizes
  - risk_adjustment.apply_sector_cap / calc_regime_multiplier

- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - 分析は DuckDB 接続を渡して prices_daily / raw_financials を参照して実行

- kabusys.ai
  - news_nlp.score_news(target_date, conn, api_key=...)
  - regime_detector.score_regime(target_date, conn, api_key=...)
  - OpenAI API キー（OPENAI_API_KEY）が必要

監視・停止フロー（フラグファイル）
------------------------------
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py などの外側からプロセスを即時終了させたい場合に利用します。
  - スクリプトは存在検査を行い、検出するとループを終了します（グレースフルシャットダウン）。

- data/kill.flag
  - KillSwitch（監視サブシステム）が条件を満たした場合に書き込み、ExecutionEngine に対して停止を促すためのフラグです。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合は自動クリアされる設定があります（本番では 0 を推奨）。

DB / ログについて
-----------------
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb (Settings.duckdb_path)
  - SQLite (monitoring): data/monitoring.db (Settings.sqlite_path)
  - Paper trading SQLite: data/paper_trading.db (Settings.paper_sqlite_path)
- monitoring_db.init_monitoring_db() により必要テーブルが作成され、既存スキーマに対する軽微なマイグレーション（列追加）も行われます。
- ログ:
  - デフォルトは logs/<app_name>.log に日次ローテーションで保存（30日分保持）
  - 標準出力（stdout）にも出力されます
  - setup_logging(app_name="execution" など) で統一設定

典型的な運用コマンド例
--------------------
- 初期設定ウィザードと検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 開発用に監視を一度だけ実行（テスト）:
  - テスト用に MonitoringEngine を直接利用するユーティリティがあるため、テストスクリプトから run_once 相当を呼ぶことができます（ユニットテスト向け）。

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境設定読み込み / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ループ起動スクリプト

  - execution/                — 発注エンジン周り（ブローカー・OrderManager 等）
  - monitoring/
    - monitoring_db.py        — monitoring DB の初期化・永続化層
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — 発注ログ監視（存在）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の生成
    - monitoring_engine.py    — 各モニタの統合ポーリング
    - alert_manager.py        — アラート送信（存在）
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

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定することを強く推奨します。自動クリアすると誤って停止条件を無視して起動してしまうリスクがあります。
- monitoring は常に Settings.sqlite_path を使用します（監視ログは環境にかかわらず本番 sqlite_path を用いる設計）。
- OpenAI API を使用する機能は API 呼び出しに失敗した場合、フェールセーフで継続するよう実装されていますが、API キーやコスト管理には注意してください。
- .env は秘密情報（トークン等）を含むため決してリポジトリにコミットしないでください。

開発 / テストのヒント
--------------------
- Settings はプロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を自動読み込みします。テストから環境自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API コールや外部副作用はモック化しやすいように設計されています（OpenAI 呼び出し関数等は差し替え可能）。

バージョン
---------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

お問い合わせ / 追加情報
---------------------
各モジュールに詳細なドキュメント文字列（docstring）が記載されています。拡張や運用設定・テストシナリオの作成はこれらを参照してください。

--- 
以上がこのコードベースの基本的な README になります。必要であれば、導入手順をより詳しく（systemd / cron / Docker コンテナでの運用例やサンプル .env）追記します。どの形式（簡易版 / 運用向け / 開発向け）を優先しますか？