README
======

概要
----
KabuSys は日本株向けの自動売買/研究プラットフォームのコードベースです。本プロジェクトは以下の主要領域を提供します。

- 発注実行エンジン（ExecutionEngine）とブローカークライアントの抽象化
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（候補選定・重み算出・株数決定・リスク調整）
- リサーチ（ファクター計算・特徴量探索）
- AI を使ったニュース NLP（OpenAI を用いたセンチメント評価）とレジーム判定
- 環境設定ウィザード・設定検証・運用用ツール（Paper Trading レポート等）

主な設計方針は「本番・ペーパートレードの分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API失敗時はフォールバック）」です。

特徴一覧
--------
- Execution と Monitoring を別プロセスで起動できる運用設計
  - run_execution: ExecutionEngine をスレッドで動かすエントリポイント
  - run_monitoring: SystemMonitor のポーリングループを実行
- 環境別分離
  - KABUSYS_ENV により development / paper_trading / live を切替
  - paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用
- Kill Switch による安全停止（data/kill.flag を書き込む）
- 監視 DB（SQLite）と分析 DB（DuckDB）の併用
- AI モジュール
  - news_nlp: ニュース記事から銘柄別センチメントを生成し ai_scores に格納
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成し market_regime を決定
- Portfolio モジュール（純粋関数）
  - 銘柄選定、等重・スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- Research モジュール（DuckDB 経由でファクター計算）
- 運用ユーティリティ
  - config_setup: .env の対話式生成
  - validate_config: .env / config/*.yaml の検証
  - tools.paper_verification_report: Paper Trading の検証レポート生成
- ログ設定ユーティリティ: 日次ローテート（logs/<app>.log）とコンソール出力を統一

事前要件（推奨）
----------------
- Python 3.10+
- 必要パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config 検証時に YAML 内容検査を行いたい場合）
- （任意）virtualenv / venv を利用した隔離環境

セットアップ手順
---------------
1. リポジトリをクローンして、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（requirements ファイルが無い場合は個別に）。
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 環境変数 (.env) を作成します（推奨: 対話式ウィザードを使用）。
   - python -m kabusys.config_setup
   - 生成した .env は絶対に Git にコミットしないでください。

4. 設定検証を行います。
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告もエラー扱いになります。

5. データディレクトリ等の作成
   - デフォルトでは data/ に以下ファイル・フラグを作成して使用します:
     - data/monitoring.db (SQLite, 監視ログ。自動生成)
     - data/paper_trading.db (Paper Trading 用 SQLite)
     - data/kabusys.duckdb (DuckDB 分析 DB)
     - data/execution.pid / data/kill.flag / data/stop_requested.flag など（起動処理で自動作成・参照）

主要環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading の専用 DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の約定挙動)
- OPENAI_API_KEY (AI 機能の利用に必須)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (ログ保存ディレクトリ、デフォルト: logs/)
- MONITOR_POLL_INTERVAL (monitoring のポーリング間隔秒、デフォルト: 60)
- KILL_FLAG_PATH (kill.flag のパス、デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアする場合: "1")

使い方
------
起動スクリプト（運用）
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）

  仕様メモ:
  - run_monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを保存します。
  - data/stop_requested.flag を作成すると監視ループは終了します。

- Execution エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せずに終了します。
  - data/execution.pid に PID を書き込みます。停止は kill.flag（KILL_FLAG_PATH）や stop_requested.flag によって行えます。

運用ツール・デバッグ
- 環境ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告でも終了コード 1 を返します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH から DB を参照するか、--db で override 可能

- AI 機能（プログラム API）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日分のニュースをスコア化して ai_scores テーブルへ書込む
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、market_regime テーブルへ判定結果を書込む

注意点 / 運用上のポイント
- Paper Trading は本番 DB と分離されています。KABUSYS_ENV=paper_trading を必ず指定してください。
- OpenAI を使う機能は API コストが発生します。API キーの管理に注意してください。
- Kill Switch（data/kill.flag）を利用すると ExecutionEngine に停止シグナルを送れます。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動クリアされるため）。
- 自動で .env を読み込む挙動はデフォルト有効です。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- ログは logs/<app_name>.log に日次ローテーションで保存されます（既定 30 日保持）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス。環境変数 / .env 自動ロードロジックを含む。
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - .env / config/*.yaml の検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py      — ニュースセンチメント算出（OpenAI 呼び出し）
  - regime_detector.py — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化（system_status / trade_logs / positions / risk_logs / dashboard 等）
  - system_monitor.py
  - trade_monitor.py (参照されるが本 README では省略)
  - risk_monitor.py
  - monitoring_engine.py — 各 Monitor を束ねる
  - kill_switch.py
  - alert_manager.py (アラート送信実装、コードベースに存在)
- execution/  (発注系コンポーネント: BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等)
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
  - logging_setup.py — ログ初期化ユーティリティ（Stream + TimedRotatingFile）
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

付録：運用用ファイル・フラグ
-------------------------
- data/stop_requested.flag
  - 手動で作成すると run_monitoring / run_execution のループが検知して安全に終了します（run_execution は起動拒否もする）。
- data/kill.flag
  - KillSwitch が書き込む。ExecutionEngine 側で検知して停止することを想定。
- data/execution.pid
  - run_execution が PID を書き込む（プロセス管理用）。

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" を参照してください。

サポート / 開発メモ
------------------
- DuckDB の SQL を多用するため、ローカルで分析を行う場合は DuckDB ファイルを用意してください。
- tests / CI に関する記載は本 README に含めていません。ユニットテストの追加を推奨します。
- AI 周りの外部 API 呼び出しはリトライ・バックオフを備えていますが、実運用ではレート制限・コスト管理に注意してください。

おわりに
--------
まずは .env を作成し、python -m kabusys.validate_config で設定が正しいことを確認した上で、小規模な Paper Trading で挙動確認を行ってください。運用上疑問点があればソース内の docstring を参照すると設計や注意点が詳細に書かれています。