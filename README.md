README
======

概要
----
KabuSys は日本株の自動売買システムの核となるライブラリ群です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・研究（ファクター計算）・AI（ニュースセンチメント）など、実運用を想定したコンポーネントを含みます。

主な設計方針
- ローカル開発・ペーパートレード・本番（live）を環境変数で切り替え可能
- DuckDB（分析用）／SQLite（監視・発注ログ）を使用
- OpenAI を使ったニュースNLP・レジーム判定機能（API キー必須）
- フラグファイル（data/kill.flag / data/stop_requested.flag）で外部からプロセス制御
- ログはコンソール＋日次ローテートファイルで出力

機能一覧
--------
- 設定管理
  - .env ファイル自動読み込み、Settings クラスで環境変数をラップ
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン / 発注
  - 実運用の ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し data/paper_trading.db に記録（本番 DB と分離）
- 監視
  - System/Trade/Risk の監視コンポーネントおよび MonitoringEngine
  - run_monitoring.py によるポーリングループ（MONITOR_POLL_INTERVAL 環境変数で間隔指定、デフォルト 60 秒）
  - kill.flag による ExecutionEngine 停止（KillSwitch）
  - 監視ログ永続化：SQLite（monitoring_db）
- ポートフォリオ構築
  - 候補選定、重み計算（等重／スコア重み）、ポジションサイジング（リスクベース等）
  - セクターキャップ・レジーム乗数適用
- 研究用モジュール
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI 統合）
  - ニュース記事から銘柄ごとのセンチメントを計算して ai_scores に保存（news_nlp.py）
  - ETF + マクロニュースを組み合わせた市場レジーム判定（regime_detector.py）
- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - ログ設定（stream + TimedRotatingFileHandler）
  - プロセス優先度・CPU affinity 設定ユーティリティ

セットアップ手順
----------------
前提
- Python 3.10 以上（型アノテーションで | を使用）
- SQLite は標準組み込み
- system によっては psutil 等を利用するためビルド環境が必要

1) 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2) 必要パッケージのインストール（例）
   pip install duckdb psutil openai PyYAML

   ※ PyYAML は設定ファイルの YAML 検証にのみ必要（無ければ検証はスキップされます）。

3) .env の初期作成（対話式）
   python -m kabusys.config_setup

   このウィザードは .env を生成（または更新）します。生成後は以下で検証してください。

4) 設定検証
   python -m kabusys.validate_config
   --strict を付けるとワーニングも失敗扱いになります:
   python -m kabusys.validate_config --strict

5) データディレクトリ / ログディレクトリの準備
   デフォルトで logs/ と data/ を使用します。多くのスクリプトは自動で親ディレクトリを作成しますが、必要に応じて手動作成してください。

主要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（例: data/kabusys.duckdb）
- SQLITE_PATH（監視用、例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、例: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト 60）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）

使い方
------
基本的なコマンド例:

- 設定ウィザード（.env の作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動
  python -m kabusys.run_monitoring
  環境変数でポーリング間隔を変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  動作メモ:
  - 監視は常に（KABUSYS_ENV にかかわらず）本番用 sqlite_path を使用します。
  - 停止要求はプロジェクトルート/data/stop_requested.flag を作成すると検知されループを終了します。

- 実行エンジン起動（発注処理）
  python -m kabusys.run_execution

  動作メモ:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行わず終了します。
  - 実行中に停止させるには data/stop_requested.flag を作成するか、Monitoring の KillSwitch により data/kill.flag が書き込まれることで Engine を停止できます。
  - 実行中は data/execution.pid に PID を書き込みます。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  任意期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア付与 / レジーム判定）
  これらは Python API として利用可能（DuckDB 接続を渡して呼び出す）。
  例（簡略）:
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")

  注意:
  - OPENAI_API_KEY が未設定だと例外になります（関数側でチェック）。
  - API コールはレート制限や一時エラーをリトライしますが、失敗時は安全にフォールバックする設計です。

停止フラグ・運用上のファイル
- data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ。存在するとループ終了・停止処理を行う。
- data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine に対する外部停止命令を表す（存在すると Engine は停止される）。
- data/execution.pid — run_execution が書く PID ファイル（実行中監視用）。
- logs/<app_name>.log — 日次ローテーションされるログファイル（デフォルト保存先 logs/）

ディレクトリ構成（要点）
-----------------------
以下は主要なモジュール配置（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数ラッパ（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — 監視ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視用）
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — （注文）監視ロジック
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書込みユーティリティ
    - monitoring_engine.py   — 各モニタ束ね実行
    - alert_manager.py       — （アラート送信用、実装参照）
  - execution/
    - broker_factory.py      — ブローカークライアント生成
    - execution_engine.py    — 発注エンジン
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — 実行時に使われるデータファイル（デフォルト）
  - logs/                    — ログ保存先（デフォルト）

開発・運用上の注意
------------------
- 環境変数の未設定は ValueError を投げる箇所があるため、まずは config_setup → validate_config を実行すること。
- monitoring は監視目的の DB（SQLITE_PATH）を使用します。development 環境でも本番 sqlite_path を参照する点に注意してください。
- paper_trading を使う場合は KABUSYS_ENV=paper_trading を設定し PAPER_TRADING_SQLITE_PATH を確認してください。本番データと分離するため重要です。
- OpenAI 利用時は API キーの取り扱いに注意し、.env を絶対にリポジトリにコミットしないでください。
- psutil によるプロセス優先度設定は権限や OS に依存し、アクセス拒否や未実装例外が発生する可能性があります（ライブラリは例外をキャッチして警告を出します）。

トラブルシュート（よくある事象）
-------------------------------
- validate_config で必須環境変数エラー:
  → .env に JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD を設定してください。
- OpenAI 関連で「API キー未設定」:
  → OPENAI_API_KEY を設定するか、関数に api_key を渡してください。
- DuckDB・PyYAML が無い:
  → pip install duckdb pyyaml
- ログディレクトリ作成失敗:
  → 権限問題の可能性。手動で logs/ を作成するか、LOG_DIR 環境変数で書き込み可能なディレクトリを指定してください。
- プロセス優先度設定で警告:
  → 権限不足や未サポート OS のためスキップされます（挙動に重大な影響はありません）。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定されています。
- ライセンスはリポジトリに別途記載してください（この抜粋には含まれていません）。

その他
-----
- 本 README はコードベースの主要機能と使い方を端的にまとめたものです。詳細なアーキテクチャや API 仕様は各ソースファイルの docstring を参照してください。
- 追加の運用手順（デプロイ手順、監視設定、CI/CD）や BrokerClient の設定等は運用環境に合わせて整備してください。

--- 
これでセットアップと運用の基本がカバーされています。必要ならば、具体的な .env テンプレートや systemd / supervisor 用ユニットファイルの例も作成します。どちらが必要か教えてください。