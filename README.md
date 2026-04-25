# KabuSys

日本株自動売買システムのモジュール群（ライブラリ + 起動スクリプト群）の README。

本ドキュメントはコードベースをもとにした概要・セットアップ・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は、日本株向けの自動売買システム／リサーチ基盤です。主な機能は次の通りです。

- 注文実行エンジン（ExecutionEngine） — ブローカー抽象化、オーダー管理、リコンシリエーション、リスク管理を含む。
- 監視（Monitoring） — システム稼働監視、注文ログ監視、リスク監視、Kill Switch（停止フラグ）連携。
- ポートフォリオ構築（portfolio） — 候補選定、重み計算、ポジションサイズ決定、セクター上限適用、レジーム乗数。
- 研究（research） — ファクター計算、特徴量探索、IC/統計サマリー、将来リターン計算。
- AI 支援モジュール（ai） — ニュースのセンチメント（OpenAI）を使ったスコアリング、レジーム検出。
- ツール（tools） — ペーパートレード検証レポート生成など。
- 環境設定ヘルパー / 設定検証 CLI（config_setup / validate_config）。

設計上、DB（DuckDB / SQLite）と外部 API（kabuステーション / J-Quants / OpenAI）を組み合わせて動作します。多くのモジュールは「副作用の少ない純粋関数」または DB 抽象化層を介して実装されています。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード分離（KABUSYS_ENV による切替）
  - BrokerClientFactory によるブローカークライアント生成
  - RiskManager（利用率、ポジション上限、ドローダウン監視等）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・プロセス状態・データ鮮度を監視
  - TradeMonitor：注文滞留や約定異常の検出（trade_logs を参照）
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringDB：SQLite に監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）を格納
- Portfolio
  - 候補選定（select_candidates）
  - 等重・スコア重み計算（calc_equal_weights / calc_score_weights）
  - 単元丸め・リスクベース発注株数計算（calc_position_sizes）
  - セクターキャップ・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - news_nlp.score_news: raw_news を集約して OpenAI でセンチメントを算出、ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロセンチメントを合成して市場レジーム判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 環境変数 / config/*.yaml の起動前検証
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## セットアップ手順

以下はローカル開発・実行に必要な最低手順例です。

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（代表例）
   - pip install duckdb psutil openai PyYAML
   - openai / duckdb / psutil は本リポジトリ内の一部機能で必須です。環境に応じて追加で必要なパッケージがある場合があります。

3. プロジェクトルートの .env を作成
   - 対話式ウィザードの利用（推奨）:
     - python -m kabusys.config_setup
   - 手動で作る場合は `.env.example` を参照して必要な環境変数を設定してください。

4. 設定検証（任意・推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ等の準備
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/<app>.log
   - ログディレクトリや data ディレクトリは自動作成されますが、権限等で失敗する場合は手動で作成してください。

注意:
- .env は Git にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- 自動 .env ロードはデフォルトで有効。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 重要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、run_execution は MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と分離）。
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — デフォルト data/execution.pid
  - KILL_FLAG_PATH — デフォルト data/kill.flag
- ログ
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
  - LOG_DIR — ログディレクトリ（デフォルト logs/）
- 実行関連
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY — ai.news_nlp / ai.regime_detector で必要（なければ例外になる）

---

## 使い方（よく使うコマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading にすると paper_trading DB / MockBrokerClient を使用します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。停止は stop flag を書くかプロセスに SIGINT を送る等で行います。

- 監視プロセス起動（SystemMonitor ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に関係なく本番パスを参照）。
    - 停止は data/stop_requested.flag を作成することで行います。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。別ファイルを指定する場合は `--db PATH`。

- AI スコアリング / レジーム検出（ライブラリ関数として利用）
  - ai.news_nlp.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続（duckdb.connect(...) の接続オブジェクト）を受け取ります。

---

## 停止フラグ・Kill Switch

- 停止（run_execution / run_monitoring 等のループ停止）:
  - プロジェクト data フォルダ内の stop_requested.flag を作成するとポーリングループが検知して終了します（run_execution / run_monitoring で使用）。
- Kill Switch（自動停止）:
  - monitoring のロジックで条件が満たされた場合、KillSwitch が data/kill.flag に理由を記述して書き込みます。ExecutionEngine はこれを見て安全に停止できます。
  - Settings によって `KILL_FLAG_CLEAR_ON_START` を 1 に設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

---

## ログ設定

- ログは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を通して統一的に設定されます。
- 出力先:
  - コンソール（stdout）
  - 日次ローテートファイル: <LOG_DIR>/<app_name>.log（デフォルト logs/<app_name>.log、30 日分保持）
- LOG_DIR 環境変数や引数でディレクトリを変更できます。

---

## 注意事項 / 実装上のポイント

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を読み込みます。既存の OS 環境変数は保護されます。
  - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- DB の分離
  - ペーパートレード時は Execution は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用し、本番の monitoring DB と分離します。
  - Monitoring（run_monitoring）は環境にかかわらず Settings.sqlite_path（監視 DB）を使用します。
- OpenAI を使う機能
  - OpenAI API への呼び出しはリトライ・バックオフやレスポンス検証を行う設計です。APIキーがないとエラーになる関数があるため、AI 機能を使う際は `OPENAI_API_KEY` を設定してください。
- 互換性 / フェイルセーフ
  - 多くの箇所で外部依存（API / DB）の失敗時にフェイルセーフ（警告ログ・スキップ）を行う実装になっています。
- 依存ライブラリ
  - 少なくとも duckdb, psutil, openai（および PyYAML は設定検証で利用）をインストールしてください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル/モジュール構成は以下の通りです（src/kabusys 以下）。

- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — 環境変数 / Settings 管理、.env 自動ロード
- config_setup.py — 対話式 .env 作成ウィザード
- validate_config.py — 起動前設定検証 CLI
- __init__.py — パッケージ定義（__version__ 等）

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite 監視 DB の初期化・読み書きラッパ
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文ログ監視）※詳細実装ファイルあり
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - alert_manager.py — 通知管理（LINE 等）※存在

- execution/
  - execution_engine.py — ExecutionEngine（起動・セッション管理）
  - broker_factory.py — Broker クライアント生成
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行に関するコンポーネント

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター制限・レジーム乗数

- research/
  - factor_research.py — ファクター計算（momentum / value / volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- ai/
  - news_nlp.py — ニュースセンチメントの OpenAI 連携
  - regime_detector.py — マクロ + MA によるレジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

- data/ (ランタイム生成想定)
  - monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid など

- logs/ (ランタイム生成想定)
  - execution.log, monitoring.log, etc.

（上記はコードベースからの抜粋です。実際にはさらに細かいファイル群があります）

---

## 参考: よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- ペーパートレードレポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README はここまでです。必要なら以下も提供できます:
- サンプル .env（機密情報はマスクした例）
- より詳細な起動シーケンス図やログ・DB スキーマの説明
- 各モジュールの API 使用例（コードスニペット）