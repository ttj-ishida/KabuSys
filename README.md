README
=====

概要
----
KabuSys は日本株自動売買のためのバックエンドライブラリ / 実行基盤です。  
主に次を提供します。

- 市場データ分析（DuckDB を用いたファクター計算・研究モジュール）
- ポートフォリオ構築（銘柄選定、重み付け、株数決定）
- 実行エンジン（kabuステーション等と連携して発注、ペーパートレード対応）
- 監視・リスク管理（プロセス/データ鮮度/ドローダウン監視、Kill Switch）
- AI 補助（ニュースセンチメント解析、レジーム判定）
- 運用補助スクリプト（.env ウィザード、設定検証、ペーパートレード検証レポート）

このリポジトリはライブラリと複数の起動スクリプト（実行エンジン・監視ループなど）を含んでいます。

主な機能
--------
- 環境設定ウィザード（kabusys.config_setup）: .env を対話式に生成/更新
- 設定検証 CLI（kabusys.validate_config）: .env / config/*.yaml の整合性チェック
- 実行エンジン起動スクリプト（kabusys.run_execution）:
  - 本番・ペーパーを切り替え可能
  - paper_trading 環境では MockBrokerClient を使用し data/paper_trading.db に完全分離して記録
- 監視ループ起動スクリプト（kabusys.run_monitoring）:
  - 定期ポーリングで SystemMonitor を実行、監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視ストア（kabusys.monitoring.monitoring_db）: SQLite ベースの監視ログ永続化
- リスク監視（kabusys.monitoring.risk_monitor）: ドローダウン・ポジション上限監視とアラート記録
- Kill Switch（kabusys.monitoring.kill_switch）: 条件達成時に data/kill.flag を書き込み実行を停止
- ポートフォリオ構築（kabusys.portfolio）:
  - 候補抽出、等重・スコア重み計算、リスク調整、ポジションサイズ計算（lot 単位で丸め）
- 研究用モジュール（kabusys.research）: ファクター計算（モメンタム・ボラティリティ・バリューなど）・IC 計算
- AI モジュール（kabusys.ai）:
  - news_nlp: OpenAI を使ったニュースセンチメント解析（ai_scores へ書き込み）
  - regime_detector: マクロニュース＋ETF MA を合成して市場レジーム判定
- ツール（kabusys.tools.paper_verification_report）: ペーパートレード DB から検証レポートを生成

セットアップ
----------
1. リポジトリをクローン / 展開し、ルートがプロジェクトルートになるように配置します（.git か pyproject.toml がある場所）。  
2. Python 仮想環境を作成して有効化することを推奨します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストールします（requirements.txt がある場合はそれを使用）。このコードベースで参照している主要パッケージ例:
   - pip install duckdb psutil openai
   - （必要に応じて PyYAML をインストールすると config/*.yaml の構文チェックが有効になります）
4. 初期 .env を作成します（2つの方法）:
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 手動で .env を作成: .env.example を参考に必要な環境変数を設定
5. 設定検証:
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合: python -m kabusys.validate_config --strict
6. データディレクトリ/ログディレクトリの確認:
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - 監視 SQLite: data/monitoring.db
     - ペーパートレード SQLite: data/paper_trading.db
     - ログディレクトリ: logs/ (デフォルト)
   - 起動時に必要な親ディレクトリは自動生成されますが、権限等に注意してください。

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（例: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — run_monitoring が参照（デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化（テスト用）

使い方
-----
各主要スクリプトの起動例:

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特徴:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB に切り替え、MockBrokerClient を使用し本番 DB と分離
    - 起動時に data/stop_requested.flag があれば起動しない
    - 実行中に data/stop_requested.flag を作ると安全に停止する
    - pid ファイル: data/execution.pid（デフォルト）を使用

- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定可能
  - 監視は常に（KABUSYS_ENV にかかわらず）本番用 sqlite_path を参照してログを保存します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 簡易基準に基づく PASS/FAIL を表示（稼働率、約定率、送信率、P95 レイテンシ等）

ファイル/フラグについて
---------------------
- data/kill.flag: Kill Switch が起動エンジンを停止するために書き込むファイル
- data/stop_requested.flag: run_execution / run_monitoring が検出して安全に停止するためのフラグ
- data/execution.pid: 実行エンジンの PID を格納するデフォルトの pid ファイル
- logs/<app_name>.log: 各アプリ（execution / monitoring 等）のログが日次ローテーションで保存されます

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 配下の主要ファイル・モジュールの一覧と説明です。

- src/kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — Settings クラス: 環境変数解決・自動 .env ロード
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト（実行/ペーパー切替）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ（ファイル / コンソール）
    - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（テーブル作成・CRUD ヘルパー）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （発注ログ等の監視: 実装参照）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 制御
    - monitoring_engine.py     — 各 Monitor をまとめてポーリングするエンジン
    - alert_manager.py         — （通知管理: 実装参照）
  - execution/
    - execution_engine.py      — 実行エンジン本体（EngineConfig 等）
    - order_manager.py         — 注文管理ロジック
    - order_repository.py      — 注文永続化（SQLite 等）
    - broker_factory.py        — BrokerClient の生成（実ブローカー / Mock 切替）
    - reconciler.py            — 発注整合処理
    - risk_manager.py          — 注文前リスク審査
  - portfolio/
    - portfolio_builder.py     — 候補選定・等重/スコア重み計算
    - position_sizing.py       — 株数（lot）計算・aggregate cap スケーリング
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — モメンタム・ボラティリティ・バリュー等の計算（DuckDB）
    - feature_exploration.py   — 将来リターン計算・IC・統計サマリー
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）で銘柄センチメントを ai_scores へ
    - regime_detector.py       — マクロニュース + ETF MA でレジーム判定

注意事項 / 運用上のヒント
------------------------
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかにしてください。live は本番なので慎重に設定してください。
- .env ファイルは絶対にバージョン管理にコミットしないでください（config_setup の注意書き参照）。
- OpenAI 関連機能を使う場合は OPENAI_API_KEY を環境変数または関数引数で必ず指定してください。
- run_monitoring と run_execution は stop/kill フラグで協調停止する仕組みがあります。運用時は data ディレクトリのフラグファイルを活用してください。
- ログは logs/ に日次ローテーションで残ります。権限やディスク容量に注意してください。
- DuckDB/SQLite ファイルのパスは Settings でカスタマイズ可能です（環境変数で上書き）。

付録: よく使うコマンド一覧
-------------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 必要パッケージ（例）:
  - pip install duckdb psutil openai PyYAML

この README はコードベースに含まれるモジュールの概要と基本的な使い方をまとめたものです。実運用前に必ず python -m kabusys.validate_config で設定の整合性を確認してください。