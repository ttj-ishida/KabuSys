KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。  
主な責務は次のとおりです。

- 戦略／ポートフォリオ構築（ファクター計算、ポジションサイジング、セクター制約など）
- 注文実行エンジン（本番／ペーパートレード分離、リスク管理、約定ログ）
- 監視（システム状態、注文状態、リスク監視、Kill Switch）
- リサーチ（ファクター、将来リターン、IC 計算）
- AI 補助（ニュースセンチメント・レジーム判定、OpenAI を利用）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

特徴
----
- モジュール化された純粋関数（ポートフォリオ構築・リスク調整・ポジション計算）
- DuckDB（時系列・分析）と SQLite（監視・注文ログ）を併用
- 本番 / ペーパートレードを明確に分離（ペーパートレードは専用 DB）
- ログはコンソールと日次ローテートファイル出力（logs/*.log）
- Kill Switch（データ駆動でのエンジン停止）と監視ループ
- OpenAI を使ったニュースセンチメント・レジーム判定（オプション）

前提
----
- Python 3.10 以上
- 必要な Python パッケージ（例）:
  - duckdb
  - openai
  - psutil
  - PyYAML（設定 YAML 検証用、必須ではない）
- OS: Linux / macOS / Windows（各 OS の差分は utils/process_priority.py で吸収）

インストール（開発環境）
--------------------
1. リポジトリをクローン・移動
   - git clone ... ; cd <repo>

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Linux/macOS
   - .venv\Scripts\activate     # Windows

3. 依存ライブラリをインストール（requirements.txt がある場合はそちらを利用）
   - pip install duckdb openai psutil pyyaml

初期設定（.env の作成）
-----------------------
1. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - 画面の案内に従って必要値（J-Quants トークン、kabu API パスワード、KABUSYS_ENV 等）を入力してください。

2. 作成後、設定検証を実行
   - python -m kabusys.validate_config
   - 本番運用前は --strict を付けて警告もチェックします:
     - python -m kabusys.validate_config --strict

主要環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production は 0 推奨）

注意:
- .env は決して Git にコミットしないでください（config_setup で生成されるヘッダにも警告があります）。

使い方
------

起動スクリプト
- 監視ループ（Monitoring）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジン（ExecutionEngine）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に stop をしたい場合は stop フラグを作成（see Kill Switch below）。

運用サポート CLI / ツール
- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 本番では --strict を検討

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

AI モジュール
- ニューススコアリング（news_nlp）やレジーム判定（regime_detector）は OpenAI API を呼び出します。OPENAI_API_KEY を設定してください。
- AI モジュールは失敗時に安全にフォールバックするよう設計されていますが、API キー未設定だと例外が発生する箇所があります（呼び出し前にキーを提供してください）。

Kill Switch / 停止フラグ
- KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 手動で強制停止する用途には data/stop_requested.flag を使う仕組みもあり、run_monitoring/run_execution はこのファイルの存在をチェックして終了します。
- KILL_FLAG_CLEAR_ON_START=1 を有効にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

ログ
---
- ログはデフォルトで stdout と logs/<app_name>.log に出力されます（TimedRotatingFileHandler、日次ローテート、30 日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行います。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス（全サービス共通）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_monitoring.py
  - Monitoring ポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / ペーパー切替）
- utils/
  - logging_setup.py — ログ統一設定
  - process_priority.py — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py — SQLite DB スキーマ・読み書き層
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — （注文監視：コードベースに記述あり）
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — kill.flag 制御
  - monitoring_engine.py — 各監視の統合ループ
  - alert_manager.py — （通知管理：コードベースに記述あり）
- execution/
  - execution_engine.py — 発注エンジン（起動・セッション管理）
  - order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算・スケール調整
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — レジーム判定（MA + マクロ NLP）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- monitoring/*.py, portfolio/*.py, research/*.py, ai/*.py — 各サブシステムの実装

（注）一部ファイル名はここで省略していますが、主要モジュール群は上記に含まれます。

運用上の注意事項 / ベストプラクティス
-----------------------------------
- 本番運用時は KABUSYS_ENV=live を設定し、ログレベル・通知設定を適切に行ってください。
- .env は機密情報を含むため安全に管理してください（Vault / CI シークレット等の利用を推奨）。
- Kill Switch / stop flag の取り扱いは慎重に。KILL_FLAG_CLEAR_ON_START を誤って有効にすると Kill Switch が無効化される可能性があります。
- ペーパートレードは paper_sqlite_path / PAPER_TRADING_SQLITE_PATH に分離されます。ペーパーデータと本番データの混入を避けてください。
- AI（OpenAI）を利用する機能は API コストやレート制限に注意してください（リトライ・バックオフ実装あり）。

追加情報 / 開発者向け
--------------------
- DuckDB をローカルで作成して prices_daily や raw_financials 等のテーブルを投入すると、research モジュールや AI モジュールをローカルで検証できます。
- monitor / execution 起動前に sqlite/duckdb のパスを .env や環境変数で設定してください（親ディレクトリが存在しないと警告が出ますが、多くは起動時に自動作成されます）。
- YAML 設定ファイル（config/*.yaml）は scripts/generate_config.py 等で生成する想定です（validate_config で存在確認と簡易パース検証を実施します）。

サンプル起動フロー（ローカルでの手順）
-----------------------------------
1. 仮想環境作成・依存ライブラリインストール
2. python -m kabusys.config_setup（.env を作成）
3. python -m kabusys.validate_config（設定を検証）
4. DuckDB / SQLite ファイルを準備（data/ ディレクトリ作成）
5. python -m kabusys.run_monitoring（監視プロセス起動）
6. 別プロセスで python -m kabusys.run_execution（実行エンジン起動）
7. 運用: logs/ 以下のログや data/kill.flag を監視・管理

サポート / コントリビューション
--------------------------------
バグ報告・改善提案は issue を作成してください。ドキュメントやテストの追加も歓迎します。

---
この README はコードベースの主要機能と運用手順を簡潔にまとめたものです。詳細な API や設計方針はソース内の docstring / コメントを参照してください。