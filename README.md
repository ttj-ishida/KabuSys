# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
本リポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、発注（Execution）および稼働監視（Monitoring）を含む一連の機能を提供します。

主な設計方針：
- DuckDB を用いた時系列ファクター計算（研究用）
- SQLite を用いた監視・ログ永続化（monitoring）
- 本番 / ペーパートレードの明確な分離（環境変数 KABUSYS_ENV）
- OpenAI を用いたニュース NLP / レジーム判定（API キー任意）
- 起動スクリプトはシンプルな CLI 型（python -m kabusys.xxx）

---

## 機能一覧（ハイレベル）

- Execution（発注エンジン）
  - Broker クライアントの抽象化（本番 / Mock）
  - Order 管理、Risk 管理、Reconciler、ExecutionEngine 起動ループ
  - paper_trading モード時は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor：注文ログ・約定監視（滞留注文・異常約定等）
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringEngine：上記を束ねたポーリングループ。MONITOR_POLL_INTERVAL で間隔制御

- 研究（Research）
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC（Information Coefficient）、統計サマリ

- ポートフォリオ構築（Portfolio）
  - 候補選定、等配分 / スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数

- AI（OpenAI 統合）
  - news_nlp: ニュースを LLM でセンチメント化して ai_scores に保存（バッチ・リトライ・検証）
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジーム判定

- ツール
  - paper_verification_report: ペーパートレードログを集計して検証レポートを出力

- 設定支援
  - config_setup: 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config: .env / config/*.yaml の起動前チェック（python -m kabusys.validate_config）

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10+（型アノテーションの構文や union 型 `|` を使用）
- SQLite（標準ライブラリ）、その他パッケージは pip でインストール

推奨手順（例）:

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （もし requirements.txt があれば `pip install -r requirements.txt`）

4. .env を作成
   - python -m kabusys.config_setup
     - 対話式で J-Quants / kabuAPI / DB パス等を設定します
   - あるいは手動でプロジェクトルートの `.env` を編集

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があれば指摘に従い修正。`--strict` を付けると警告も失敗として扱います。

注意:
- 自動で .env を読み込む仕組みがあります（プロジェクトルートが発見できた場合）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要スクリプト）

- 環境切替
  - KABUSYS_ENV は次のいずれか: `development`, `paper_trading`, `live`
    - `paper_trading`：Mock ブローカーを使用し、DB を data/paper_trading.db に分離
    - `live`：本番。設定値は慎重に確認してください（validate_config の追加チェックあり）

- 起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - 起動時に data/execution.pid に PID を書きます（設定に応じて）
    - 起動前に `data/stop_requested.flag` が存在すると起動せず終了します
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用

- 起動（Monitoring）
  - python -m kabusys.run_monitoring
    - 監視ループを開始（デフォルト 60 秒間隔）
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、1 以上）
    - 監視は本番 sqlite_path（SQLITE_PATH）を使用（環境に関係なく本番 DB を参照）
    - ループを停止するにはプロジェクトルートの `data/stop_requested.flag` を作成

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- ライブラリ関数（研究やバッチ実行から利用）
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.ai.score_news (ニュースセンチメントのバッチ処理)
  - kabusys.ai.regime_detector.score_regime (レジーム判定)
  - kabusys.portfolio.*（候補選定・配分・ポジションサイズ算出）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定動作（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 使用時に必要）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、default 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH — pid / kill flag のパス（.env で上書き可能）

---

## フラグファイルによる制御（運用上の注意）

- data/stop_requested.flag
  - run_execution / run_monitoring のループを優雅に停止するための外部停止フラグ。
  - ファイルが存在するとループは終了します。

- data/kill.flag
  - KillSwitch（監視内）から ExecutionEngine 停止を要求するために書き込まれるファイル。
  - 一度書き込まれると Execution 側は検出して停止（安全のため .env の KILL_FLAG_CLEAR_ON_START を確認してください）。

---

## ロギング・ログファイル

- ログはデフォルトで stdout と日次ローテーションされるファイル（logs/<app_name>.log）に出力されます。
- setup_logging() でログディレクトリやログレベルを環境変数または引数で上書きできます。
- 日次ローテーション、30 日保持がデフォルト設定です。

---

## DB 初期化 / マイグレーション

- monitoring_db.init_monitoring_db(conn) が monitoring 用のテーブルを冪等的に作成し、既存 DB に対して必要なカラム追加（簡易マイグレーション）を行います。
- paper_trading モードは paper_trading 用 SQLite を使用して本番 DB と分離します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py               — 環境変数 / Settings 管理（自動 .env ロード）
- config_setup.py         — .env 対話ウィザード
- validate_config.py      — 設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py           — ニュース NLP（OpenAI）バッチ処理
  - regime_detector.py    — レジーム判定

- monitoring/
  - monitoring_db.py      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py     — システム状態 / データ鮮度監視
  - trade_monitor.py      — (注文監視 モジュール)
  - risk_monitor.py       — ドローダウン / ポジション上限監視
  - kill_switch.py        — kill.flag 書き込みロジック
  - monitoring_engine.py  — 各モニタの統合ループ
  - alert_manager.py      — (通知管理: LINE 等)

- execution/
  - execution_engine.py   — ExecutionEngine 本体
  - broker_factory.py     — BrokerClient 抽象化（Mock / 実装）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- research/
  - factor_research.py    — ファクター計算
  - feature_exploration.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

- utils/
  - logging_setup.py      — ログ設定ユーティリティ
  - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルを抜粋した一覧です）

---

## 開発 / テストのヒント

- 研究・集計系は DuckDB 接続を受け取って動作するため、テスト用の DuckDB ファイルを用意して関数単位で確認可能です。
- AI モジュールは OpenAI クライアント呼び出しを内部で行います。ユニットテスト時は `_call_openai_api` をモックして外部 API を叩かないようにしてください（コード内でテストしやすいように設計されています）。
- validate_config.py は起動前の問題検出に有用です。CI に組み込むことを推奨します。

---

## よくある運用上の注意

- 本番（KABUSYS_ENV=live）では kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0 を推奨。
- paper_trading は本番 DB と完全分離すること。環境変数 `PAPER_TRADING_SQLITE_PATH` を確認してください。
- OpenAI の利用は API コストが発生します。news_nlp / regime_detector を運用する場合はレート・コストにご注意ください。
- プロセス優先度設定（set_process_priority）は OS によって動作が異なります。権限不足で失敗することがあるためログを確認してください。

---

この README はコードベースの主要な使い方・設計意図の概要をまとめたものです。各モジュールの詳細な仕様やパラメータ調整は該当ファイルの docstring / コメントを参照してください。必要に応じて README を改善しますので、追加で欲しい情報（例: systemd ユニット例、運用手順、Docker 化手順など）があればお知らせください。