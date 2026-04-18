KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部実装です。  
モジュールは監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI を使ったニュース解析（AI）などで構成されています。

この README ではプロジェクト概要、主な機能、セットアップ手順、起動／使い方、およびディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
- 自動売買に必要な以下の機能を提供する Python パッケージ:
  - 実行エンジン（ExecutionEngine）：ブローカクライアントを介した発注管理、リスク制御、オーダー調整
  - 監視（Monitoring）：システム状態・注文ログ・リスク監視、Kill Switch（フラグファイル）による安全停止
  - ポートフォリオ構築（Portfolio）：銘柄選定、重み付け、ポジションサイズ計算、セクター制約
  - リサーチ（Research）：ファクター計算（Momentum / Value / Volatility 等）および特徴量探索（IC 等）
  - AI（news_nlp / regime_detector）：OpenAI を用いたニュースセンチメント評価、マーケットレジーム判定
  - ユーティリティ：ログ設定、プロセス優先度、設定管理、.env ウィザード、構成検証ツール 等

主な機能一覧
--------------
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - インタラクティブな .env 作成ウィザード（kabusys.config_setup）
  - 起動前の設定検証（kabusys.validate_config）
- 実行エンジン（run_execution.py）
  - 本番 / ペーパートレードを切替可能（KABUSYS_ENV）
  - Paper Trading 時は専用 SQLite ファイル（data/paper_trading.db）を使用し本番 DB と分離
  - プロセス優先度設定、PID ファイル出力、停止フラグ監視
- 監視（run_monitoring.py / monitoring.*）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor / RiskMonitor: 注文の滞留・約定異常・ドローダウン等の監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止
  - Monitoring DB（SQLite）による永続化（system_status/trade_logs/positions/risk_logs/dashboard）
- ポートフォリオ構築（portfolio.*）
  - 候補選定、等配分／スコア配分、リスクベースのポジションサイズ計算
  - セクター集中制限・レジーム乗数（calc_regime_multiplier）
- リサーチ（research.*）
  - DuckDB を用いたファクター計算（momentum/value/volatility）
  - 将来リターン計算 / IC（Information Coefficient）算出 / 統計サマリ
- AI（ai.*）
  - news_nlp: raw_news から銘柄別ニュースを集約して OpenAI (gpt-4o-mini) でセンチメント評価、ai_scores へ保存
  - regime_detector: ETF 1321 の MA200 乖離 + マクロニュースで市場レジーム判定し DB に保存
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. リポジトリをクローンし、ワークディレクトリを設定
   - project root が .git または pyproject.toml を含むことを想定しています。

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 主要依存（コード内 import を参照）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証時に推奨）
   - 例（pip）:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があればそれを使用してください）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（必須環境変数は以下）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 参考: config_setup が作成する .env の項目:
     - KABUSYS_ENV（development / paper_trading / live）
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
     - DUCKDB_PATH, SQLITE_PATH
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意）
     - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START

5. 設定確認
   - python -m kabusys.validate_config
   - 問題があれば修正してください。--strict オプションで警告も失敗扱いにできます。

6. データディレクトリの作成
   - デフォルトでは data/ に DB・フラグ・pid を作成します。必要に応じてパーミッション等を確認してください。
   - ログは logs/ に出力されます（setup_logging に依存）。

基本的な使い方（起動／停止）
----------------------------
- 実行エンジン（発注実行）
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB とは分離）
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止
    - 実行中は data/stop_requested.flag を監視し、存在したらエンジン停止処理を行う
  - PID ファイル:
    - デフォルト: data/execution.pid（Settings.pid_file_path で変更可）

- 監視プロセス（ポーリング）
  - 起動:
    - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
    - 監視は Settings.sqlite_path（data/monitoring.db など）を使用
    - 停止用フラグ: src 内で定義された stop flag（data/stop_requested.flag）を検出するとループを終了
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Kill Switch（自動停止トリガ）
  - RiskMonitor 等が危険な状態（ドローダウンやポジション上限超過）を検出すると KillSwitch が data/kill.flag を書き込みます。
  - ExecutionEngine は起動時／実行中に kill.flag の存在を参照して停止します（本番安全機構）。
  - KillSwitch は一度書き込むと冪等（既存ファイルがあれば再書き込みしない）です。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされる設定がありますが、本番では 0 を推奨します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用トークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
  - paper_trading にすると発注はモックで本番 DB と分離
