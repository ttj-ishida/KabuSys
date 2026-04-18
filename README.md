# KabuSys

日本株向けの自動売買システムのパッケージ（ライブラリ／起動スクリプト群）。  
このリポジトリは注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースNLP／レジーム判定）等の機能を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次を主目的とするモジュール群です。

- 日次のファクター計算・特徴量探索（DuckDB ベースの時系列解析）
- 銘柄選定・配分（等配分・スコア配分・リスクベース等）
- ポジションサイズ算出（単元株丸め、max/utilization 等の制約）
- 実行エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネント
- Paper Trading（検証用のモックブローカーと専用 SQLite DB）
- ニュースを LLM でスコアリングする AI モジュール（OpenAI を使用）
- 設定ウィザード／検証用 CLI、検証レポート出力ツール

設計方針の特徴:
- データ処理は基本的に DuckDB / SQLite を利用（ローカルファイルベース）
- 重要処理はフェイルセーフ（API 失敗時は安全なデフォルトで継続）
- ルックアヘッドバイアス対策（日時参照は外部から渡す・target_date ベース）

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行 / 監視
  - 実行エンジン起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBroker を使い paper_trading DB に記録
  - 監視ループ起動スクリプト: python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を上書き可能（デフォルト 60 秒）
    - 停止は data/stop_requested.flag を作成することで行える
- 監視用コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス状態を監視
  - TradeMonitor: 発注・約定ログの整合性・滞留注文検出（コード内に実装）
  - RiskMonitor: ドローダウン監視・保有数上限監視と risk_logs への記録
  - KillSwitch: 条件を満たしたら data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB: SQLite を用いた永続層（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ（純粋関数群）
  - 銘柄選定 / スコアソート (select_candidates)
  - 等配分 / スコア加重 (calc_equal_weights / calc_score_weights)
  - セクター上限適用 (apply_sector_cap)
  - レジーム乗数 (calc_regime_multiplier)
  - 株数算出 / 単元丸め / aggregate cap (calc_position_sizes)
- 研究（research）
  - ファクター計算: モメンタム・ボラティリティ・バリュー（DuckDB 経由）
  - 将来リターン / IC 計算 / 統計サマリー
- AI
  - news_nlp: ニュース記事を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores テーブルに書き込み
  - regime_detector: ETF（1321）MA とマクロニュースセンチメントを組合せて市場レジーム（bull/neutral/bear）を判定・永続化
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## 前提条件（主な外部ライブラリ）

コード内で使用している外部パッケージの例（バージョンは環境に合わせて調整してください）:

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証で任意）
- （その他、実行環境に応じた broker client 等）

インストール例:
pip install duckdb psutil openai pyyaml

※ requirements.txt は本リポジトリに含まれていないため、実行に必要なパッケージは環境に明示的にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. 初期設定 (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（以下にサンプルを記載）
5. 設定検証
   - python -m kabusys.validate_config
   - 失敗があればメッセージに従って修正
6. データ / ログ ディレクトリの確認（通常は自動作成される）
   - data/（SQLite 等）
   - logs/（ログ）

.env の主な例（.env は絶対に Git 管理下に置かないこと）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

自動読み込み:
- 起動時に .env/.env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env を対話式で作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db） に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書き込みます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。
  - 停止:
    - data/stop_requested.flag を作成するとループが検知して終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラム的に）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

  注意: OpenAI API を使う機能は OPENAI_API_KEY が必要（api_key 引数でも可）。未設定だと例外を投げます。

- ライブラリ利用（研究・ポートフォリオ関数）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

---

## 環境変数（要確認）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨／主要:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI 機能で必要
- MONITOR_POLL_INTERVAL — 監視ループの秒数（run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START — 本番注意（live 時は 0 推奨）

設定検証は python -m kabusys.validate_config で行えます。

---

## 停止 / Kill スイッチ

- Graceful stop for loops:
  - data/stop_requested.flag — run_execution / run_monitoring のループを終了させる
- Kill Switch:
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止指示を出します（monitoring 側で判定）。KILL_FLAG_CLEAR_ON_START によって起動時に自動クリアする設定もあり（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要構成（抜粋）:

- src/kabusys/
  - __init__.py (version)
  - config.py — 環境変数 / Settings 管理、.env 自動ロードロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装あり)
  - execution/
    - execution_engine.py (実装あり)
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py / broker_factory.py 等
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

ルートにある想定ディレクトリ:
- data/ — SQLite DB / flag / pid ファイル等（実行時に作成）
- logs/ — ログファイル（setup_logging が作成）

---

## 開発者向けメモ

- ログ設定は kabusys.utils.logging_setup.setup_logging を全スクリプトで呼び出して統一してください（ファイル・コンソール両対応）。
- Settings は環境変数ベースでプロパティを提供します。Settings().is_paper / is_live で環境分岐。
- DuckDB 接続は research / ai モジュールへ直接渡して SQL 処理を行います（外部 API 呼び出しなしで分析可能）。
- テスト時に .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分（news_nlp / regime_detector）は外部 API のため、ユニットテスト時は _call_openai_api をパッチしてエミュレーションしてください（コードにもその旨注記あり）。

---

以上がこのコードベースの概要と基本的な使い方です。  
具体的な API（ExecutionEngine や OrderManager 等）の利用方法は各モジュールのドキュメント（ソース内 docstring）を参照してください。必要であれば各モジュールごとの詳細 README を作成できます。