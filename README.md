KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのシステムです。本リポジトリには以下の主要機能群が含まれます。

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で発注を実行。ペーパートレード/本番を切り替え可能。
- Monitoring（監視）: システム稼働状況・注文状態・リスク指標を定期チェックし、ログや Kill Switch を管理。
- Portfolio 構築ロジック: 候補選定、重み算出、ポジションサイズ計算、セクター制限など。
- Research / Factor 計算: モメンタム、ボラティリティ、バリュー等のファクター計算、IC評価等の統計ユーティリティ。
- AI モジュール: ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定。
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード/検証、監視DB層、ツール（検証レポート生成）など。

主な特徴
--------
- 環境変数ベースの柔軟な設定（.env / .env.local 自動読み込み）
- ペーパートレード用 DB を本番と完全に分離（KABUSYS_ENV）
- DuckDB を用いた分析用 DB インターフェース
- OpenAI を用いたニュース NLP / レジーム判定（API キー必須）
- 監視ループ（MONITOR_POLL_INTERVAL で間隔指定）、Kill Switch による安全停止
- 日次ログローテーション（logs/<app>.log、TimedRotatingFileHandler）

セットアップ手順
----------------
1. Python 環境
   - Python 3.10+ を推奨（typing|match 機能は不要だが、ライブラリ互換性のため）。
2. 依存パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - 必要に応じて: pip install PyYAML（config 検証で YAML の中身をチェックする場合）
3. リポジトリルートで .env を作成
   - 自動対話ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成（必須項目は下記参照）。
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。
5. データディレクトリ等の準備
   - デフォルトでは data/ 以下に DB やフラグファイルを作成します。必要に応じて環境変数で上書きしてください。

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB とは分離）
- DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの fill 動作（instant | partial | never | reject。デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = クリア、0 = クリアしない。デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化（テスト用）

使い方（主要スクリプト）
------------------------
- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前に推奨）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 備考: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動時、data/stop_requested.flag が存在するとエンジンは起動しません。
  - ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を使用します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に settings.sqlite_path（監視 DB）を使用します（KABUSYS_ENV に依存しない点に注意）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI / バッチ呼び出し（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と日付を渡してニュースセンチメントを ai_scores テーブルへ書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書き込みます。

ロギング / ログファイル
----------------------
- setup_logging() により stdout と日次ローテーションファイル（logs/<app>.log）に出力されます。
- LOG_DIR 環境変数または引数でログディレクトリを変更可能。失敗した場合はコンソール出力のみで継続します。

監視 / Kill Switch の仕組み
--------------------------
- MonitoringEngine が SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、異常を検出時に MonitoringDB (SQLite) に記録・AlertManager で通知します（AlertManager の実装に依存）。
- KillSwitch はリスク条件（例: ドローダウン超過、ポジション上限超過）を満たすと data/kill.flag を書き込み、ExecutionEngine 側がそれを検出して安全停止します。
- kill.flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険なため注意。

開発者向けメモ
--------------
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env を自動読み込みします。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings クラス: kabusys.config.Settings を通じて環境変数にアクセスします。
- DB マイグレーション: monitoring_db.init_monitoring_db() は実行時に必要なテーブルの作成や簡易マイグレーション（カラム追加）を行います。冪等です。
- process_priority: kabusys.utils.process_priority.set_process_priority("high") で優先度をあげる実装があります（psutil 必須）。OS によっては失敗しても警告でスキップされます。

ディレクトリ構成（抜粋）
---------------------
以下は本リポジトリ内の主なファイル／ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数管理（Settings）
  - config_setup.py          — .env 対話作成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — 共通ロガー設定
    - process_priority.py    — プロセス優先度 / CPU affinity utilities
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続層（テーブル定義 + DB ラッパー）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - trade_monitor.py       — （省略）注文監視ロジック
    - monitoring_engine.py   — 各 Monitor をまとめるエンジン
    - kill_switch.py         — Kill Switch ロジック（flag ファイル管理）
    - alert_manager.py       — （省略）通知管理
  - execution/               — ExecutionEngine・注文管理等（ファクトリ, engine, order_manager 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み算出
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
    - position_sizing.py     — 発注単位（株数）計算
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン計算、IC、統計要約
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で銘柄ごとにスコア化
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパーの検証レポート生成ツール

（注）この README はリポジトリ内の主要ファイル群を抜粋して説明しています。各モジュールの詳細は該当ファイルの docstring / コメントを参照してください。

よくある運用上の注意
-------------------
- 本番（KABUSYS_ENV=live）時は .env の内容・LINE 通知・Kill Switch 設定を十分に確認してください。
- OpenAI を使う機能は API コストとレイテンシ、リトライ戦略を考慮して運用してください。API キーは漏洩しないよう管理してください（.env を Git にコミットしない）。
- ログディレクトリや DB のパスは適切な権限のあるディレクトリに設定してください。ログディレクトリ作成に失敗してもプロセスは stdout のみで動作します。

ライセンス / バージョン
-----------------------
パッケージバージョンは kabusys.__version__ = "0.1.0" です。ライセンス情報・貢献ガイドは別途リポジトリルートに配置してください。

この README に関する補足や、特定モジュールの詳しい使い方（例: ExecutionEngine の設定・Broker クライアント実装、TradeMonitor の詳細など）が必要であれば教えてください。追加のセクション（運用手順、デバッグ方法、テスト方法 など）を作成します。