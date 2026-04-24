KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を行うためのモジュール群です。  
主な機能は以下のとおりです。

- 発注・ExecutionEngine（本番 / ペーパートレード切替対応）
- 監視（システム状態・注文・リスク監視）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量探索）
- AI（ニュース NLP によるセンチメントスコアリング、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- ペーパートレード検証レポート生成ツール

主な設計方針：
- DuckDB（分析用）と SQLite（監視 / ペーパートレード用）を併用
- 環境変数 / .env で設定を管理（Settings クラス経由）
- 本番 / ペーパートレードは明確に分離（実 DB と paper DB）
- LLM 連携（OpenAI）機能は API キー必須、失敗時はフェイルセーフで継続

機能一覧
--------
- Execution
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により実ブローカー / モック切替）
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler 等の実装
- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングループを起動
  - MonitoringEngine: System/Trade/Risk Monitor を統合してアラート・Kill Switch を評価
  - MonitoringDB: 監視用 SQLite テーブル（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio
  - 銘柄選定（select_candidates）、重み計算（等金額 / スコア加重）
  - セクターキャップ、レジーム乗数、ポジションサイズ計算（lots 単位で丸め）
- Research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、ai_scores を更新
  - regime_detector.score_regime: ETF の MA やマクロ記事を使って市場レジーム判定
- Tools
  - tools.paper_verification_report: ペーパートレード DB から PASS/FAIL 判定付きレポート生成
- ユーティリティ
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: 設定検証 CLI（strict モードあり）
  - utils.logging_setup: 一貫したロギング（コンソール + 日次ローテーションファイル）
  - utils.process_priority: プラットフォーム非依存のプロセス優先度 / CPU affinity 設定

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - 本説明はパッケージが src/ 配下にある想定です。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主な外部依存（最低限推奨）:
     - duckdb, psutil, openai, pyyaml（config 検証で必要）など

4. 環境変数 / .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成後、内容を確認して必要な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳格扱いする場合:
     - python -m kabusys.validate_config --strict

6. DB の初期化
   - run_execution / run_monitoring 起動時に必要テーブルは自動作成（init_monitoring_db）されます。
   - DuckDB ファイル（分析用）は設定されたパスに作成されます。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV
  - 値: development | paper_trading | live
  - 役割: 実行モード。paper_trading の場合は MockBroker を使用して paper DB に記録。
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログファイル保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" でクリア）

使い方（コマンド例）
-------------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
    - 起動中は data/execution.pid（デフォルト）に PID を書きます。
    - 停止は data/stop_requested.flag を作成するか、Engine 側の kill.flag による停止検出で行います。

- Monitoring 起動（監視ループ）
  - MONITOR_POLL_INTERVAL を上書きする場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に（KABUSYS_ENV に関係なく）本番 sqlite_path を使用して監視テーブルへ記録します。

- ペーパートレード検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

停止 / Kill Switch
------------------
- ExecutionEngine の停止要求:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。
- Kill Switch:
  - RiskMonitor 等の判定で kabusys.monitoring.kill_switch.KillSwitch が data/kill.flag を書き込む場合があります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を消します（本番では危険なので 0 推奨）。

ログ
---
- 共通のログ設定ユーティリティを用いて stdout とファイル（logs/<app_name>.log）へ出力します。
- ログディレクトリは LOG_DIR 環境変数または既定の logs/ が使用されます。
- TimedRotatingFileHandler により日次ローテーション・30日分保持。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はコードベースに含まれる主要モジュールの概要（src/kabusys 配下）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード機能付き）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite テーブル初期化 + CRUD ラッパー
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常の監視（ファイルに記載の想定実装）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — Monitor を束ねるエンジン（run() / run_once()）
    - alert_manager.py        — （アラート送信）※実装参照
  - execution/
    - execution_engine.py     — ExecutionEngine（セッション実行本体）
    - broker_factory.py       — ブローカークライアント生成（本番/モック）
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
    - news_nlp.py             — OpenAI を使ったニュースセンチメント処理
    - regime_detector.py      — レジーム判定（MA + マクロセンチメント）
  - data/                     — デフォルトの DB/log/pid/flag 等が置かれる想定ディレクトリ（実行時自動作成）
  - tools/
    - paper_verification_report.py

注意事項 / 運用メモ
-------------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知等の設定を必ず確認してください。
- OpenAI 連携機能は API 料金・レート制限に注意して運用してください。失敗時はフェイルセーフで継続する設計ですが、出力品質やコスト管理は運用者の責任です。
- .env は決してリポジトリにコミットしないでください（config_setup.py のコメントにも記載）。
- DB のバックアップやログローテーションのポリシーは運用環境に合わせて調整してください。
- process_priority はプラットフォーム依存の権限により失敗する場合があります（警告ログのみ）。

貢献 / 開発
-----------
- ローカル開発では KABUSYS_ENV=development を使用してください（発注等は行われません）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを無効化できます。
- 既存の DB スキーマに対する互換性を保つため、monitoring_db.init_monitoring_db は冪等かつ簡易マイグレーションを含みます。

以上。実際に起動してみて不明点や追加してほしいドキュメント（例: API 仕様、DB スキーマ説明、運用手順書など）があれば教えてください。