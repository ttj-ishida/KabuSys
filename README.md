README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。  
ポートフォリオ構築・ポジションサイズ計算・リスク制御・監視（システム・注文・リスク）・ペーパートレード検証・ニュース NLP を含むモジュール群を提供します。  
設計方針として「本番データベースとペーパートレード DB の分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API失敗時の安全なフォールバック）」を重視しています。

主な機能
--------
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて本番または paper_trading モードで動作
  - paper_trading は MockBrokerClient を使用し data/paper_trading.db に記録
- 監視プロセス（SystemMonitor をポーリング）起動スクリプト（run_monitoring）
  - システムリソース、データ鮮度、実行プロセスの監視
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
- MonitoringDB（SQLite）用の永続化層（監視ログ・トレードログ・リスクログ・ダッシュボード）
- MonitoringEngine：System/Trade/Risk 各モニタの統合・Kill Switch 評価・アラート連携
- リスク監視（ドローダウン・ポジション上限）および KillSwitch（data/kill.flag 書き込み）
- ポートフォリオ構築モジュール（候補選定、等金額／スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数）
- リサーチ（ファクター計算: momentum/value/volatility、特徴量探索、IC・統計サマリー）
- AI モジュール
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント評価（ai_scores テーブル書き込み）
  - regime_detector: ETF（1321）MA とマクロニュースセンチメントの合成による市場レジーム判定
  - OpenAI 連携には OPENAI_API_KEY が必要
- ツール
  - paper_verification_report: ペーパートレード DB から運用検証レポート生成
- 設定関連
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）

前提条件（依存パッケージ）
------------------------
主な依存（プロジェクトに requirements.txt は同梱されていない想定のため代表例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の内容検証を行う場合に必要）

セットアップ手順
--------------
1. リポジトリをクローンし、プロジェクトルートへ移動
   - 一般的には src/ をパッケージルートとします（本リポジトリは src レイアウト）。

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトで要求されるバージョンはプロジェクトによる。CI や requirements を参照してください）

4. 初期設定（.env の作成）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使用する場合:
     - OPENAI_API_KEY を環境変数または .env に設定

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - strict モード（警告も FAIL）:
     - python -m kabusys.validate_config --strict

6. ログディレクトリの確認
   - デフォルトログディレクトリ: logs/
   - LOG_DIR 環境変数で変更可能

実行方法（概要）
----------------

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - development: 開発（発注なし）
    - paper_trading: MockBrokerClient を使用、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
    - live: 本番（実際の API 経由で発注）
  - 停止は data/stop_requested.flag を作成することでスレッド停止を促します。
  - ExecutionEngine により PID ファイル（data/execution.pid）を作成します。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視プロセスは常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に関係なく本番 DB を参照する設計）。
  - 停止は data/stop_requested.flag により検知して終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ニュース・レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None) — OPENAI_API_KEY が必要
  - regime_detector.score_regime(conn, target_date, api_key=None) — OPENAI_API_KEY が必要
  - これらは DuckDB 接続（DuckDBPyConnection）を受け取り、ai_scores / market_regime 等に書き込みます
  - 使用モデルは gpt-4o-mini（コード内定義）。API の失敗は安全にフォールバックする設計です。

重要なファイル・フラグ
--------------------
- data/stop_requested.flag
  - run_execution/run_monitoring が存在チェックを行い、作成されていると順次停止します（外部からの停止要求）。
- data/kill.flag
  - KillSwitch がリスクトリガー発生時に書き込む停止フラグ。ExecutionEngine の起動ロジックは KILL_FLAG_CLEAR_ON_START に応じてクリアするか判断します（環境変数で制御）。
- data/execution.pid
  - 実行エンジンの PID ファイル（settings.pid_file_path／デフォルト）。

環境変数（主なもの）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development|paper_trading|live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL — デフォルト INFO
- LOG_DIR — ログフォルダ（デフォルト logs/）
- OPENAI_API_KEY — AI モジュール使用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

停止 / Kill Switch の動作
------------------------
- RiskMonitor / KillSwitch により条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine 側が検出して停止する仕組みです。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動的に kill.flag をクリアします（本番では 0 を推奨）。

開発者向けメモ
--------------
- config.py はプロジェクトルート（.git もしくは pyproject.toml を探索）を基に .env を自動読み込みします。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- logging は kabusys.utils.logging_setup.setup_logging を全起動スクリプトで呼ぶことで統一されています。
- プロセス優先度設定は kabusys.utils.process_priority.set_process_priority を使用（psutil 必須）。Windows / POSIX を考慮した実装です。
- DuckDB を使ったリサーチ機能は prices_daily / raw_financials / raw_news 等のテーブルに依存します。データ投入は別途データパイプラインを通す想定です。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
- config.py                  — 環境変数 / Settings
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- tools/
  - paper_verification_report.py  — ペーパートレード検証レポート
- ai/
  - news_nlp.py               — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py        — 市場レジーム判定
- portfolio/
  - portfolio_builder.py      — 候補選定 / 重み付け
  - position_sizing.py        — 発注株数計算
  - risk_adjustment.py        — セクター上限・レジーム乗数
  - __init__.py
- research/
  - factor_research.py        — モメンタム / バリュー / ボラティリティ計算（DuckDB）
  - feature_exploration.py    — forward returns / IC / 統計サマリー
  - __init__.py
- monitoring/
  - monitoring_db.py          — SQLite 永続化層（schema / CRUD）
  - system_monitor.py         — システム監視
  - trade_monitor.py          — （注文監視; 実装参照）
  - risk_monitor.py           — ドローダウン・ポジション上限監視
  - kill_switch.py            — kill.flag 制御
  - monitoring_engine.py      — 各モニタ統合
  - alert_manager.py          — （アラート送信; 実装参照）
- execution/
  - execution_engine.py       — 実行エンジン（EngineConfig 等）
  - broker_factory.py         — BrokerClient 作成
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- monitoring/                 — 監視関連（上記）
- utils/
  - logging_setup.py          — ロギング設定ユーティリティ
  - process_priority.py       — プロセス優先度設定ユーティリティ
  - __init__.py

補足
----
- 本 README はコードベースから読み取れる設計・設定を簡潔にまとめたものです。詳細な API 仕様や実行時の挙動は各モジュールの docstring を参照してください。
- 実行前には必ず python -m kabusys.validate_config で設定チェックを行うことを推奨します。
- 本番運用時は KABUSYS_ENV=live の設定と LINE 通知等の監視設定・ kill_flag の取り扱いを慎重に行ってください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE 等を参照してください。
- 貢献手順やコントリビューションポリシーがあれば同ディレクトリに CONTRIBUTING.md を追加してください。