KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（プロトタイプ）です。  
主に発注エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、リサーチ・ファクター計算、AI（ニュースセンチメント／レジーム判定）などのコンポーネントを含みます。モジュール設計はテストしやすく、環境ごとの分離（paper_trading vs live）やフェイルセーフを重視しています。

主な機能
--------
- Execution Engine
  - 本番／ペーパートレード（KABUSYS_ENV=paper_trading で MockBroker を使用）
  - 注文管理・リスク管理・照合（reconciler）
  - 発注ログの永続化（SQLite）
- Monitoring
  - システム状態（CPU/MEM/DISK）、データ鮮度、プロセス死活、注文状態の監視
  - Kill Switch（閾値超過で data/kill.flag を書き込み ExecutionEngine を停止）
  - アラート送信フック（LINE などに接続可能）
- Portfolio Construction
  - 候補選定、等分配・スコア加重配分、リスク調整（セクター上限・レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - DuckDB を用いたファクター計算（Momentum/Volatility/Value 等）
  - 将来リターン・IC 解析・統計サマリ用ユーティリティ
- AI（OpenAI 経由）
  - ニュース記事のセンチメント化（ai_scores テーブルへ保存）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（market_regime テーブルへ保存）
  - OpenAI 呼び出しは堅牢なリトライ・バリデーションを実装
- ツール
  - Paper Trading の検証レポート出力スクリプト（tools/paper_verification_report.py）
- 設定管理・ユーティリティ
  - .env 対話式ウィザード（config_setup.py）と起動前検証 CLI（validate_config.py）
  - 統一ログ設定（utils/logging_setup.py）
  - プロセス優先度設定（utils/process_priority.py）

必要条件
--------
- Python 3.10+
- 主要依存:
  - duckdb
  - openai
  - psutil
  - （オプション）PyYAML（config/*.yaml の検証）
- 標準ライブラリの sqlite3 等を使用

セットアップ手順
--------------
1. リポジトリをクローンして任意の仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb openai psutil
   - YAML 検証を有効にする場合: pip install pyyaml

3. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 必要なら厳格モード: python -m kabusys.validate_config --strict

4. データディレクトリ（デフォルト: data/）や logs/ を作成（setup は自動で作成する箇所もありますが事前に用意しておくと安全）
   - mkdir -p data logs

主要な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合 必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注は MockBroker により data/paper_trading.db に記録され、本番 DB と分離されます
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- KILL_FLAG_CLEAR_ON_START (0/1) — Execution 起動時に kill.flag を自動クリアするか
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

例: 最小 .env（ウィザードで作成推奨）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO

基本的な使い方
--------------
- 実行エンジンを起動する
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker が使用され data/paper_trading.db に発注ログが残ります
  - 起動時に data/stop_requested.flag があると起動を行わず終了します
  - 実行中に data/stop_requested.flag を作成するとエンジンが安全に停止します

- 監視プロセスを起動する
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は常に本番用の sqlite_path を使用して監視ログを永続化します
  - 監視が Kill Switch 条件を満たすと data/kill.flag を書き込み、ExecutionEngine の停止を促します

- 設定ウィザード（.env を生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH も指定可能

- AI 機能（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を設定すること（引数で渡すことも可能な関数もあります）
  - Python API 例:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力（30日分保持）
- コンソールには stdout に出力されます（stderr ではない）
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されます

停止（Kill Switch / Stop Flag）
------------------------------
- ExecutionEngine の停止は主に以下の方法で行います:
  - Kill Switch: 監視が閾値を越えた場合 monitoring が data/kill.flag を書き込み（Execution は Settings.kill_flag_path を監視して停止）
  - 手動停止: data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して安全に終了します
- KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に kill.flag を自動クリアします（本番では 0 を推奨）

データベースとマイグレーション
-----------------------------
- 監視用 SQLite の初期化 / マイグレーションは monitoring_db.init_monitoring_db が担います
  - テーブル: system_status, trade_logs, positions, risk_logs, dashboard
  - 既存 DB にカラムがない場合の軽微なマイグレーションロジックあり（例: latency_ms, peak_value の追加）

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数ロード / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (※実装ファイルがある想定)
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py (※通知管理のためのフック想定)
    - kill_switch.py
  - execution/
    - execution_engine.py (エンジン本体)
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

設計上の注意点
--------------
- 本システムはルックアヘッドバイアス防止を強く意識して設計されています（target_date 未満条件の徹底、datetime.today() の非使用など）。
- AI 呼び出しは堅牢化（リトライ、レスポンス検証）されていますが、誤応答を完全に排除するものではありません。AI 機能を有効にする場合は API キー情報・コストに注意してください。
- 本番運用時は KABUSYS_ENV=live の設定・LINE 通知などを十分に確認し、KILL_FLAG_CLEAR_ON_START=0 を推奨します。

貢献・拡張
----------
- strategy / execution の実装拡張、ブローカープラグイン追加、アラート送信先追加（LINE/webhook/Slack）などを想定しています。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）に合わせて research/ai モジュールを拡張してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス表記はリポジトリに応じて追加してください。

補足
----
- ここに書かれているコマンドや環境変数はリポジトリ内のスクリプト仕様に基づきます。実運用前に必ず validate_config で設定を確認し、テスト環境（paper_trading）で十分に動作検証を行ってください。質問や追加のドキュメントが必要であれば教えてください。