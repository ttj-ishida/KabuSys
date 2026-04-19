README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。以下の主要機能を備え、実運用（live）・ペーパートレード（paper_trading）・開発（development）で動作するよう設計されています。

主な設計方針:
- 発注ロジックと監視・リサーチを分離
- 本番 DB とペーパートレード DB を分離
- DuckDB を分析用、SQLite を監視 / 発注ログ用に使用
- OpenAI を用いたニュース NLP / レジーム判定機能（任意）
- 自動ログローテーション・プロセス優先度設定等のユーティリティを提供

機能一覧
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパーの分離（KABUSYS_ENV に依存）
  - BrokerClientFactory によるブローカ接続抽象化
  - OrderManager / RiskManager / Reconciler などのコンポーネントを組み立てて運用
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス稼働 / データ鮮度の監視
  - TradeMonitor: 発注・約定ログの整合チェック（コード内に該当実装）
  - RiskMonitor: ドローダウン・ポジション上限（DRAWDOWN_ALERT など）
  - KillSwitch: 危険条件で ExecutionEngine に停止フラグを書き込む
  - MonitoringEngine: 各モニタを束ねるポーリングループ
- ポートフォリオ構築（pure functions）
  - 候補選定、等金額 / スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ（DuckDB ベース）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI（OpenAI 統合、任意）
  - news_nlp: ニュースのセンチメントを算出して ai_scores に保存
  - regime_detector: ETF / マクロニュースを合成して市場レジーム判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成

前提条件
--------
- Python 3.8+（コードは型ヒントや新しい標準ライブラリを利用）
- 必要パッケージ（一例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定 YAML を検証したい場合）
- SQLite（標準ライブラリで利用可能）
- ネットワーク（ブローカー API / OpenAI を使う場合）

インストール（例）
-----------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 必要ライブラリのインストール（最小例）
   - pip install duckdb psutil

   OpenAI 機能を使う場合:
   - pip install openai

   設定 YAML の検証を使う場合:
   - pip install PyYAML

環境設定（.env）
----------------
プロジェクトルートに .env を置くか、環境変数を設定します。推奨は対話式ウィザードを使う方法です。

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション（デフォルト値）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- LOG_LEVEL — INFO
- LOG_DIR — logs/
- OPENAI_API_KEY — OpenAI を使用する場合
- PAPER_FILL_MODE — instant|partial|never|reject（paper_trading の約定挙動）
- KILL_FLAG_CLEAR_ON_START — 0/1（起動時に kill.flag を自動クリアするか）

対話式ウィザード:
- python -m kabusys.config_setup

設定検証:
- python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱いで exit(1)

データベース
----------
- DuckDB（分析用）: デフォルト data/kabusys.duckdb
- SQLite（監視ログ）: デフォルト data/monitoring.db
- Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

監視 DB の初期化は起動スクリプト側で自動実行されます（init_monitoring_db）。

基本的な使い方
--------------
- ExecutionEngine（発注エンジン）を起動:
  - python -m kabusys.run_execution
  - 挙動は KABUSYS_ENV に依存:
    - paper_trading: MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録
    - live: 実ブローカーで発注
  - 停止制御:
    - data/stop_requested.flag を作成するとループを終了（run_execution / run_monitoring が参照）
    - monitoring により条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine に停止指示が出る

- Monitoring（監視ループ）を起動:
  - MONITOR_POLL_INTERVAL (秒) でポーリング間隔を変更可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / リサーチ機能（プログラム的に呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # conn は duckdb 接続
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic ...
    - 各関数は duckdb 接続と target_date を受け取る

ログ
---
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- ログの出力先は LOG_DIR 環境変数または setup_logging の引数で変更可能。
- ログレベルは LOG_LEVEL（DEBUG/INFO/...）で制御

プロセス優先度と終了制御
-----------------------
- 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限不足時は警告のみ。
- 監視プロセス / 実行プロセスは stop_requested.flag / kill.flag によって安全に停止できます。

ファイルベースのシグナル
- data/stop_requested.flag: 手動で作成すると run_* スクリプトが検知して停止
- data/kill.flag: Monitoring がリスク条件を検知して ExecutionEngine を停止させるために書き込む
- PID ファイル: data/execution.pid（ExecutionEngine が使用）

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env のローディングと Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity
  - execution/               — 発注関連コンポーネント（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/               — ポートフォリオ構築（builder / sizing / risk_adjustment）
  - research/                — ファクター計算・解析
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py
  - data/ (ランタイムで生成)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (ペーパートレード時)
    - stop_requested.flag, kill.flag, execution.pid など

注意事項 / 運用上のヒント
------------------------
- 本番環境（KABUSYS_ENV=live）では kill.flag / KILL_FLAG_CLEAR_ON_START の設定に注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番では危険です。
- .env は絶対にバージョン管理にコミットしないでください（config_setup でも同旨の注記あり）。
- OpenAI API を使う際は API キー管理に注意（環境変数 OPENAI_API_KEY を使用）。
- DB のバックアップ・ログのローテーション・プロセス監視は運用ルールに従って構成してください。
- パッケージ化 / デプロイ時は CWD に依存しないよう Settings._find_project_root がプロジェクトルートを検出しますが、適切な配置で運用してください。

問い合わせ / 拡張
-----------------
- コードはモジュール単位で拡張しやすく設計されています。AI モジュール、ブローカー実装、ポートフォリオ最適化ロジックなどを置き換えて利用できます。
- リサーチ系は DuckDB に格納された prices_daily / raw_financials / raw_news テーブルが前提です。データ投入パイプラインは kabusys.data.pipeline などに実装を追加してください。

以上がこのコードベースの README（日本語）です。必要であれば、導入手順の詳細スクリプト（requirements.txt、systemd / Supervisor サービスファイル例、Dockerfile 等）や各サブモジュールの API 使用例を追加で作成します。どの情報を優先して追加しますか？