- OPENAI_API_KEY — OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=する, 0=しない）

ディレクトリ構成
-----------------
（src/kabusys 以下を基準に抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/.env 読み込み・Settings クラス
    - config_setup.py          — 対話式 .env ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - monitoring/
      - monitoring_db.py       — SQLite スキーマ / MonitoringDB ラッパー
      - system_monitor.py      — CPU/メモリ/Disk / データ鮮度監視
      - trade_monitor.py       — （注文ログ監視、コード内に実装あり）
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag の作成・管理
      - monitoring_engine.py   — 各 Monitor を束ねるエンジン
      - alert_manager.py       — （アラート送信ロジック）
    - execution/
      - execution_engine.py    — ExecutionEngine 実装
      - order_manager.py       — 発注管理
      - order_repository.py    — 注文履歴保存
      - reconciler.py          — 注文調整
      - broker_factory.py      — BrokerClientFactory（本番/モック分離）
      - risk_manager.py        — リスク管理ロジック
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み計算
      - position_sizing.py     — 発注株数計算
      - risk_adjustment.py     — セクター制限・レジーム乗数
    - research/
      - factor_research.py     — momentum/value/volatility 計算
      - feature_exploration.py — forward returns / IC / summary
    - ai/
      - news_nlp.py            — ニュースセンチメント（OpenAI）
      - regime_detector.py     — レジーム判定（MA200 + マクロニュース）
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
    - utils/
      - logging_setup.py       — ログの統一設定
      - process_priority.py    — プロセス優先度 / CPU affinity

ログ・DB・フラグの既定位置
-------------------------
- ログ: logs/<app_name>.log（日次ローテート、30世代保持）
- DuckDB: data/kabusys.duckdb（変更可）
- 監視 SQLite: data/monitoring.db（変更可）
- ペーパートレード SQLite: data/paper_trading.db（paper_trading 時）
- PID / stop / kill フラグ:
  - data/execution.pid（ExecutionEngine の PID ファイル）
  - data/stop_requested.flag（外部からの「即時停止」指示用）
  - data/kill.flag（KillSwitch により作成される停止フラグ）

開発・デバッグ時のポイント
-------------------------
- .env 自動ロードはプロジェクトルートの検出に依存（.git または pyproject.toml が必要）
- .env の自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- ロギングは setup_logging() で統一的に設定するため、スクリプト冒頭で呼び出してください
- OpenAI 呼び出しはリトライとフェイルセーフが組み込まれているが、API キーの設定とコストに注意してください
- DuckDB クエリはローカル DB（prices_daily / raw_financials / raw_news 等）を参照する設計です。適切なデータ投入が必要です

よくある運用ユースケース
-----------------------
- ローカル開発（発注なし）:
  - KABUSYS_ENV=development に設定 → 実行エンジンは発注を行わない実装（設定に応じる）
- ペーパートレード検証:
  - KABUSYS_ENV=paper_trading に設定 → Mock broker を使い data/paper_trading.db に記録
  - 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 本番運用:
  - KABUSYS_ENV=live。LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）の確認を推奨
  - validate_config.py で事前に guard を確認（KILL_FLAG_CLEAR_ON_START は 0 を推奨）

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE（存在する場合）を参照してください。
- バグ報告・機能追加は Issue / Pull Request を通じてお願いします。

補足
----
- この README はソースコードのコメントと構造に基づいて作成しています。実運用に際してはテスト・監査・セキュリティ検討を十分に行ってください。
- 実際のブローカ接続やマネー管理は重大なリスクを伴います。paper_trading で十分に検証した後に live 運用を開始してください。

必要であれば、起動シーケンス図や主要クラスの API 仕様、よく使う CLI コマンドの例（systemd / Docker / docker-compose）や、想定される依存関係の requirements.txt を別ファイルで作成します。どれを追加しますか？