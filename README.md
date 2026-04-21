# KabuSys

バージョン: 0.1.0

KabuSys は日本株自動売買システムのコアライブラリおよび運用用スクリプト群です。ポートフォリオ構築、ポジションサイズ計算、リスク制御、監視・アラート、Paper Trading 検証、LLM ベースのニュースセンチメント集計などの機能を含みます。

---

## プロジェクト概要

主な設計方針・特徴

- モジュール化された純粋関数群（ポートフォリオ構築・リスク調整・ポジションサイズ計算など）と運用スクリプト（ExecutionEngine／Monitoring）の組み合わせ。
- DuckDB を分析向け DB として利用、SQLite を監視/発注ログ用に利用。
- Paper Trading（仮想発注）を本番 DB と完全分離して運用可能。
- OpenAI（GPT 系）を用いたニュース NLP（センチメント）、およびレジーム判定の仕組みを提供（API キー必要）。
- 運用監視（SystemMonitor / TradeMonitor / RiskMonitor）、Kill Switch による停止制御、アラート送信の基盤を含む。
- 自動環境読み込み（`.env` / `.env.local`）と対話式の `.env` 作成ウィザード、設定検証ツールを提供。

---

## 機能一覧

- 実行スクリプト
  - run_execution: ExecutionEngine を起動（本番 / paper_trading 切替）
  - run_monitoring: SystemMonitor のポーリングループを起動
  - config_setup: `.env` 対話式ウィザード（初期設定）
  - validate_config: 環境設定・config/*.yaml の事前検証
  - tools.paper_verification_report: Paper Trading の検証レポート生成

- ポートフォリオ（純粋関数）
  - 候補選択: select_candidates
  - 重み計算: calc_equal_weights / calc_score_weights
  - ポジションサイズ算出: calc_position_sizes
  - セクター上限適用: apply_sector_cap
  - レジーム乗数: calc_regime_multiplier

- 研究（research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary

- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を集約してセンチメントスコアを ai_scores に書き込み
  - regime_detector.score_regime: ETF とマクロニュースを使った日次市場レジーム判定

- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - monitoring_db: SQLite テーブルの初期化・永続化 API
  - risk_monitor / kill_switch / monitoring_engine: 運用監視と Kill Switch ロジック

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで `X | None` を使用しているため）
- SQLite は標準ライブラリで利用可能
- システムにより追加パッケージが必要（以下参照）

推奨手順（ローカル環境）

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - インストール例（必須/推奨パッケージ）:
     - pip install duckdb psutil openai
     - PyYAML は設定検証（config/*.yaml の内容チェック）で任意: pip install pyyaml
   - プロジェクトに requirements.txt があればそれを使ってください:
     - pip install -r requirements.txt

4. 初期設定（.env）の作成
   - 対話式で作成:
     - python -m kabusys.config_setup
   - あるいは `.env` を手動で作成（下記の環境変数参照）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

補足
- 環境変数は自動で `.env` / `.env.local` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- Python パッケージやバージョンは用途により追加要件がある場合があります（OpenAI SDK のバージョンなど）。

---

## 環境変数（主要）

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（運用に影響）
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
  - run_execution は KABUSYS_ENV=paper_trading の場合、Paper Trading 用 DB に書き込み（本番 DB と分離）
- OPENAI_API_KEY: AI（news/regime）を使う際に必要

データベース / ログ / PID / フラグ
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイルパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1)

運用設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60 秒。無効値はデフォルトにフォールバック）
- PAPER_FILL_MODE: Paper Trading の挙動（instant / partial / never / reject）

注意
- Monitoring（run_monitoring）は KABUSYS_ENV に関係なく settings.sqlite_path（監視 DB）を使用します。
- Execution は paper_trading の場合 PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離します。

---

## 使い方（主要コマンド）

- 環境変数のセット例（UNIX 系）
  - export JQUANTS_REFRESH_TOKEN="..." ; export KABU_API_PASSWORD="..." ; export OPENAI_API_KEY="..."

- 対話式 .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 注意: 起動前に kill.flag（KILL_FLAG_PATH）が存在する場合はエンジンは起動しません

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更（秒）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB指定: --db PATH （デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

停止・運用
- プロセス停止（外部）:
  - 実行プロセスに対して SIGINT/Ctrl+C で停止（スレッド join を待つ）
- 停止フラグによる制御:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが終了します（停止用フラグ）
  - Kill Switch: システム監視の結果に応じて `KILL_FLAG_PATH` に kill.flag が書き込まれると ExecutionEngine 側で停止処理が走ります。`KILL_FLAG_CLEAR_ON_START` による自動クリア設定に注意。

ライブラリとしての利用例（Pythonから）
- ポートフォリオ計算
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
- AI スコアリング（DuckDB 接続が必要）
  - from kabusys.ai import score_news

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要なモジュール構成（src/kabusys 以下）です:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコア化
    - regime_detector.py     — 市場レジーム判定（ETF + マクロニュース）
    - __init__.py

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数算出・配分制御
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — （発注ログ監視 — 実装参照）
    - kill_switch.py         — kill.flag 書込みロジック
    - monitoring_engine.py   — 複数モニタを束ねるエンジン
    - alert_manager.py       — （アラート送信管理）
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
    - __init__.py

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / affinity 設定
    - __init__.py

- data/                      — デフォルトの DB / PID / フラグ置き場（手動作成される）
- logs/                      — デフォルトのログ保存先（setup_logging が作成）

（上記は抜粋です。リポジトリ内の完全なファイル構成は実際のツリーを参照してください。）

---

## 重要な運用注意点 / トラブルシューティング

- Python バージョン:
  - 本コードは Python 3.10+ を想定しています（`X | None` 型注釈等の利用）。

- DB の分離:
  - Monitoring（監視）は常に settings.sqlite_path を参照します。ExecutionEngine は paper_trading のときに PAPER_TRADING_SQLITE_PATH を使用して本番データと分離します。環境変数の設定に注意してください。

- ロギング:
  - setup_logging により stdout（コンソール）とファイル（logs/<app>.log、日次ローテーション）が設定されます。ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソール出力のみになります。

- OpenAI API:
  - news_nlp / regime_detector は OpenAI の API キー（OPENAI_API_KEY）を必要とします。API 呼び出しはリトライやフォールバックロジックを含みますが、未設定時は例外となる関数があります（明示的にチェックしています）。

- フラグファイルによる停止:
  - data/stop_requested.flag をプロセス外から作成することで監視ループ・実行ループを停止できます（実行スクリプトは定期的にこのファイルの存在をチェックします）。

---

## 付録: .env のサンプル（要編集）

以下は config_setup と整合する最低限のサンプルです。`.env` は絶対にバージョン管理に含めないでください（秘密情報を含みます）。

JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

---

この README は主要な使い方と注意点をまとめたものです。より詳細な実装や API の使い方は各モジュールの docstring を参照してください（例: kabusys/portfolio/*.py, kabusys/ai/*.py, kabusys/monitoring/*.py）。必要であれば利用シナリオ（デプロイ手順、systemd ユニット例、Dockerfile など）や詳細な運用手順も追加できます。