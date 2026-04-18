README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ・モニタリングを目的とした Python パッケージです。本プロジェクトは以下の機能群を備え、実運用（live）、ペーパートレード（paper_trading）、開発（development）の各モードに対応します。

主な特徴
- 株価データを DuckDB で集計・解析する研究モジュール（ファクター計算、特徴量探索など）
- ポートフォリオ構築用の純関数群（候補選定、重み算出、ポジションサイズ計算）
- ExecutionEngine（発注エンジン）の起動スクリプト（本番/ペーパートレード切替、リスク管理）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）のポーリング実装と kill-switch
- ニュース NLP / レジーム検出（OpenAI を利用したセンチメント評価）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- ペーパートレード検証レポート生成ツール

機能一覧
---------
- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config (--strict)
- 実行コンポーネント
  - ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録
  - Monitoring 起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視・自動停止
  - システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス生存）
  - トレード監視（滞留注文・約定異常など）
  - リスク監視（ドローダウン・ポジション上限）→ 条件満たすと data/kill.flag を出力（KillSwitch）
  - kill.flag を利用した ExecutionEngine の停止
- 研究・リサーチ
  - ファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン・IC 計算・統計サマリー
- AI 支援
  - ニュース NLP による銘柄別センチメント算出（OpenAI）
  - レジーム判定（MA とマクロニュースの合成）
- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------

前提
- Python 3.10 以上
- git リポジトリのルートにプロジェクトがあること（.env 自動ロードのため）

依存パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config 検証や YAML parsing が必要な場合に推奨）
- その他: 標準ライブラリ

インストール例（仮想環境推奨）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. pip で必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

初期設定
1. 対話式で .env を生成（推奨）
   - python -m kabusys.config_setup
   - 生成後、.env をプロジェクトルートに保存してください（.env は絶対に Git にコミットしないでください）

2. 設定検証
   - python -m kabusys.validate_config
   - 問題があればメッセージに従って修正。厳格モード:
     - python -m kabusys.validate_config --strict

重要な環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- KABUSYS_ENV: 実行モード（development / paper_trading / live）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading モードのとき）
- LOG_LEVEL / LOG_DIR: ログ出力設定

使い方
------

一般的な起動方法（プロジェクトルートで実行）

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更したい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用します（monitoring 用 DB）

- 実行エンジン起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録（本番 DB と完全分離）
  - 実行中に停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成すると安全に停止します
  - KillSwitch による強制停止は data/kill.flag を監視して行われます（Monitoring が書き込む）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能

ログ
- ログはデフォルトで logs/ に日次ローテーションで保存されます（設定は LOG_DIR 環境変数または setup_logging の引数で変更可）。
- ログレベルは LOG_LEVEL で指定（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト INFO。

停止・フラグファイル
- 停止リクエスト（stop_requested.flag）
  - run_monitoring / run_execution のループは data/stop_requested.flag の存在をチェックします。存在するとループを抜け安全に終了します。
- Kill Switch（kill.flag）
  - Monitoring 系のロジックで重大なリスク（ドローダウンやポジション上限超過）を検出すると data/kill.flag を書き込み、ExecutionEngine のシャットダウントリガーになります。
- 起動時に kill.flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を .env に設定できます（本番では 0 推奨）。

ディレクトリ構成
----------------

プロジェクトの主要なファイル/ディレクトリ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring 起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤー（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （trade 関連監視。コードベースの中に実装あり）
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信管理。LINE 等）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動 / セッション管理）
    - broker_factory.py      — ブローカークライアント生成（本番 / Mock）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py
  - data/                    — デフォルトの DB / フラグファイル配置（data/monitoring.db 等）
  - logs/                    — デフォルトログ出力先

注意点 / トラブルシュート
-------------------------
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定だと validate_config がエラーを返します。まず .env を設定してください。
- OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。無い場合は ValueError が出ます。
- PyYAML がインストールされていない場合、validate_config は YAML の内容検証をスキップします（警告表示）。
- DuckDB や SQLite DB ファイルが存在しない／親ディレクトリがない場合、validate_config が警告を出しますが多くの起動処理はディレクトリを自動作成します。
- psutil を使った優先度/affinity の設定は権限により失敗する場合があります（警告でスキップされます）。
- run_execution は paper_trading モード時に paper_sqlite_path を使用して DB を分離します。実アカウントでの誤発注リスクを回避するため、本番設定には十分注意してください。

開発向けヒント
- モジュールを直接実行することでスクリプトを起動できます（python -m kabusys.run_monitoring）。
- ユニットテストや CI のために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます。
- OpenAI 呼び出し部分は内部で _call_openai_api を使っているため、テスト時は該当関数をモックすることで API 呼び出しを回避できます。

ライセンス
----------
（リポジトリに記載のあるライセンスをここに記載してください）

以上。ご不明点や README に追記したい情報があれば教えてください。