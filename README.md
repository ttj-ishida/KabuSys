# KabuSys

日本株向けの自動売買・研究プラットフォーム（モジュール群）。  
このリポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、LLMを使ったニューススコアリングなどを含みます。

以下はコードベース（src/kabusys）から作成した README。実行方法や設定手順、主要機能・ディレクトリ構成を日本語でまとめています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提（依存関係）
- セットアップ手順
- 環境変数（主要）
- 使い方（起動・ユーティリティ）
- 実行時の挙動メモ（paper_trading / live 等）
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- KabuSys は日本株向け自動売買・研究プラットフォームです。
- モジュール化された構成で、発注エンジン、監視・リスク管理、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI）によるセンチメント集約、検証ツール等を提供します。
- 実行・監視プロセスはローカルの SQLite / DuckDB をデータ永続化に使用します（本番 DB とペーパートレード DB を分離可能）。

主な機能一覧
- ExecutionEngine：発注ロジックと注文管理（OrderManager、RiskManager、Reconciler 等）
- Monitoring：SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視エンジン（ログ記録・アラート・Kill Switch）
- Portfolio：候補選定、重み計算、ポジションサイジング、セクター制限などの純粋関数群
- Research：DuckDB を利用したファクター計算（momentum, volatility, value）・特徴量解析（IC, forward returns 等）
- AI：ニュース記事のセンチメントスコアリング（OpenAI 使用）および市場レジーム判定（LLM + MA200 合成）
- ツール：ペーパートレード検証レポート出力スクリプト等
- 設定支援：.env 対話式ウィザード、設定検証 CLI

前提（依存関係）
- Python 3.10+ を想定（型注釈 / match 等を使用していませんが、Union 記法などのため 3.10+ が望ましい）
- 必要な主要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - sqlite3（標準ライブラリ）
  - PyYAML（config 検証で任意利用）
- 推奨：仮想環境を作成して依存をインストールしてください。

例:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai pyyaml

（注）実リポジトリに requirements.txt がない場合はプロジェクトのドキュメントや CI を参照して正確なバージョンを取得してください。

セットアップ手順
1. リポジトリをチェックアウト、仮想環境を作成して有効化。
2. 依存パッケージをインストール（上記参照）。
3. データ / ログディレクトリを用意（自動作成されることもありますが事前に作っておくと権限問題を回避できます）。
   - data/
   - logs/
4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考）。
5. 設定の検証:
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます。
6. （paper_trading を使う場合）PAPER_TRADING_SQLITE_PATH を設定するかデフォルトの data/paper_trading.db を利用。

主要な環境変数（要点）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 動作環境
  - KABUSYS_ENV — execution 動作モード: development | paper_trading | live
    - development: ローカル開発（発注なし等の振る舞い）
    - paper_trading: モックブローカーを使用し、発注は data/paper_trading.db へ記録
    - live: 実際に発注する本番モード
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default data/paper_trading.db）
- ログ・プロセス
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログディレクトリ（デフォルト logs/）
  - PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- その他
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。デフォルト 60）
  - OPENAI_API_KEY — OpenAI を使う場合に必要
  - PAPER_FILL_MODE — ペーパートレードにおける Fill モード（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（1/0）

使い方（起動・ユーティリティ）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading DB（分離）へ記録します。
    - 起動前に data/stop_requested.flag が存在すると起動しません。
    - 実行中に data/stop_requested.flag が作成されると安全に停止します。
- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します（KABUSYS_ENV に依存しません）。
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 任意期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能
- AI / ニューススコアリング（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要（引数または環境変数）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム判定（MA200 とマクロニュースの LLM 集約）
- 監視テスト用
  - MonitoringEngine を組み合わせて run_once() を呼ぶことで単発実行テストが可能

実行時の挙動メモ（重要）
- paper_trading モード:
  - MockBrokerClient を使用し、発注データは paper_trading 用 SQLite に記録されます（本番 DB と完全分離）。
- Kill Switch / Stop Flag:
  - kill.flag（デフォルト data/kill.flag）は ExecutionEngine に停止シグナルを送るために監視から作成されます。存在するとエンジンは停止します。
  - stop_requested.flag（data/stop_requested.flag）は run_execution / run_monitoring の停止トリガーとして使われます（外部から停止する際に便利）。
- PID ファイル:
  - ExecutionEngine は起動時に PID ファイル（例 data/execution.pid）を書きます。監視や外部ツールはこれを参照します。
- ロギング:
  - ログはコンソール(stdout) と 日次ローテートされたファイル logs/<app_name>.log に出ます。LOG_DIR 環境変数で変更可。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存スキーマに列がない場合は ALTER TABLE による簡易マイグレーションを行います。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings の読み取り・自動 .env ロードロジック
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor ポーリングループ起動（python -m kabusys.run_monitoring）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクター上限・レジーム乗数
    - position_sizing.py — 発注株数計算
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — forward returns, IC, 統計サマリ等
  - ai/
    - news_nlp.py — raw_news を LLM でスコアリングし ai_scores に書き込む
    - regime_detector.py — MA200 と LLM マクロセンチメントを合成して regime 判定
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・永続化ロジック（MonitoringDB クラス）
    - system_monitor.py — システム・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （実装ファイル。コードベースでは参照あり）
    - monitoring_engine.py — 複数モニタを束ねるエンジン
    - kill_switch.py — Kill Switch 実装
    - alert_manager.py — （アラート送信ロジック、コードベースで参照）
  - execution/
    - execution_engine.py — ExecutionEngine クラス（起動 / run_session 管理）
    - broker_factory.py — ブローカークライアント生成（Mock/実ブローカー切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行に必要なコンポーネント
  - utils/
    - logging_setup.py — アプリ共通のログ設定ユーティリティ
    - process_priority.py — プロセス優先度（Windows / POSIX を吸収）
  - monitoring/monitoring_db.py — 監視DB定義（再掲：テーブル作成や CRUD を提供）

補足（開発者向けメモ）
- DuckDB 接続は研究・AI モジュールで頻繁に利用します。prices_daily / raw_financials / raw_news 等のテーブルを前提としています。
- OpenAI を利用する機能（news_nlp, regime_detector）は API 通信の失敗に対して耐性（リトライ・フォールバック）を持つ設計です。API キーは OPENAI_API_KEY で指定してください。
- monitoring と execution はそれぞれ独立したプロセスとして運用される想定。ops では systemd / cron / supervisor 等で管理する想定です。
- 設定検証（validate_config）を必ず起動前に実行して、環境変数や設定ファイルの不備を検出してください。

以上がリポジトリの README 相当の概要です。必要であれば各機能（AI 周り、ポジションサイジング、RiskManager のパラメータ説明など）についてさらに詳細なドキュメント（設計仕様、パラメータ一覧、サンプル .env）を作成します。どの章を詳細化しましょうか？