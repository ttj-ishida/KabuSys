README
======

概要
----
KabuSys は日本株の自動売買・リサーチ基盤です。本リポジトリは以下の主要機能を持つモジュール群を含みます。

- ExecutionEngine（発注エンジン）と Monitoring（監視）による運用基盤
- Portfolio 構築（候補選定、重み付け、株数計算）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュースのセンチメント評価・市場レジーム判定）
- 各種ユーティリティ（設定読み込み、ログ設定、プロセス優先度など）
- 開発用の CLI（.env ウィザード、設定検証、Paper Trading レポート生成）

主な設計方針として、
- 本番/ペーパートレード DB を分離（KABUSYS_ENV に依存）
- ルックアヘッドバイアス回避（日付の取り扱いを慎重に実装）
- フェイルセーフ（外部 API 失敗時は安全側にフォールバック）
があります。

機能一覧
--------
- run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading 時は MockBroker）
- run_monitoring: SystemMonitor のポーリング起動（MONITOR_POLL_INTERVAL で間隔調整）
- config_setup: 対話式 .env 作成ウィザード
- validate_config: .env および config/*.yaml の事前検証 CLI
- tools.paper_verification_report: Paper Trading の検証レポート生成
- portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター制限
- research: ファクター計算（モメンタム・ボラティリティ・バリュー）・IC / 統計解析
- ai.news_nlp: OpenAI を使ったニュースのセンチメントスコアリング（ai_scores へ書込）
- ai.regime_detector: マクロニュースと ETF MA200 を組み合わせた市場レジーム判定
- monitoring: system/trade/risk を監視し kill.flag 生成やアラート通知を行う
- utils: ログ設定、プロセス優先度/CPU affinity 設定 など

セットアップ手順
----------------
前提
- Python 3.9+（ソースは型注釈を使用）
- SQLite（組み込み）、DuckDB（Python パッケージ）
- 外部ライブラリ: duckdb, psutil, openai, PyYAML（YAML 検証用、任意）

推奨手順（ローカル）
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （開発用）pip install PyYAML

   依存関係例:
   - duckdb
   - psutil
   - openai
   - PyYAML（任意）

4. .env の作成
   - python -m kabusys.config_setup
   - あるいは .env を手動で作成（下記「環境変数例」参照）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います

6. データディレクトリ作成（必要に応じて）
   - デフォルト DB / ログ / pid ディレクトリは data/, logs/ を想定しています

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意・挙動に影響するもの
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
    - paper_trading: MockBroker を使用し paper_trading.db にデータを記録
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB。デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/…、デフォルト: INFO）
  - OPENAI_API_KEY（AI 機能を使う場合必須）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（監視・停止制御）

.env の簡易例
（config_setup を使えば対話式に生成されます）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

使い方
------
起動スクリプト
- ExecutionEngine（エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード用 DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 停止させたい場合はデータディレクトリに kill.flag を作成（KillSwitch 経由）や stop_requested.flag を作る

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず）

CLI ユーティリティ
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

AI / Research API（ライブラリ的利用）
- ニュースのセンチメント付与（プログラムから呼ぶ）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=None)
  - api_key が None の場合は環境変数 OPENAI_API_KEY を参照

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=None)

ログ・監視
- ログファイル: logs/<app_name>.log（日次ローテーション、デフォルト 30 日保持）
- ログ出力は標準出力とファイルの両方に出ます（utils.logging_setup.setup_logging）
- 停止フラグ:
  - data/stop_requested.flag : run_monitoring/run_execution がチェックする停止トリガー（存在でループを抜ける）
  - data/kill.flag : KillSwitch が生成し、ExecutionEngine に停止を促す（起動時に自動クリア設定がある）

ディレクトリ構成
----------------
リポジトリの主要なファイル・ディレクトリ（src/kabusys を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings ラッパー（自動 .env ロード機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — OpenAI を使ったニューススコアリング
    - regime_detector.py       — マクロ + MA200 でレジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 + DB 操作用クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                 — 発注エンジン関連（Engine / BrokerFactory / OrderManager 等）
  - data/                      — データ / DB / フラグファイル（実行時に使用するディレクトリ）
- config/                      — YAML 設定ファイル群（テンプレート生成スクリプトあり）
- logs/                        — デフォルトログ出力先（実行時に自動生成）

注意事項
--------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup.py の注意書き参照）。
- OpenAI API を使う機能は料金が発生する可能性があります。利用時はキー管理とコストに注意してください。
- KABUSYS_ENV=live は実際に発注を行う設定です。運用前に validate_config で設定を十分確認してください。
- DuckDB / SQLite のパスはデフォルトで data/ 以下を使います。運用環境では永続ストレージを指定してください。
- run_execution/run_monitoring は stop_requested.flag を監視します。停止させたい場合は data/stop_requested.flag を作成してください（ファイルの中身は任意）。

トラブルシュート
----------------
- ログが出ない / ファイルが作成されない:
  - 権限やディスク容量、LOG_DIR/LOG_LEVEL の設定を確認してください。
- OpenAI 呼び出しで失敗:
  - OPENAI_API_KEY が設定されているか、ネットワーク・レート制限を確認してください。AI モジュールはリトライ・フォールバック処理を備えていますが、キーがないと実行時にエラーになります。
- 設定検証でエラーが出る:
  - .env の必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）を確認。config/*.yaml は存在しない場合警告が出ます。

付録: よく使うコマンド
---------------------
- .env を対話作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上が本プロジェクトの概要・セットアップ・使い方の概要です。追加で README に載せたい内容（例: 要件ファイルの追加、Docker 化手順、CI 設定、より詳しい API ドキュメント等）があれば教えてください。