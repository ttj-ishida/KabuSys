KabuSys — 日本株自動売買システム（README）
=================================

概要
---
KabuSys は日本株の自動売買／リサーチ用の小規模フレームワークです。  
このリポジトリには、以下の主な機能群が実装されています。

- 実行コンポーネント（ExecutionEngine）と監視コンポーネント（Monitoring）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- リサーチ（ファクター計算、特徴量解析）
- AI モジュール（ニュースセンチメントによるスコアリング、レジーム判定）
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザード / 設定検証ツール
- SQLite / DuckDB を使ったロギング・分析データ永続化

主な設計方針として、実運用とペーパートレードを明確に分離し、DB・ブローカーインターフェースを差し替え可能にしています。

主な機能一覧
-------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db を使う
  - プロセス優先度の設定、PID 管理、停止フラグに対応
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行し、監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境に関わらず本番用 sqlite_path を使用
- 環境設定ウィザード（config_setup.py）
  - .env の対話式生成 / 更新をサポート
- 設定検証（validate_config.py）
  - 必須環境変数や config/*.yaml の存在・簡易構文チェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード用 SQLite を読み、稼働率・注文成功率・レイテンシ等のレポートを出力
- ポートフォリオ構成モジュール（portfolio/）
  - 候補選定、等重/スコア重み、リスク調整、ポジションサイズ計算
- AI モジュール（ai/）
  - raw_news を LLM（OpenAI）でスコアリングし ai_scores に保存
  - 市場レジーム判定（ma200 + マクロニュースセンチメントの合成）
- utilities（utils/）
  - ログ設定、プロセス優先度/CPU affinity 設定など
- 永続化（monitoring/monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルなどの作成・更新ロジック

必要な依存パッケージ（例）
------------------------
最低限想定されるパッケージ（環境に応じて追加してください）:
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config の詳細検証を行いたい場合）
インストール例:
- pip install duckdb psutil openai PyYAML

セットアップ手順
----------------

1. リポジトリをクローン／展開
   - この README を置いているプロジェクトルートを想定します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install duckdb psutil openai PyYAML

4. 環境変数設定（.env）
   - 対話式ウィザードを使うと簡単です:
     - python -m kabusys.config_setup
   - 手動で作成する場合はプロジェクトルートに .env を置く。最低限必要な値:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - LOG_LEVEL, LOG_DIR など

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - エラーがあれば修正し、--strict を付けると警告も失敗扱いになります。

使い方（主要スクリプト）
------------------------

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBroker を使用
    - 起動時に data/stop_requested.flag をチェックし、存在する場合は起動を中止
    - 実行中に data/stop_requested.flag を作成するとエンジンが停止します
    - PID ファイルを data/execution.pid に書きます（パスは Settings.pid_file_path で変更可）

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor を一定間隔で実行し、結果を SQLITE_PATH（data/monitoring.db）へ保存
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
    - 監視は常に本番 sqlite_path を使用（環境に関係なく共有監視 DB）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先して指定可能）

AI 関連（OpenAI 使用部）
------------------------
- ニューススコアリング（ai.news_nlp.score_news）や regime_detector では OpenAI API を使用します。
- OPENAI_API_KEY を環境変数に設定するか、各関数の api_key 引数で渡してください。
- LLM 呼び出しはリトライやフォールバック（失敗時はスコア 0 等）を備えていますが、API 使用量に注意してください。

監視・Kill Switch / 停止フラグ
------------------------------
- KillSwitch は監視結果（ドローダウンやポジション上限）を元に data/kill.flag を書き込むことで ExecutionEngine に停止を促します。
- 実行ループを外部から停止するには project_root/data/stop_requested.flag を作成してください。run_monitoring/run_execution はこのファイルを検出して安全に終了します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動クリアします（本番では 0 推奨）。

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して統一されます。
- デフォルトは logs/<app_name>.log（日次ローテーション、30 日分保持）とコンソール（stdout）出力。
- LOG_LEVEL / LOG_DIR 環境変数でカスタマイズ可能。

ディレクトリ構成
----------------
（プロジェクトルート直下に src/ を配置している構成を想定）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数と設定のラッパー（Settings）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py      — ロギング設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite テーブル作成・永続化 API
    - system_monitor.py     — システム / データ鮮度監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - trade_monitor.py      — （注文ログ監視等; 実装あり）
    - monitoring_engine.py  — 各 Monitor の統合ループ
    - alert_manager.py      — アラート送信（LINE 等、実装に依存）
    - kill_switch.py        — kill.flag 制御
  - execution/
    - execution_engine.py   — 実際の ExecutionEngine（エンジン本体）
    - broker_factory.py     — ブローカークライアント生成（本番 / mock の切替）
    - order_manager.py      — 注文管理
    - order_repository.py   — 注文永続化（SQLite 等）
    - reconciler.py         — 注文整合処理
    - risk_manager.py       — 実行時リスク制御
  - portfolio/
    - portfolio_builder.py  — 候補選定、重み計算
    - position_sizing.py    — 株数計算、集約上限ロジック
    - risk_adjustment.py    — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン / IC / 統計
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI でスコア付与）
    - regime_detector.py    — 市場レジーム判定（ma200 + macro LLM）
  - data/                   — デフォルト DB / フラグファイル等（実行時に作成）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

補足 / 運用上の注意
-------------------
- 本番環境（KABUSYS_ENV=live）では設定ミスが重大な事故に直結します。validate_config で十分にチェックしてください。
- Kill Switch や停止フラグの扱いを理解してから運用してください（特に KILL_FLAG_CLEAR_ON_START）。
- ペーパートレードは本番 DB と分離しています（PAPER_TRADING_SQLITE_PATH）。データの混同に注意。
- OpenAI や外部 API の利用には API キーとコスト管理が必要です。
- DuckDB / SQLite のファイルパスは環境変数で柔軟に変更可能です。バックアップ・権限に注意してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報は本リポジトリのトップレベルに配置してください（LICENSE ファイル等）。

問い合わせ / 開発メモ
---------------------
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テストで便利）。
- テスト用に各種関数は外部依存（DB や OpenAI 呼び出し）を引数で注入できるよう設計されています（単体テスト容易性を考慮）。

以上が README の要旨です。必要ならば、具体的な起動例（systemd ユニット、Dockerfile、docker-compose）や詳細な設定例（.env.example や config/*.yaml のテンプレート）を追記します。どの情報を追加しますか？