# KabuSys

日本株自動売買システムの内部ライブラリ群と起動スクリプト群をまとめたリポジトリです。  
この README はコードベース（src/kabusys 以下）の利用方法・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（バックエンドライブラリ群）です。  
主に次の機能を備えています。

- 戦略の研究・ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- ExecutionEngine（発注・Order管理・リスク管理・reconciler 等）
- 監視（System / Trade / Risk）と Kill Switch（条件に応じて Execution を停止）
- Paper Trading 向け分離 DB モード
- AI 支援機能（ニュース NLP、レジーム判定） — OpenAI API 経由
- 各種ユーティリティ（ロギング設定、プロセス優先度、設定ウィザード等）
- CLI ツール：.env ウィザード、設定検証、Paper Trading 検証レポート生成 等

設計方針として、DB は DuckDB（分析）と SQLite（監視・取引ログ）を併用し、Paper Trading は本番 DB と分離されます。起動スクリプトはプロセス優先度を高く設定し、ログは stdout と日次ローテートファイルへ出力します。

---

## 主な機能一覧

- portfolio
  - 候補選定（select_candidates）
  - 等金額・スコア重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用、レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン / IC / 統計（calc_forward_returns / calc_ic / factor_summary）
- execution
  - ExecutionEngine 起動用スクリプト（run_execution.py）
  - BrokerClientFactory により実運用と PaperTrading 用 Mock を切替
  - RiskManager / OrderManager / Reconciler 等（発注・リスク制御）
- monitoring
  - System / Trade / Risk のモニタ（SystemMonitor / TradeMonitor / RiskMonitor）
  - MonitoringEngine: 各 Monitor を束ねポーリング、Alert/ KillSwitch 連携
  - MonitoringDB: SQLite に監視ログ保存（system_status, trade_logs, risk_logs, positions, dashboard）
  - KillSwitch: 条件により data/kill.flag を書き停止指示
- ai
  - ニュースを LLM（OpenAI）でスコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- ユーティリティ
  - ログセットアップ（kabusys.utils.logging_setup.setup_logging）
  - プロセス優先度設定（kabusys.utils.process_priority）
  - 環境変数/設定読み込み（kabusys.config）
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）

---

## 必要要件（主要パッケージ）

最低限必要な Python パッケージ（代表例）:

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml の中身検証に使用）

pip でのインストール例:
- pip install duckdb psutil openai pyyaml

（実際の requirements.txt がある場合はそれに従ってください）

---

## セットアップ手順

1. リポジトリをチェックアウトし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストールします。
   - pip install duckdb psutil openai pyyaml

3. データ / ログ ディレクトリを作成
   - mkdir -p data logs

4. 環境変数設定（.env）
   - 対話式ウィザードで作成するのが簡単です:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を置く（.env の自動ロードはデフォルトで有効）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（代表）:
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: PaperTrading 用 DB（paper_trading 時に使用。デフォルト data/paper_trading.db）
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - LOG_LEVEL, LOG_DIR 等

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. DB 初期化は起動時に自動で行われます（monitoring 用テーブルの作成・マイグレーション等）。

---

## 使い方（起動・実行）

すべての起動スクリプトはモジュールとして実行できます。プロジェクトルートで仮想環境を有効にしてから実行してください。

- ExecutionEngine を起動（通常運用 / Paper Trading 切替は KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。
    - 実行時に data/stop_requested.flag が設定されていると起動せずに終了します。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring を起動（ポーリングループ）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（KABUSYS_ENV にかかわらず）。
  - 監視ループの終了は project_root/data/stop_requested.flag を作成すると検出して終了します。

- 設定ウィザード（.env を対話式に作成）:
  - python -m kabusys.config_setup

- 設定検証 CLI:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は --db オプション、もしくは環境変数 PAPER_TRADING_SQLITE_PATH（未指定時は data/paper_trading.db）

- AI / 研究用関数呼び出し（ライブラリ利用例）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research.calc_momentum(conn, date) など、DuckDB 接続を渡して呼び出します。

---

## ログ・ファイル / フラグの取り扱い

- ログ
  - kabusys.utils.logging_setup.setup_logging により stdout（StreamHandler）と logs/<app_name>.log（日次ローテート）が自動的に設定されます。
  - ディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/` に作成されます。

- PID / 停止フラグ / Kill Switch
  - data/execution.pid : Execution 起動時に書き込まれる PID ファイル（run_execution が使用）
  - data/stop_requested.flag : 起動中プロセスを優雅に停止させたい場合にこのファイルを作成すると run_monitoring/run_execution のループが検知して終了します（run_execution は起動前に既に存在すると起動をキャンセルします）。
  - data/kill.flag : KillSwitch が条件を満たしたときに書き込むファイル。ExecutionEngine 側でこれを検出して停止する設計です。
  - NOTE: .env の KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- OPENAI_API_KEY — AI 機能に必要
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR — ログ格納ディレクトリ
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"0" または "1"）

.env の自動ロードについて:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出して `.env` と `.env.local` を自動で読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きできます。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 注意事項 / 運用上のヒント

- run_execution と run_monitoring は両方ともプロセス優先度を "high" に設定します（プラットフォーム依存で設定できない場合は警告が出ます）。
- Paper Trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH）。本番 DB を上書きしないよう注意してください。
- AI 機能は OpenAI API キーが必要です。API 呼び出し失敗時はフェイルセーフ（スコア 0 など）で継続する設計ですが、API 使用量に注意してください。
- ローカルでのテスト・CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して環境を明示的に制御するのが便利です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI 経由）
    - regime_detector.py           — 市場レジーム判定（OpenAI 経由）
  - monitoring/
    - monitoring_db.py            — SQLite テーブル作成・永続化層
    - monitoring_engine.py        — 各 Monitor を束ねる
    - system_monitor.py           — システム・データ鮮度監視
    - trade_monitor.py            — （TradeMonitor 実装がある想定）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — Kill Switch 実装
    - alert_manager.py            — （通知 / LINE 等の実装がある想定）
  - execution/
    - execution_engine.py         — ExecutionEngine 本体（起動・セッション管理）
    - broker_factory.py           — BrokerClientFactory（本番 / Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py            — ロギング初期化
    - process_priority.py         — プロセス優先度 / CPU affinity
    - __init__.py
  - data/ (実行時に生成される想定）
    - kubusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)

（実際の細かいファイルはリポジトリの内容に依存します。上は主要なファイルを抜粋したものです。）

---

## 開発者向けメモ

- DuckDB 接続を受け取る研究関数群は副作用を持たない純粋関数として実装されています。テストがしやすい設計です。
- monitoring/monitoring_db.py はスキーママイグレーション（カラム追加）を起動時に冪等に実行します。
- AI 関連は外部 API に依存するため、ユニットテストでは _call_openai_api をモックする設計になっています（テスト用のフックを用意）。
- 設定の自動ロードはプロジェクトルート検出に基づくため、パッケージ化後も作業ディレクトリに依存せず動きます。

---

問題や追加してほしい項目があれば教えてください。必要であれば README に .env のサンプルテンプレートや起動例の systemd/pm2/cron 登録例なども追加できます。