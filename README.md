# KabuSys

KabuSys は日本株の自動売買システム（学術/実運用用のプロトタイプ）です。本リポジトリは以下の主要コンポーネントを含みます：注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、ニュース NLP（LLM によるセンチメント評価）など。

バージョン: 0.1.0

---

## プロジェクト概要

- 注文実行（ExecutionEngine）とそれを補助する OrderManager / RiskManager / Reconciler 等の実装。
- 監視コンポーネント（System / Trade / Risk Monitor）による稼働監視および Kill Switch（停止フラグ）機能。
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ決定、セクター制限、レジーム乗数）。
- リサーチ用モジュール（ファクター計算、将来リターン、IC 計算、統計要約）。
- ニュース NLP（OpenAI を利用した銘柄ごとのセンチメントスコア算出）とレジーム判定（MA200 とマクロニュースの組合せ）。
- 運用補助ツール（.env 対話式ウィザード、設定検証、Paper Trading 検証レポート生成など）。
- ログ、プロセス優先度や CPU affinity のユーティリティを提供。

---

## 主な機能一覧

- Execution:
  - 実売買 / ペーパートレードの分離（KABUSYS_ENV による切替）
  - MockBrokerClient を用いたペーパートレード（データは data/paper_trading.db に記録）
  - RiskManager によるポジション制約・レート制限など
- Monitoring:
  - system_status / trade_logs / risk_logs / dashboard 等の永続化（SQLite）
  - プロセス生存確認・データ鮮度チェック・滞留注文検出・ドローダウン監視
  - Kill Switch: 重大なリスクを検知した際の停止フラグ書き込み
- Research:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- AI:
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores への書き込み）
  - マクロニュース + ETF MA200 による市場レジーム判定
- Utilities:
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ロギング設定ユーティリティ（logs 日次ローテート）
  - process priority / CPU affinity 設定ユーティリティ

---

## 要件 (概略)

- Python 3.10+
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合に必要）
- 標準ライブラリ: sqlite3 等

※ 実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を参照してください（存在する場合）。

---

## セットアップ手順

例: Unix 系 OS を想定

1. リポジトリをクローン/チェックアウト
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - 例（代表パッケージ）:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt / pyproject.toml がある場合はそれに従ってください:
     - pip install -r requirements.txt

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 本番運用時は KABUSYS_ENV=live、ペーパートレード時は KABUSYS_ENV=paper_trading
   - ウィザードで作成した .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります:
     - python -m kabusys.validate_config --strict

6. データベース・ログディレクトリの準備
   - デフォルトは:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - Logs: logs/
   - 多くのコードは起動時にディレクトリを作成するため通常は手動作成は不要です。

7. OpenAI を使用する機能を使う場合:
   - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key 引数で渡してください。

---

## 使い方（主な実行コマンド）

- ExecutionEngine（注文実行）
  - 起動:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは data/paper_trading.db に記録されます。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中は data/execution.pid に PID を書き込みます。停止は stop フラグにより行います。

- Monitoring（監視ループ）
  - 起動:
    - python -m kabusys.run_monitoring
  - オプション:
    - ポーリング間隔の上書き: 環境変数 MONITOR_POLL_INTERVAL（秒）を設定できます（デフォルト 60 秒）。不正値や 0/負値は無視され、デフォルトにフォールバックします。
  - 注意:
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視 DB を初期化します。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（ツール）
  - 例:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / レジームスコア、ニューススコア（ライブラリ呼び出し）
  - Python から直接呼び出す例:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="sk-...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="sk-...")

---

## 動作上の注意点・運用メモ

- データベース分離:
  - ペーパートレード（KABUSYS_ENV=paper_trading）は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。
- Kill Switch:
  - KillSwitch は監視ループから条件（ドローダウンやポジション上限等）で data/kill.flag を書き込むことで ExecutionEngine に停止を要求します。
  - ExecutionEngine は起動時や実行中に kill.flag を監視し、存在すれば停止します。
  - KillFlag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）。
- ロギング:
  - setup_logging により stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）を設定します。ログディレクトリは LOG_DIR 環境変数で上書き可能。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます。設定に失敗しても警告に留まり処理は続行されます。
- DB 初期化:
  - Monitoring 起動時に init_monitoring_db() が呼ばれ、必要テーブルの作成（冪等）とスキーママイグレーション（既存列チェック→追加）を行います。
- 環境変数自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）が見つかると、.env と .env.local を自動的に読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 主要な環境変数（抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - LOG_LEVEL — デフォルト: INFO
  - OPENAI_API_KEY — OpenAI を使う場合に必須
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（詳細は Settings クラス参照）

.env ウィザードで主要項目の入力を補助します。

---

## ディレクトリ構成（主要ファイル・モジュールの概略）

- src/kabusys/
  - __init__.py — パッケージ定義、__version__
  - config.py — Settings クラス（環境変数読み込み・検証・デフォルト）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュースを LLM に送って銘柄ごとのスコアを ai_scores に書き込むロジック
    - regime_detector.py — マクロニュースと ETF MA200 を組合せレジーム判定
    - __init__.py — ai API エクスポート（score_news など）
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite スキーマ初期化・読み書きラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — （存在）滞留注文や約定異常検出（実装ファイルが同フォルダにある想定）
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — kill.flag の作成 / 解除
    - monitoring_engine.py — 各 Monitor を統合してポーリング実行
    - alert_manager.py — アラート送信管理（LINE 等。実装が存在する想定）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（run_session 等）
    - order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py — 発注関連コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・丸め・集約キャップ
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py — 主要関数のエクスポート
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py — 研究 API のエクスポート
  - data/ (実行時に生成される想定)
    - kill.flag, stop_requested.flag, execution.pid, monitoring.db, paper_trading.db, kabusys.duckdb など
  - utils/
    - logging_setup.py — 標準化されたログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 参考・運用ヒント

- 開発環境では KABUSYS_ENV=development を使い、本番やペーパーの DB を誤って上書きしないように注意してください。
- 本番（live）運用時は LINE 通知等のアラート先を必ず設定してください（validate_config で注意喚起があります）。
- Kill Flag / Stop Flag はファイルベースのシンプルな制御です。自動化スクリプトや運用手順と合わせて運用してください。
- DuckDB はリサーチ・分析向けのローカル列指向 DB として利用しています。大量データの集計時に高速です。
- OpenAI を利用する処理は API コストが発生するため、定期的なバッチやサンプリングでの運用を推奨します。

---

必要に応じて README にサンプル .env のテンプレート、systemd / supervisor 向けのユニットファイル例、より詳細な運用手順（PID 管理、ログローテーション監視など）を追加できます。追加したい内容があれば教えてください。