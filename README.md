# KabuSys

日本株向けの自動売買システム（ライブラリ + 実行スクリプト群）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 要件（依存ライブラリ）
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要項目）
- 注意点 / 運用メモ
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買を想定したモジュール群です。
- 注文実行（ExecutionEngine）、監視（MonitoringEngine）、リスク監視、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュースセンチメントや市場レジーム判定）などの機能を含みます。
- SQLite（監視/ペーパートレード）と DuckDB（分析データ）を併用する設計です。
- 設定は .env ファイル / 環境変数で管理します。対話式ウィザード・検証ツールを備えています。

機能一覧
- ExecutionEngine：発注フロー、オーダー管理、リスク管理、Reconciler 等を組み合わせた注文実行エンジン。KABUSYS_ENV に応じて実ブローカーまたはモック（ペーパー）を選択。
- Monitoring：システム状態（CPU/メモリ/ディスク）、プロセス生存、データ鮮度、注文滞留・約定異常等を監視し、ログを SQLite に永続化。
- Kill Switch：ドローダウンやポジション上限超過時にフラグファイルを書き、ExecutionEngine を停止させる仕組み。
- Portfolio construction：候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数などの純粋関数群（DB 非依存）。
- Research：DuckDB を用いたファクター計算（Momentum/Volatility/Value 等）、特徴量探索、IC 計算、統計サマリ。
- AI モジュール：ニュースを LLM（OpenAI）でスコアリングする news_nlp、マクロ×ETF を合成して市場レジームを判定する regime_detector。
- ツール：Paper Trading の検証レポート生成スクリプトなど。
- 設定管理：.env 対話ウィザード（config_setup）と設定検証 CLI（validate_config）。

要件（主な依存ライブラリ）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- （任意）PyYAML — config/*.yaml の検証に使用
※ 実際の依存バージョンは pyproject.toml 等を参照してください。

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai
   - （オプション）pip install pyyaml

3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 注意: .env は Git に含めないでください。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ（data/）の準備
   - デフォルト DB パス（必要に応じて作成されます）
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db（ペーパー用）
   - scripts 起動時に自動でディレクトリを作る処理もありますが、権限等に注意。

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
- データベース
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 時、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant|partial|never|reject）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector で必要
- ログ・監視
  - LOG_LEVEL — DEBUG|INFO|...
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト data/execution.pid）

使い方（主要コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine（本番 / ペーパーの起動）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db など）に書き込みます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。
- Monitoring（監視ループ起動）
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。
    - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV に依らない）。
    - data/stop_requested.flag を検知するとループを終了します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数、未設定時は data/paper_trading.db
- AI モジュール（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡してニューススコアを ai_scores に書き込みます。OPENAI_API_KEY が必要。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ保存します。OPENAI_API_KEY が必要。

運用上の注意 / 補足
- 自動で .env をロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Kill Switch / stop flag:
  - Kill Switch は data/kill.flag を書くことで ExecutionEngine に停止を促します（KillSwitch が評価して書き込みます）。
  - 手動で強制停止する場合は data/stop_requested.flag を置くことで run_execution/run_monitoring スクリプトに終了を指示できます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は必要なテーブル・カラム（冪等）を作成します。スクリプト起動時に呼ばれます。
- Process priority:
  - 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限がない場合は警告が出てスキップされます。
- ログ:
  - LOG_LEVEL 環境変数でログレベルを指定できます（デフォルト INFO）。

簡単な運用フロー（例）
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite のデータを準備（価格データ / raw_news など）
4. 監視を起動（本番環境で先に監視を動かすことを推奨）
   - python -m kabusys.run_monitoring
5. ExecutionEngine を起動
   - python -m kabusys.run_execution
6. 必要に応じて paper_verification_report を実行して結果を確認

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込みと Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - execution/               — 発注・エンジン関連（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ + 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — OpenAI を用いたニュースセンチメント
    - regime_detector.py     — マクロ + ETF でレジーム判定
  - data/                    — （実行時に使用される data/*.db やフラグファイルを想定）
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity

開発者向けメモ
- DuckDB 接続は分析処理（research, ai）で使用され、prices_daily / raw_financials / raw_news などを参照します。
- MonitoringDB は監視・ログ保存専用の SQLite を想定し、init_monitoring_db() は安全に複数回呼べます（冪等）。
- AI モジュールは API の失敗に寛容で、失敗時はフォールバック値（0.0 等）で継続する実装方針です。
- テスト時は OpenAI 呼び出し部分をモックできるように設計されています（内部関数を patch）。

ライセンス / コントリビュート
- このリポジトリに含まれる README はコードベースの簡易ドキュメントです。実際に導入・本番運用する場合は運用手順、監視閾値、ロールバック手順、秘密情報管理（Vault 等）の追加が必要です。

---

補足: もっと詳細な API ドキュメント、各モジュールのユースケース例、設定項目の完全一覧（.env.example 形式）などが必要であれば、その内容に合わせて README を拡張できます。どの部分を詳述したいか教えてください。