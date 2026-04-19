README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリは:
- 注文実行エンジン（ExecutionEngine）
- システム監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算
- 研究用ファクター計算・特徴量解析
- ニュース NLP / 市場レジーム判定（OpenAI を利用）
- 環境設定ウィザード・設定検証ツール
などを含むモジュール群で構成されています。

主な特徴
--------
- 実行環境を KABUSYS_ENV（development / paper_trading / live）で切替可能
- Paper Trading モードは MockBrokerClient と専用 SQLite DB（data/paper_trading.db）で本番と完全分離
- DuckDB を用いた分析用データストア（デフォルト: data/kabusys.duckdb）
- SQLite を用いた監視・ログ永続化（デフォルト: data/monitoring.db）
- モジュール化されたポートフォリオ構築・リスク調整・ポジションサイズ計算（純粋関数）
- OpenAI を利用したニュースセンチメント & レジーム判定（フェイルセーフで実行）
- 対話式 .env ウィザード（config_setup）、起動前設定検証ツール（validate_config）
- 日次ローテーションログ（logs/*.log）と統一ロギング設定

サポートする外部依存（代表）
--------------------------------
- Python 3.10+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（config/*.yaml の深い検証を行う場合）
- 標準ライブラリ: sqlite3, threading, logging など

インストール（例）
------------------
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai

   オプション（YAML 検証）
   - pip install pyyaml

設定（.env）
-----------
プロジェクトルートに .env を置くか、環境変数で設定します。推奨は対話式ウィザードで .env を作ること。

対話式ウィザード:
- python -m kabusys.config_setup
  → J-Quants トークン、kabu API パスワード、KABUSYS_ENV、DB パス等を対話形式で作成/更新します。

設定検証:
- python -m kabusys.validate_config [--strict]
  → .env と config/*.yaml の基本チェック。--strict を付けると警告もエラー扱いにします。

重要な環境変数（抜粋・デフォルト）
-------------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番で kill.flag を自動クリアするか（0/1、推奨 0）

使い方（エントリポイント）
--------------------------

1) 実行エンジン（ExecutionEngine）起動
- 簡単起動:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag があれば起動せず終了します。
  - data/execution.pid に PID を書く（設定で変更可）。
  - 外部停止は data/stop_requested.flag を作成するか、監視側の KillSwitch が data/kill.flag を書き込むことで行います。

2) 監視ループ起動
- python -m kabusys.run_monitoring
- 特記事項:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を使用（環境に関係なく同一監視 DB に書きます）。
  - 停止は data/stop_requested.flag を作成することでループを抜けます。

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ統計、その他検証結果と PASS/FAIL 判定

ロギング
--------
共通のロギングセットアップ:
- kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します。
- 出力先: stdout（コンソール）と日次ローテーションファイル logs/<app_name>.log（デフォルト）
- ログレベルは LOG_LEVEL 環境変数または引数で制御します。

停止・Kill Switch
-----------------
- data/stop_requested.flag: 手動で作成すると run_execution / run_monitoring のループが終了します（スクリプトで参照）。
- data/kill.flag: KillSwitch（監視）により書き込まれると ExecutionEngine に停止シグナルを送ります。KillSwitch はドローダウン超過・ポジション上限超過などの条件で書き込みます。
- KILL_FLAG_CLEAR_ON_START 環境変数が "1" の場合、起動時に kill.flag が自動クリアされます（本番では 0 推奨）。

データベース・マイグレーション
------------------------------
- monitoring_db.init_monitoring_db が起動時に呼ばれ、必要なテーブルとインデックスを作成します（冪等）。
- 既存 DB にカラムがない場合の簡単なマイグレーション（例: dashboard.peak_value、trade_logs.latency_ms の追加）を行います。

AI（OpenAI）機能
----------------
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols を集約して OpenAI で銘柄毎のセンチメントを計算し、ai_scores テーブルへ書き込みます。
  - API キーは引数か環境変数 OPENAI_API_KEY で指定します。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルに記録します。
- 両者とも API 呼び出しに対してリトライやクリップ等のフェイルセーフ実装を含みます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py ................... 環境変数/設定管理（自動 .env ロードを含む）
- config_setup.py ............. .env 対話式ウィザード
- validate_config.py .......... 起動前の設定検証ツール
- run_execution.py ............ ExecutionEngine 起動スクリプト
- run_monitoring.py ........... Monitoring ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py ................ ニュース NLP スコアリング
  - regime_detector.py ......... 市場レジーム判定
- monitoring/
  - monitoring_db.py ........... SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py .......... システム状態・データ鮮度監視
  - trade_monitor.py ........... （注文監視: コード内に存在）
  - risk_monitor.py ............ ドローダウン・ポジション制限監視
  - kill_switch.py ............. kill.flag 書き込みロジック
  - monitoring_engine.py ...... 各モニタの統合実行ループ
  - alert_manager.py ........... （アラート送信: コード内に存在）
- execution/
  - execution_engine.py ........ ExecutionEngine（起動・セッション管理）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
- portfolio/
  - portfolio_builder.py ....... 候補選定・スコア並び替え
  - position_sizing.py ......... 株数計算・資金配分ロジック
  - risk_adjustment.py ......... セクターキャップ・レジーム乗数
- research/
  - factor_research.py ......... ファクター計算（momentum/value/volatility）
  - feature_exploration.py ..... IC/forward returns/統計サマリ
- utils/
  - logging_setup.py ........... ログ初期化ユーティリティ
  - process_priority.py ........ プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py . Paper Trading の検証レポートジェネレータ

開発上の注意点 / ベストプラクティス
-----------------------------------
- .env は決してリポジトリにコミットしないこと（config_setup にもその注意書きが含まれます）。
- 本番運用時は KABUSYS_ENV=live を設定し、KILL_FLAG_CLEAR_ON_START=0 を推奨。
- OpenAI の呼び出しを行う機能は API 料金・レート制限の対象です。API キー・バッチ頻度には注意してください。
- Paper Trading は本番 DB と分離されていますが、DuckDB（分析用）は同一ファイルを参照する設計のままなので運用時は必要に応じて分離してください。

よくあるコマンドまとめ
----------------------
- .env 作成（対話）:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

付録: トラブルシューティング
-----------------------------
- ログディレクトリ作成に失敗する場合:
  - LOG_DIR を書き込み可能なディレクトリに設定するか、権限を確認してください。失敗するとファイル出力は無効化され stdout のみになります。
- OpenAI API の接続/429 エラー:
  - 一時的なエラーは内部で指数バックオフしリトライします。失敗が続く場合は API キー・料金状態・ネットワークを確認してください。
- SQLite/DuckDB のパスが存在しない/親ディレクトリがない:
  - validate_config で警告が出ます。必要であれば事前にディレクトリを作成してください（多くは起動時に自動作成されます）。

以上。必要があれば README に含めるサンプル設定 (.env.example) や起動ユースケース別の運用手順（systemd ユニット / supervisor / Dockerfile の例）も作成できます。どの情報が必要か教えてください。