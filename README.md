README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤ライブラリです。
このリポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を用いたセンチメント集計）、および運用補助ツール（設定ウィザード・設定検証・ペーパートレード検証レポート生成など）が含まれます。

主な設計方針
- 本番環境での誤発注を防ぐため、環境（KABUSYS_ENV）に応じた挙動切替をサポート
- DuckDB / SQLite を用いた時系列データ・監視ログ保存
- OpenAI（gpt-4o-mini）を利用したニュースセンチメントとレジーム判定（API キーが必要）
- ロギングやプロセス優先度設定など運用性に配慮したユーティリティ群

機能一覧
---------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - 実行中は data/execution.pid を管理し、停止フラグ（data/stop_requested.flag）で停止可能
- 監視ループ起動スクリプト: run_monitoring.py
  - システム資源・プロセス・注文状況・リスクを定期チェック
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - 監視ロジックは常に本番の sqlite_path を参照（環境に依らない）
- 監視永続化層（SQLite）: monitoring_db.py
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理
- Kill Switch: kill_switch.py
  - ドローダウンやポジション上限超過などで data/kill.flag を書き込み、ExecutionEngine 停止をトリガー
- 監視エンジン: monitoring_engine.py
  - 各 Monitor を統合しアラート送信や Kill Switch 評価を行う
- ポートフォリオ構築関連:
  - 候補選定・重み付け: portfolio_builder.py
  - セクター上限・レジーム補正: risk_adjustment.py
  - 株数決定・単元丸め・集計制御: position_sizing.py
- 研究用モジュール:
  - ファクター計算（モメンタム / バリュー / ボラティリティ）: research/factor_research.py
  - 将来リターン・IC・統計サマリ: research/feature_exploration.py
- AI 関連:
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメント算出: ai/news_nlp.py
  - 市場レジーム判定（ETF MA とマクロニュース合成）: ai/regime_detector.py
- 運用ツール:
  - 対話式 .env ウィザード: config_setup.py
  - 設定検証 CLI: validate_config.py
  - Paper Trading 検証レポート生成: tools/paper_verification_report.py
- ユーティリティ:
  - ログ設定: utils/logging_setup.py（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定: utils/process_priority.py

前提条件 / 依存
---------------
（プロジェクトルートで動作する想定）
- Python 3.9+
- 必要な外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証を有効にする場合）
- SQLite は標準ライブラリで利用可能

（インストール例）
pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローン / 展開
2. Python 仮想環境の作成と依存インストール（上記参照）
3. 初期データディレクトリを作成（必要に応じて）
   mkdir -p data logs
4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - もしくは手動で .env に必要な環境変数を設定
5. 設定検証（起動前に推奨）:
   python -m kabusys.validate_config
   - 警告を厳格に扱う場合:
     python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API トークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector が必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR — ログレベル / ログディレクトリ
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で参照）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" で有効）

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml のある階層）に .env / .env.local があれば自動で読み込みます。
- 自動読み込みを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方
------
1) .env の作成（対話式）
   python -m kabusys.config_setup

2) 設定検証
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict

3) 監視ループ起動（system monitor）
   python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を指定可能（例: export MONITOR_POLL_INTERVAL=30）
   - 監視ループは data/stop_requested.flag が存在すると終了します（運用側で作成）
   - 監視は環境にかかわらず本番の sqlite_path を使用します（監視データは共通）

4) 実行エンジン起動（ExecutionEngine）
   python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、Mock ブローカーを使用し data/paper_trading.db を利用
   - 起動時に data/stop_requested.flag が存在する場合はエンジンを起動せず終了します
   - 実行中、data/execution.pid に PID を書きます。停止は stop flag 作成で行えます

5) Paper Trading 検証レポート生成
   python -m kabusys.tools.paper_verification_report
   - 期間指定:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で指定可

6) AI 系処理
   - ニュースのセンチメントスコア算出:
     kabusys.ai.score_news(conn, target_date, api_key=...)
     （DuckDB 接続を渡して使用）
   - 市場レジーム判定:
     kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - これらは OPENAI_API_KEY または引数で API キーを与える必要があります

運用メモ / 停止・Kill Switch
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ（存在でループ停止）
  - data/kill.flag: KillSwitch が書き込むフラグ。ExecutionEngine の起動/停止ロジックで参照
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動で削除します（本番では 0 推奨）
- ログは logs/<app_name>.log に日次ローテートで保存されます（utils.logging_setup を使用）

ディレクトリ構成
----------------
以下は主要モジュールと役割の一覧（src/kabusys 以下）。実際のファイルはこの README に付随するコードツリーを参照してください。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env の読み込み・Settings 抽象化
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID 管理、paper_trading 分離）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py : ログの統一設定（stdout + 日次ファイル）
    - process_priority.py : プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py : SQLite テーブル初期化と読み書きユーティリティ
    - system_monitor.py  : システム資源・データ鮮度チェック
    - trade_monitor.py   : 注文滞留や約定異常検出（コード内参照）
    - risk_monitor.py    : ドローダウン・ポジション上限監視
    - kill_switch.py     : kill.flag 管理
    - monitoring_engine.py : 各 Monitor をまとめる
    - alert_manager.py   : （アラート送信ロジック、LINE 等を想定）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 実行エンジンと注文関連ロジック（run_execution から組み立てて起動）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py       : ニュースセンチメント（OpenAI）処理
    - regime_detector.py: レジーム判定（ETF MA + マクロニュース）
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成
  - data/ (運用環境に作成される想定)
    - monitoring.db (SQLite, default)
    - paper_trading.db (paper trading 用 db)
    - kill.flag, stop_requested.flag, execution.pid
  - logs/ (ログ出力先)

開発・デバッグのヒント
---------------------
- validate_config.py は YAML パースに PyYAML が必要ですが、未インストールでもスキップして動作します（警告出力）。
- DuckDB 関連の処理はデータベースのスキーマ・テーブル（prices_daily, raw_financials, raw_news など）に依存します。テスト用データを用意してください。
- OpenAI 呼び出し部はユニットテスト時に差し替え可能（関数を patch してモックする設計）。
- ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続します。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE（存在する場合）を参照してください。

お問い合わせ・貢献
-----------------
- バグ報告・機能提案は Issue に記載してください。プルリク歓迎です。README やドキュメントに追記すべき点があれば PR をお寄せください。

以上。README に書かれているコマンド例やファイル名はリポジトリの実ファイルと照らし合わせてご利用ください。