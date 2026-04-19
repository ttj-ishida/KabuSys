KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買に関する各種コンポーネント（注文実行、監視、リサーチ / ファクター計算、AI ニュース解析、ポートフォリオ構築など）をまとめた Python コードベースです。  
このリポジトリは以下の責務を持つモジュール群で構成されています:

- ExecutionEngine（発注実行・リスク管理）
- Monitoring（システム稼働監視・アラート・Kill Switch）
- Research（ファクター計算・特徴量解析）
- AI（ニュースの NLP によるセンチメント算出、レジーム判定）
- Portfolio（候補選定・重み計算・株数算出）
- Tools（検証レポート生成・設定ウィザード・設定検証）

主な機能
--------
- 発注エンジン（本番 / ペーパートレードの分離）
  - KABUSYS_ENV により paper_trading / live / development を切替可能
  - paper_trading の場合は専用の SQLite（data/paper_trading.db）へ記録
- 監視サブシステム
  - CPU / メモリ / ディスク / プロセス生存の定期検査
  - トレードログ・リスクログ・ダッシュボード永続化（SQLite）
  - Kill Switch（条件を満たすと data/kill.flag を作成して Execution を停止）
- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリューなどのファクター算出（DuckDB 上の prices_daily / raw_financials）
  - forward returns、IC（情報係数）、統計要約等
- AI モジュール
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメント集約（ai_scores へ書込）
  - マクロニュースを使った市場レジーム判定（market_regime テーブルへの書込）
  - API 呼び出しはリトライ・バックオフ・レスポンス検証を実装
- ポートフォリオ構築
  - シグナルから候補選定、等加重/スコア加重、リスクベースのポジションサイズ算出
  - セクター上限やレジーム乗数の適用
- 運用支援ツール
  - .env 対話式ウィザード（config_setup）
  - 起動前チェック（validate_config）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report）

セットアップ
----------
1. Python と依存ライブラリのインストール（例）
   - 推奨: Python 3.9+
   - 主要依存パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を有効にする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

2. プロジェクトルートに .env を配置
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成
   - 自動読み込み:
     - 本コードは .env/.env.local を自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

3. 主要な環境変数（必須 / 推奨）
   - 必須:
     - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - LOG_DIR: logs/
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）

4. ログディレクトリ
   - デフォルト: logs/
   - ログ設定は kabusys.utils.logging_setup.setup_logging を使用し、ログは logs/<app_name>.log に日次ローテートで保存されます。

使い方
------
- 設定ウィザード（.env 作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパー共通スクリプト:
    - python -m kabusys.run_execution
  - 動作挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 停止方法: data/stop_requested.flag（停止を検知して順次シャットダウン）
    - 実行中 pid は data/execution.pid に書き出されます

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。1 未満や不正値はデフォルトにフォールバック。
  - 監視は Settings.sqlite_path（監視用 DB）に接続し、SystemMonitor / TradeMonitor / RiskMonitor を定期実行します。
  - 監視は常に本番 sqlite_path を参照（環境にかかわらず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（--db が優先）

- AI モジュール（プログラム的利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - 引数 conn は DuckDB の接続オブジェクト
    - api_key が None の場合は環境変数 OPENAI_API_KEY を利用
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - OpenAI を呼びマーケットレジームを計算して DuckDB の market_regime に書込

注意点 / 運用メモ
----------------
- DB の分離
  - paper_trading は本番データと分離するため専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
- Kill Switch
  - KillSwitch は設定された flag_path（デフォルト data/kill.flag）に理由テキストを書き込んで ExecutionEngine に停止を促します。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 は危険（自動でクリアされるため誤起動の可能性有り）
- ローカル自動読み込み
  - リポジトリルート（.git または pyproject.toml が存在する場所）を基に .env/.env.local を自動読み込みします。
- OpenAI の利用
  - OpenAI API 呼び出し時は retry/backoff を実装していますが、API キー・コストに注意してください。
- 監視の停止フラグ
  - run_monitoring と run_execution の両方で "stop_requested.flag"（data/stop_requested.flag）を見てループ終了やエンジン停止を行います。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は主要なモジュールとファイルの概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動読み込み）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (注: 実装がある場合)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

（上記は実装済みファイルの抜粋です。詳細は src/kabusys 配下を参照してください。）

開発・デバッグのヒント
--------------------
- ログレベルは LOG_LEVEL 環境変数で変更できます（例: export LOG_LEVEL=DEBUG）。
- ログ出力先は LOG_DIR（デフォルト logs/）。ファイルハンドラ作成に失敗した場合はコンソールのみで継続します。
- 設定検証ツール python -m kabusys.validate_config は依存パッケージ（PyYAML）がない場合 YAML の検証をスキップします。
- テスト時には環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動 .env ロードを無効化できます。
- OpenAI 呼び出しをユニットテストする場合、kabusys.ai.news_nlp._call_openai_api 等を patch して外部 API をモックしてください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（存在する場合）。

補足
----
この README はコードベースの主要な使い方と構成をまとめたものです。細かな実装や追加のユーティリティは該当モジュールのドキュメント（ソース内 docstring）を参照してください。質問や追加情報が必要であればお知らせください。