README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークです。本リポジトリは戦略の研究・ファクター計算、ポートフォリオ構築、注文実行（本番 / ペーパートレード）、監視・アラート、AI（ニュースの NLP）などの主要コンポーネントを含みます。設計方針として「外部 API への不要なアクセスを避ける」「ルックアヘッドバイアスを防ぐ」「フェイルセーフで継続可能にする」ことを重視しています。

主な機能
--------
- 戦略・研究
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索、IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ構築
  - 候補選定、等重 / スコア重み付け、ポジションサイズ計算（単元株丸め・上限管理）
  - セクター集中制限、レジーム乗数（market regime に応じた投下資金調整）
- 注文実行
  - ExecutionEngine を用いた注文処理（本番 / paper_trading 切替）
  - RiskManager / OrderManager / Reconciler 等の組み合わせ
  - paper_trading 環境では MockBrokerClient を使用し、データは data/paper_trading.db に記録
- 監視・アラート
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による安全停止（Kill Switch）
  - SQLite に監視ログを永続化（monitoring_db）
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai_scores）
  - マクロニュース + ETF MA200 乖離を合成した市場レジーム判定
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report）

前提・依存パッケージ
-------------------
最低限必要な Python パッケージ（一例）:
- duckdb
- psutil
- openai
- PyYAML（config の詳細検証は任意。インストールされていない場合は検証をスキップします）

例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai pyyaml

セットアップ手順
---------------
1. リポジトリをクローン
    git clone <repo-url>
    cd <repo-root>

2. 仮想環境作成・依存インストール
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install duckdb psutil openai pyyaml

3. 初期環境ファイル（.env）の作成（対話式）
    python -m kabusys.config_setup
   - ウィザードが .env を生成します。生成後、必要な必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を確認してください。
   - .env は絶対に Git にコミットしないでください。

4. 設定検証
    python -m kabusys.validate_config
   - 警告も厳格に扱う場合:
    python -m kabusys.validate_config --strict

5. DB 初期化
   - 実行スクリプトは起動時に必要なテーブルを作成します（SQLite のマイグレーション処理を含む）。通常は手動で追加作業は不要です。

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用しデータは paper_sqlite_path に保存されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector などで使用）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）。デフォルト: INFO
- LOG_DIR: ログファイル保存先（デフォルト: logs/）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" ならクリア）デフォルト: 0
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

使い方（主要スクリプト）
-----------------------

- 環境設定ウィザード（.env 生成）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視ループ開始（SystemMonitor をポーリング）
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - run_monitoring は monitoring 用の sqlite_path（settings.sqlite_path）を本番設定にかかわらず使用します。
  - 停止: data/stop_requested.flag をプロジェクトルート直下に作成するとループが終了します（stop フラグの検出動作）。

- 注文実行エンジン起動
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が既に存在する場合はエンジンを起動せず終了します。
  - 実行中に停止させたい場合は data/stop_requested.flag を作成するとエンジンに停止要求が届きます（実装により安全に停止処理が行われます）。
  - PID 管理: Execution は data/execution.pid を使用します（Settings.pid_file_path でカスタマイズ可能）。

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションでファイルを指定可能。
  - レポートは稼働率、注文成功率、送信率、レイテンシ等を算出し PASS/FAIL 判定を行います。

- AI（ニューススコアリング / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必須です（関数は api_key 引数でも受け取れます）。
  - ニューススコアリング: kabusys.ai.news_nlp.score_news
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - これらは DuckDB 接続を受け取り、raw_news / news_symbols / prices_daily 等のテーブルを参照します。

停止・Kill Switch（安全停止）
---------------------------
- Kill Switch は監視コンポーネント（RiskMonitor 等）の判定により data/kill.flag を書き込み、ExecutionEngine に停止指示を出す仕組みです。
- KillSwitch.clear() を利用して起動時に kill.flag をクリアする設定（KILL_FLAG_CLEAR_ON_START=1）が用意されていますが、本番では 0 を推奨します。
- 外部から強制的に実行を停止したい場合は data/stop_requested.flag を作成してください（run_execution / run_monitoring のループが検出して終了します）。

ログ
----
- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます（TimedRotatingFileHandler 日次ローテーション、30日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging から行われます。LOG_DIR, LOG_LEVEL により挙動を変更できます。

ディレクトリ構成
---------------
（主要なファイル・パッケージのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル定義・CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - ...                    — AlertManager, TradeMonitor など（省略）
  - execution/
    - execution_engine.py    — ExecutionEngine（エンジン本体）
    - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し、スコア保存）
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py

注意事項・運用上のポイント
------------------------
- production（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0 にしてください。
- paper_trading は本番 DB と分離されます。PAPER_TRADING_SQLITE_PATH を指定することで記録先を変更できます。
- OpenAI を使う機能は API コスト・レイテンシに注意してください。API キーは安全に管理し、利用時は rate limit / retry ロジックに留意してください（実装済み）。
- logs ディレクトリ・data ディレクトリは起動時に自動作成されますが、権限等で作成に失敗する場合はコンソール出力のみになります。

開発・テスト向け情報
--------------------
- MonitoringEngine.run_once は単発実行（テスト）用に各 Monitor を 1 回だけ呼び出します。ユニットテストでの利用を想定しています。
- OpenAI 呼び出し部分は内部関数（_call_openai_api）を patch / mock してテスト可能です。
- DuckDB / SQLite に依存する関数は外部データ（prices_daily / raw_financials / raw_news 等）に依存するため、テスト時はテスト用 DB を用意するかモック化してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

お問い合わせ・貢献
-----------------
バグ報告・機能追加の提案は Issue を作成してください。プルリクエストは歓迎します。コードスタイル・テストカバレッジを維持するため、変更は小さく分けて送ることを推奨します。

以上。実行や設定で不明点があれば、具体的にどのコマンド・どのファイルで困っているかを教えてください。追加で README に加えるサンプル .env テンプレートや起動スクリプトの systemd unit 例なども作成できます。