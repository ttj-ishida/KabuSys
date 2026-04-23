README
=======

概要
----
KabuSys は日本株の自動売買および研究を支援する Python パッケージです。本リポジトリには以下の主要機能を提供するモジュール群が含まれます。

- マーケット・ファクター計算や特徴量探索（research）
- ポートフォリオ構築（portfolio）
- 発注実行エンジン（execution）
- 監視・アラート・Kill Switch（monitoring）
- ニュース NLP / レジーム判定（ai）
- 各種ユーティリティ（設定・ログ・プロセス優先度など）
- ペーパートレード検証レポート生成ツール（tools）

主な設計方針は「本番 DB とペーパートレードの分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に制御する（OpenAI 等）」などです。

機能一覧
--------
- 設定管理・ウィザード
  - .env の自動読み込み（.env, .env.local）、config_setup による対話的生成
  - validate_config による事前検証（--strict オプションあり）
- 実行エンジン（ExecutionEngine）
  - 実行環境に応じた Broker クライアント選択（本番 / paper_trading）
  - リスク管理、オーダー管理、リコンサイル機能
  - 停止フラグ（data/stop_requested.flag, data/kill.flag）による安全停止
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度確認
  - TradeMonitor / RiskMonitor: 注文・ドローダウン・ポジション上限監視
  - KillSwitch: 閾値超過時に kill.flag を書いて ExecutionEngine を停止
  - MonitoringEngine: 各モニタを束ねてポーリング・アラート送信
  - 永続化: SQLite ベースの monitoring DB（init_monitoring_db により冪等作成）
- 研究用モジュール（research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - DuckDB ベースで高速に集計・分析
- ポートフォリオ構築（portfolio）
  - 候補選定、等重／スコア重み付け、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイジング（単元株丸め、aggregate cap 調整）
- AI 系（ai）
  - news_nlp: OpenAI によるニュースセンチメント集約・ai_scores 書き込み
  - regime_detector: ETF MA200 とマクロニュースから日次レジーム判定
  - OpenAI 呼び出しはリトライ/バックオフや JSON バリデーションを含む堅牢な実装
- ツール
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポート生成

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（typing の | 記法などを利用）
- SQLite は標準ライブラリで OK
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の検証を行う場合）
  - （必要に応じて他の依存を追加）

例（仮想環境作成 + パッケージインストール）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. インストール（最低限）
   - pip install duckdb psutil openai PyYAML

.env の準備
- 対話式ウィザードで .env を生成することを推奨:
  - python -m kabusys.config_setup
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI を使う場合:
  - OPENAI_API_KEY を設定するか、score_news/score_regime 呼び出し時に api_key を渡す

.env 自動読み込み
- 起動時にプロジェクトルート（.git または pyproject.toml を探索）を検出できれば:
  - .env が自動で読み込まれ、.env.local は優先して上書きされます
- 自動ロードを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

ディレクトリ / ファイル用意
- data/ : SQLite（data/monitoring.db, data/paper_trading.db）、PID/FLAG を格納
- logs/ : ログファイル（logs/execution.log, logs/monitoring.log など）
- 必要に応じて手動で作成するか、起動時に自動生成されます

設定検証（任意だが推奨）
- python -m kabusys.validate_config
- --strict を付けると警告も失敗として exit(1) を返す

使い方
------

起動スクリプト（モジュールとして実行可能）
- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 説明: 一定間隔で SystemMonitor.check_once() を呼び、monitoring DB（settings.sqlite_path）にログ保存。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で上書き可。停止は data/stop_requested.flag を作成することで行う。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 説明: KABUSYS_ENV によって paper_trading モード時は MockBroker を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ分離して記録。停止は data/stop_requested.flag または kill.flag によって行います。起動時に data/execution.pid が書かれます。

設定ウィザード / 検証
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

ライブラリ関数の呼び出し例
- AI スコアリング（プログラム内で）
  - from kabusys.ai import score_news
  - n = score_news(duckdb_conn, target_date, api_key="sk-...")
- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="sk-...")

環境変数の主要一覧
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（1/0）

注意点・運用メモ
- monitoring は環境にかかわらず settings.sqlite_path（本番監視 DB）を使用します。ペーパートレードの履歴は別 DB に保存されます。
- stop/kill 制御:
  - data/stop_requested.flag: 実行中の run_* スクリプトに対する停止要求（監視スレッドやエンジンが定期的に確認）
  - data/kill.flag: KillSwitch によって書かれ、ExecutionEngine に致命的停止を促す
- ログ:
  - ログは logs/<app_name>.log に日次ローテートで出力（utils.logging_setup.setup_logging を使用）
- OpenAI 呼び出しは API エラーやレート制限に対してリトライ・バックオフ処理を行いますが、API キーやコストの管理は運用側で行ってください。

ディレクトリ構成
----------------

以下は主要ファイル/モジュールの概要（src/kabusys 以下）。パッケージは Python パッケージとして配置されています。

- kabusys/
  - __init__.py                    — パッケージ定義（__version__）
  - config.py                      — 設定管理クラス Settings（.env 自動読み込み、各種プロパティ）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - data/                          — （ランタイム）data ファイル群（DB・PID・FLAG 等）
  - logs/                          — ログ出力先（デフォルト）
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py             — monitoring SQLite 永続化層（init + CRUD）
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文監視（滞留・価格異常等）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 書込み / クリア
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - alert_manager.py             — （アラート送信管理、実装による）
  - execution/
    - broker_factory.py            — BrokerClient の生成（本番 / mock 切替）
    - execution_engine.py          — ExecutionEngine 本体（セッション管理等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・資金配分ロジック
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — momentum/value/volatility 計算（DuckDB）
    - feature_exploration.py       — forward returns / IC / summary
  - ai/
    - news_nlp.py                  — ニュースセンチメント取得・ai_scores 書き込み
    - regime_detector.py           — レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

ライセンス・貢献
---------------
- 本 README はコードベースの説明目的です。ライセンス情報や貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

付録: よく使うコマンド例
---------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 監視開始: python -m kabusys.run_monitoring
- 実行エンジン開始: python -m kabusys.run_execution
- ペーパートレードレポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。運用時はまず config_setup→validate_config を実行して設定状況を確認してから各プロセスを起動してください。