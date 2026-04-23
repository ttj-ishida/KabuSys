KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリです。本リポジトリは以下の機能群を提供します。
- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（銘柄選定・重み算出・ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量解析）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- 運用支援ツール（環境設定ウィザード、設定検証、ペーパートレード検証レポート）

本 README はコードベース（src/kabusys 以下）の利用方法と構成をまとめたものです。

主な特徴
--------
- 本番 (live) / ペーパートレード (paper_trading) / 開発 (development) を環境変数で切替可能
- Paper Trading は完全に本番 DB と分離（data/paper_trading.db を使用）
- DuckDB を用いたリサーチ向け高速分析（prices_daily, raw_financials 等を想定）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントおよびレジーム判定（リトライ・検証ロジック付き）
- 監視サイクル（MonitoringEngine）と Kill Switch による安全停止機構
- ログは標準出力と日次ローテートファイル（logs/*.log）へ出力

前提条件（主要依存パッケージ）
----------------------------
- Python 3.10+
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml の検証に使用）
※ 開発環境では requirements.txt 等を用意している可能性があります。必要パッケージをインストールしてください。

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - git clone ... && cd <project-root>

2. 仮想環境を作成して依存パッケージをインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt  （存在しない場合は手動で duckdb, psutil, openai 等をインストール）

3. .env の作成（まずはウィザードで）
   - python -m kabusys.config_setup
     - 対話式で J-Quants / kabu API のトークンや DB パス等を設定して .env を生成します。
   - 設定後、検証:
     - python -m kabusys.validate_config
       --strict オプションを付けると警告も失敗扱いにできます

4. デフォルトのデータディレクトリ作成
   - data/ フォルダは起動時に自動作成される場合がありますが、必要に応じて作成しておくと良いです。
   - デフォルトの SQLite / DuckDB パス:
     - data/monitoring.db （監視用 SQLite）
     - data/paper_trading.db （paper_trading 用 SQLite）
     - data/kabusys.duckdb （DuckDB）

重要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境。development / paper_trading / live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能（ニュース NLP / レジーム判定）で必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発向け）

実行方法（主要スクリプト）
-------------------------
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明: ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録します。
  - 停止制御: data/stop_requested.flag が作られると安全に停止します。PID は data/execution.pid に保存されます。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor のポーリングループを開始します。デフォルトポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可。
  - 監視は本番 sqlite_path（監視 DB）を常に使用します（環境に依存しない）。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config [--strict]
  - .env と config/*.yaml の基本チェックを行います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止 / Kill Switch 周り
-----------------------
- Kill Switch は data/kill.flag に文字列を書いて ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START 設定に基づきクリアすることが可能）。
- run_execution と run_monitoring の両方で data/stop_requested.flag を使ってローカル的な停止を検出します（例: 管理用 stop ファイル）。

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging を全スクリプトから利用しています。
- デフォルトでは標準出力（stdout）と logs/<app_name>.log（日次ローテーション、30日保持）へ出力されます。
- ログディレクトリは LOG_DIR 環境変数、あるいはデフォルトの logs/ を使用します。

簡単な使い方例
----------------
1. .env を作成（ウィザード）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. ペーパートレードでエンジン起動（例）
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution

4. 監視プロセスを起動
   - python -m kabusys.run_monitoring
   - モニタリング間隔を 30 秒にする場合:
     - export MONITOR_POLL_INTERVAL=30
     - python -m kabusys.run_monitoring

5. Paper Trading レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

主要ディレクトリ構成
--------------------
以下は src/kabusys 以下の主要ファイル / モジュールと役割の一覧です（抜粋）。

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（自動 .env ロード等）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前チェック CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

  - execution/              — 発注エンジン関連（OrderManager など）
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite 書き込み層
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — 注文状況監視（滞留注文など）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — kill.flag 管理
    - monitoring_engine.py  — 各モニタを束ねる実行ループ
    - alert_manager.py      — LINE 等への通知（実装参照）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数（ポジションサイズ）計算
    - risk_adjustment.py    — セクター制限、レジーム乗数
  - research/
    - factor_research.py    — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py    — マクロ + ETF MA によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート作成ツール
  - utils/
    - logging_setup.py      — ロギング設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ
    - （その他ユーティリティ群）

補足・注意事項
--------------
- OpenAI を使用する機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しはリトライやレスポンス検証を行いますが、API 使用に伴うコスト・レイテンシには注意してください。
- 本番環境（KABUSYS_ENV=live）での運用前には validate_config にて必須項目・警告を必ず確認してください（LINE 通知設定や Kill Switch 設定など）。
- .env は機密情報を含むため絶対に Git にコミットしないでください。

ライセンス / 貢献
-----------------
（必要に応じてここにライセンス情報や貢献方法を追記してください）

以上が主要な導入ガイドです。必要があれば各モジュールの詳しい利用方法（API、関数仕様、例）をさらに生成します。どの部分を詳細に書けばよいか教えてください。