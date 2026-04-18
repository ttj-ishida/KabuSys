KabuSys
=======

プロジェクト概要
----------------
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
主な目的は次のとおりです。

- 日次のファクタ計算・リサーチ（DuckDB ベース）
- 市場レジーム判定やニュース NLP によるセンチメント評価（OpenAI を利用）
- ExecutionEngine（発注エンジン）および監視（Monitoring）コンポーネント
- Paper Trading（疑似発注）用の分離された DB と検証ツール
- 監視ログ／リスク監視・Kill Switch による安全停止機構

機能一覧
--------
- 設定管理:
  - .env ウィザード（kabusys.config_setup）で初期設定を対話的に作成
  - 設定検証 CLI（kabusys.validate_config）で起動前チェック
- 実行コンポーネント:
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV に応じてペーパートレード用のモックブローカーを使用可能
    - paper_trading 時は data/paper_trading.db に書き込み（本番 DB と分離）
  - Monitoring（監視）ポーリングループ（kabusys.run_monitoring）
    - CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度、取引ログなどを監視
    - Kill Switch により重篤なリスクで Execution を停止
- モジュール群:
  - portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター制約など
  - research: ファクター計算（モメンタム／ボラティリティ／バリュー）、IC 等の解析
  - ai: ニュース NLP（OpenAI）による銘柄センチメント、レジーム判定
  - monitoring: 監視用 DB 層、各種モニター、アラート／Kill Switch 実装
  - utils: ログ設定、プロセス優先度設定などユーティリティ
- ツール:
  - paper_verification_report: Paper Trading の検証レポート生成

セットアップ手順
----------------
1. リポジトリをクローン / パッケージを配置
   - 開発環境ではプロジェクトルート（pyproject.toml や .git がある階層）を基準に動作します。

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な外部依存:
     - duckdb, psutil, openai, PyYAML（config 検証用）
     - 例: pip install duckdb psutil openai PyYAML

4. ディレクトリ作成（初回）
   - data/ および logs/ を作成しておくとよいです（ログや DB のデフォルト保存先）。
     - mkdir -p data logs

5. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - またはリポジトリにある .env.example を参考に作成してください。
   - 必須環境変数例:
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）

6. （任意）設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------
全ての CLI はパッケージモジュールとして実行できます。代表的なコマンドは以下の通りです。

- ExecutionEngine を起動（本番または paper_trading に応じて振る舞いが変わります）
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag があると起動しません。
  - 実行中は data/execution.pid に PID を書きます（設定で変更可能）。

- Monitoring を起動（ポーリングで各種チェック）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - data/stop_requested.flag を作成するとループが終了します。
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を参照します（環境に依らず本番監視 DB を使用）。

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db でデータベースパスを明示可（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

停止・Kill Switch に関する操作
- Execution を外部から停止したい場合:
  - Kill Switch（kabusys.monitoring.kill_switch）は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 手動で停止フラグを立てる場合は data/stop_requested.flag を作成すると各 run_* スクリプトが検知して終了します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番環境では 0 を推奨）。

重要な環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1)
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging により行われます。
- デフォルトでは logs/<app_name>.log に日次ローテーション（30 日保持）で出力されます。log_dir は LOG_DIR 環境変数または setup_logging の引数で変更可能。
- コンソール出力は stdout に出ます（task scheduler や cron での取り扱いを考慮）。

データベース
------------
- DuckDB: 分析用途。デフォルト data/kabusys.duckdb
- SQLite:
  - 監視 DB（monitoring.db）: system_status, trade_logs, positions, risk_logs, dashboard 等のテーブルを持つ
    - init_monitoring_db が起動時にテーブルを冪等で初期化／マイグレーションします
  - paper_trading.db: ペーパートレードの注文ログ等（paper_trading 実行時に使用）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要ファイル構成の概略です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — IC 等の解析ユーティリティ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — （trade_monitor 実装あり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信処理）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

（注）上記はコードベースの一部抜粋に基づく主要ファイル一覧です。実際のリポジトリ内に他のファイル・サブパッケージが存在する場合があります。

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア等の設定に注意してください（KILL_FLAG_CLEAR_ON_START=0 推奨）。
- OpenAI API を使用する処理（news_nlp, regime_detector）は API 呼び出し失敗時にフェイルセーフ（0.0 等）で継続するよう設計されていますが、API キーは適切に保護してください。
- Paper Trading（is_paper）は発注ロジックと DB を分離しています。ペーパートレード結果は data/paper_trading.db に記録されます。
- ログ・DB への書き込み権限、ディスク容量に注意してください。

トラブルシューティング（簡易）
-----------------------------
- .env が読み込まれない／設定が反映されない:
  - プロジェクトルートが正しく検出されているか（.git または pyproject.toml が存在）を確認。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されている場合、自動読み込みはスキップされます。
- Monitoring がすぐ停止する:
  - data/stop_requested.flag や data/kill.flag の存在を確認。
- OpenAI 呼び出しで失敗する:
  - OPENAI_API_KEY が有効か、ネットワーク接続を確認。RateLimit や一時障害はリトライ実装があります。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__（現在は 0.1.0 が設定されています）。
- ライセンスはリポジトリに付随する LICENSE を参照してください（存在する場合）。

補足
----
- 詳細な設計（PortfolioConstruction.md / StrategyModel.md 等）が参照される実装コメントが各所に含まれています。運用や戦略の微調整はそれらのドキュメントを参照してください。
- 開発・テスト時は KABUSYS_ENV=development を使用し、本番用設定（live）は十分に検証した上で適用してください。

以上。README の内容について補足やプロジェクト固有の追加情報（インストールスクリプト、CI ワークフロー、実行例のログ抜粋等）が必要であれば教えてください。