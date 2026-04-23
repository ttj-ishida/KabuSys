# KabuSys

日本株自動売買システムのライトウェイト実装。  
このリポジトリは戦略・ポートフォリオ構築、実行エンジン、監視・アラート、研究用ユーティリティ、AI を用いたニュース解析などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を分離して実装したモジュール群です。

- ExecutionEngine: 発注・注文管理・リスク管理を行う実行コンポーネント（本番 / ペーパートレード切替対応）
- Monitoring: システム稼働状況・注文ログ・リスク監視・Kill Switch（停止フラグ）の管理
- Portfolio: 候補選定、重み計算、ポジションサイズ決定、セクターキャップなどのポートフォリオ構築ロジック
- Research: DuckDB 上でファクター計算や統計解析を行う研究用関数群
- AI: OpenAI を用いたニュースセンチメント / レジーム判定
- Tools: ペーパートレードの検証レポート生成など補助スクリプト
- Utils: ロギング、プロセス優先度設定など運用ユーティリティ

設計方針の一例:
- 実行スクリプトは環境変数で挙動を切り替え可能（KABUSYS_ENV）
- ペーパートレードは本番 DB と明確に分離（別 SQLite ファイル）
- .env ワークフローをサポートする CLI（対話式ウィザード / 検証ツール）
- DuckDB を分析用 DB として利用

---

## 主な機能一覧

- 実行エンジン（run_execution.py）
  - ブローカークライアント抽象化（本番 / モック）
  - 注文管理（OrderManager）、リスク管理（RiskManager）、照合（Reconciler）
  - PID ファイル・停止フラグのハンドリング
- 監視（run_monitoring.py / monitoring/*）
  - CPU / メモリ / ディスク使用率監視
  - Execution プロセス監視（PID ファイルチェック）
  - 注文ログ・ポジション・リスクログの永続化（SQLite）
  - Kill Switch（閾値を超えた場合に data/kill.flag を書き込み Execution を停止）
  - アラート送信フック（AlertManager 経由）
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等重配分・スコア加重、リスクベースのポジション決定
  - セクター集中制限、レジーム乗数
- リサーチ（research/*）
  - Momentum / Volatility / Value ファクター計算（DuckDB 上で完結）
  - 将来リターン計算、IC（情報係数）など
- AI（ai/*）
  - ニュース記事を集約して OpenAI でセンチメント評価し ai_scores に書き込む
  - マクロニュース + ETF MA を用いた市場レジーム判定
- ユーティリティ
  - ログ設定（logs/ に日次ローテート）
  - プロセス優先度・CPU affinity 設定
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定ワークフロー
  - 対話式 .env 作成（config_setup.py）
  - 起動前チェック（validate_config.py）

---

## セットアップ手順（ローカル）

1. リポジトリをクローン／チェックアウト

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール  
   ※ requirements.txt がある場合はそれを利用してください。無い場合の例：
   - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（リポジトリルートに配置）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（抜粋）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db) — 注: monitoring は環境にかかわらずこの本番 sqlite_path を使用
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI モジュールを使う場合)
     - LOG_LEVEL, LOG_DIR
     - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルトでは data/ と logs/ を使用します。必要なら作成してください（多くのスクリプトは自動作成します）。

---

## 起動・使い方

注意: 実行スクリプトはモジュールとして起動できます（例: python -m kabusys.run_execution）

- ExecutionEngine を起動（本番またはペーパートレードは KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - ペーパートレード環境では Settings.is_paper が True になり、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します
  - 実行中の PID ファイル: data/execution.pid（デフォルト。Settings.pid_file_path で変更可）
  - 停止: data/stop_requested.flag（stop フラグファイル）を作成すると実行中スレッドが検知して停止します

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - モニタは Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（KABUSYS_ENV に依らず本番 monitoring DB を使う点に注意）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視の停止は data/stop_requested.flag を作成（または KeyboardInterrupt）

- Kill Switch（監視から発動）
  - 条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine は起動時または稼働中にこのフラグを検知して停止します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアしますが、本番では 0 を推奨

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI モジュール（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ログ
  - 標準出力（stdout）と logs/<app_name>.log に日次ローテートで出力（30 日分保持）
  - setup_logging() で統一設定されます
  - ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/

---

## 環境変数一覧（重要なもの抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db) — Monitoring は常に本番用 sqlite_path を使います
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (ペーパートレード時の約定モード: instant|partial|never|reject、デフォルト instant)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- LOG_DIR
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数、デフォルト 60)
- PID_FILE_PATH (Execution pid ファイルパス、デフォルト data/execution.pid)
- KILL_FLAG_PATH (Kill Switch の flag パス、デフォルト data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: "1" で有効)

---

## 運用上の注意

- monitoring は Settings.sqlite_path（監視 DB）を使用します。KABUSYS_ENV に関係なく本番監視 DB を参照する意図的な実装になっています。ペーパートレードの監視を別に行いたい場合は設計を調整してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して DB を完全分離します。
- Kill Switch 周りは意図的に厳しめ（デフォルト閾値など）に設計されています。本番運用前に validate_config で設定を確認してください。
- OpenAI や外部 API を利用する機能は API レート制限・一時エラーを考慮したリトライロジックが実装されていますが、API キーとコスト管理は適切に行ってください。
- ロギングのファイル出力に失敗した場合、コンソールのみで継続します（警告ログが出力されます）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — 対話式 .env 作成ウィザード
  - validate_config.py            — 起動前の設定検証ツール
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                 — ニュース NLP スコアリング
    - regime_detector.py          — レジーム判定
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (実装ファイルが存在する前提)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装ファイルが存在する前提)
  - execution/
    - execution_engine.py (実装ファイルが存在する前提)
    - broker_factory.py (実装ファイルが存在する前提)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/ (想定されるデータディレクトリ)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (ペーパートレード用)
    - kabusys.duckdb (DuckDB)
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリにはさらに細かなファイルやテストが含まれる場合があります）

---

## 参考コマンドまとめ

- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python REPL から機能呼び出し例（DuckDB 接続等の準備が必要）:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.research import calc_momentum

---

問題や追加で README に加えたい項目（例: 詳細な設定例、依存関係の正確な一覧、運用手順書）などあれば教えてください。必要に応じて README を拡張します。