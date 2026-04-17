# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用ユーティリティ群。

このリポジトリはシグナル／ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、LLM を使ったニュースセンチメント評価などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを支える Python モジュール群です。主な責務は次のとおりです。

- 市場データ（DuckDB）を使ったファクター計算・研究機能
- 銘柄選定・配分・株数計算（ポートフォリオ構築）
- ExecutionEngine を中心とした発注フロー（本番 / ペーパートレード分離）
- 監視サブシステム（システム状態、注文滞留、リスク検出、Kill Switch）
- LLM を用いたニュースセンチメント評価・市場レジーム判定
- 環境設定ウィザード・設定検証・運用用レポート出力ツール

設計方針として、本番とペーパートレードは DB を分離し、ルックアヘッドバイアスを避けるため日付参照を直接使わない実装が多く採用されています。

---

## 主な機能一覧

- portfolio:
  - 銘柄候補選定（select_candidates）
  - 等金額 / スコア重み付け（calc_equal_weights, calc_score_weights）
  - 株数決定（calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- research:
  - Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算・IC 計算・統計サマリ（calc_forward_returns, calc_ic, factor_summary）
- execution:
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - 注文レポジトリ・オーダー管理・リコンシリエーション・リスク管理（RiskManager 等）
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor と統合する MonitoringEngine
  - SQLite ベースの監視ログ（monitoring_db.py）
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止
  - LINE 通知用 AlertManager（クールダウン付き）
  - run_monitoring.py によるポーリングデーモン起動
- ai:
  - ニュースセンチメント評価（news_nlp.score_news） — OpenAI を利用して ai_scores テーブルへ書き込み
  - 市場レジーム判定（regime_detector.score_regime） — ETF の MA と LLM による複合評価
- tools:
  - Paper Trading レポート生成（tools/paper_verification_report.py）
- 設定支援:
  - 対話式 .env ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）

---

## 必要な依存関係

（代表的なもの）
- Python 3.9+
- duckdb
- psutil
- openai
- requests
- PyYAML（config の YAML 検証を行いたい場合）

インストール例（仮）:
pip install duckdb psutil openai requests pyyaml

※ 実際のパッケージ名・バージョンはプロジェクトの packaging / requirements ファイルに従ってください。

---

## セットアップ手順

1. リポジトリをクローン / 取得
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上記の代表パッケージを個別にインストール）

4. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 重要: .env は絶対に Git にコミットしないでください（APIキー等が含まれます）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - monitoring 用 SQLite、DuckDB は初回アクセス時にスキーマ作成を行います（init_monitoring_db を参照）
   - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離されます

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードでの約定振る舞い（instant / partial / never / reject）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値 "1"）

補足:
- config.py はプロジェクトルート（.git または pyproject.toml）を探索し `.env`/.env.local を自動ロードします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

以下は代表的なコマンド例です。

- 環境ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作: KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、data/paper_trading.db に記録。本番では sqlite_path を使用。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - Execution は data/execution.pid を作成します（起動後は PID ファイルで実行を監視）。

- 監視デーモン起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用して監視ログを永続化します
  - 停止フラグ: プロジェクト/data/stop_requested.flag を作ると監視ループが終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH によりデフォルト DB を上書き可能

- AI (ニュース評価 / レジーム判定)
  - プログラムから関数を呼び出して利用します（例: kabusys.ai.news_nlp.score_news、kabusys.ai.regime_detector.score_regime）
  - 呼び出し時は OpenAI API キー（引数 or OPENAI_API_KEY 環境変数）が必要
  - LLM 呼び出しは冗長性（リトライ）・バリデーション・スコアクリップ等を行う安全なラッパー実装

---

## 運用上の注意

- .env は機密情報を含むため絶対にコミットしないこと。
- 本番環境（KABUSYS_ENV=live）では Kill Switch の設定や LINE 通知の設定を必ず確認してください。validate_config の live チェックが警告を出します。
- run_monitoring は監視用の sqlite DB（monitoring）に永続化します。Monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使う点に注意してください。
- run_execution は paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH を用います（本番 DB と完全分離）。
- プロセス優先度設定（set_process_priority）はプラットフォーム依存で権限が必要な場合があります。アクセス権限不足時は警告を出してスキップします。
- kill.flag / stop_requested.flag による停止フラグや PID ファイルの取り扱いに注意してください（誤って本番の Kill Switch をクリアしないこと）。
- OpenAI を使う機能は API 呼び出し料金が発生します。API キー管理とコスト管理を行ってください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み・設定ラッパ
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite の監視テーブル初期化・DB ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                — 発注エンジン関連（OrderManager, OrderRepository, Reconciler, RiskManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュースセンチメント評価（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

- data/                       — 実行時に利用するファイル（DB、PID、フラグ等）
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (ペーパートレード)
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 追加情報 / トラブルシューティング

- MONITOR_POLL_INTERVAL が不正な値（非正整数/0/負数）の場合、run_monitoring はデフォルトの 60 秒を使用します。
- config.py の自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト環境などで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 周りはネットワーク・API レートリミット等に備えてエクスポネンシャルバックオフとリトライ実装が入っています。失敗時は安全策としてスコア 0.0 やスキップなどのフェイルセーフ挙動を取る設計です。

---

この README はコードベースの主な機能と運用手順を簡潔にまとめたものです。より詳しいアーキテクチャや設計背景はプロジェクト内のドキュメント（Design / Markdown）やソースの docstring を参照してください。必要であれば、特定モジュールの使い方（例: ExecutionEngine の構成や portfolio のパラメータ説明）を追記しますのでお知らせください。