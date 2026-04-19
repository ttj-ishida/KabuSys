# KabuSys

日本株向けの自動売買・研究プラットフォーム（モジュール群）です。  
このリポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、研究用ファクター計算、AI を使ったニューススコアリングなどの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提 / 必要要件
- セットアップ手順
- 使い方（主要コマンド例）
- 重要な環境変数
- 実行制御（Kill Switch / stop フラグ）
- ディレクトリ構成（主要ファイル解説）
- 備考

---

## プロジェクト概要

KabuSys は日本株自動売買のためのコンポーネント群です。主な役割は以下の通りです。

- 発注エンジン（ExecutionEngine）: 実際の取引またはペーパートレードを行う。
- 監視コンポーネント: システムの稼働状況、注文状況、リスク（ドローダウンや保有上限）を定期監視し、必要に応じて Kill Switch を発動。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定（単元丸め等）。
- 研究モジュール: DuckDB 上の時系列データを用いたファクター計算・解析（モメンタム、バリュー、ボラティリティ等）。
- AI モジュール: OpenAI を用いたニュースセンチメント（銘柄ごとの ai_score）と市場レジーム判定。
- 運用補助ツール: .env ウィザード、設定検証、ペーパートレード検証レポート生成など。

---

## 主な機能一覧

- 環境設定ウィザード（kabusys.config_setup）で .env の生成・更新
- 設定検証 CLI（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading では MockBroker と専用 SQLite を使用して本番 DB と分離
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- 監視用 DB 操作クラス（monitoring_db）と各種 Monitor（System / Trade / Risk）
- Kill Switch（monitoring.kill_switch）によりファイルベースで Execution を停止
- ポートフォリオ構築（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes）
- 研究（research.calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic 等）
- AI サービス（ai.news_nlp, ai.regime_detector）によるニューススコアリング・レジーム判定
- 運用レポート（tools.paper_verification_report）

---

## 前提 / 必要要件

- Python 3.10 以上（typing の | Union 表記や構文を使用）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML 検査を行う場合）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（OpenAI API や kabuAPI を利用する場合）

※ requirements.txt は含まれていないため、環境に応じて依存をインストールしてください。

---

## セットアップ手順（ローカル開発向け）

1. 仮想環境を作成・有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. pip の更新・依存インストール
   - pip install --upgrade pip
   - 代表的なパッケージ:
     - pip install duckdb psutil openai pyyaml

   必要に応じて追加パッケージをインストールしてください。

3. ディレクトリ作成（ログ・データ用）
   - mkdir -p data logs

   実行スクリプトは起動時に必要ファイル・ディレクトリの存在を仮定します。

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 必須項目（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV（development / paper_trading / live）
   - 生成後、.env をコミットしないでください（シークレット情報を含むため）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

---

## 使い方（主要コマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 通常（開発/default）:
    - python -m kabusys.run_execution
  - ペーパートレード（DB を分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  実行中、data/execution.pid に PID を書き、data/stop_requested.flag を作ることでプロセス停止を要求できます（詳しくは下記の実行制御節参照）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する例（30 秒）:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI/Research 関数
  - モジュール API を直接インポートして使用します（例: kabusys.ai.score_news, kabusys.research.calc_momentum）。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）, default: development
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI を使う機能（ai.news_nlp / ai.regime_detector）で使用
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、既定 60）

.env (生成されるファイル) は絶対に Git にコミットしないでください。

---

## 実行制御（Kill Switch / stop フラグ）

- stop_requested.flag
  - run_monitoring.py, run_execution.py は data/stop_requested.flag の存在を監視してプロセス停止処理を行います（運用上の強制停止などに使用）。
  - このファイルの場所はプロジェクトルート/data/stop_requested.flag（スクリプト内で設定）です。

- kill.flag（Kill Switch）
  - 監視ロジック（KillSwitch）により、リスク基準（ドローダウン閾値超過など）に達した場合に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされますが、本番では 0 を推奨します。

- PID ファイル
  - Execution 実行時に data/execution.pid が作成されます。

運用時はこれらのフラグ/ファイル作成・削除を利用して外部からプロセスを管理できます。

---

## ディレクトリ構成（主要ファイルの解説）

（ルート: src/kabusys 以下）

- __init__.py
  - パッケージ定義・バージョン

- config.py
  - 環境変数・設定管理。.env 自動読み込み機能、Settings クラスを提供。

- config_setup.py
  - 対話式 .env 生成ウィザード。

- validate_config.py
  - 起動前の設定検証ツール（必須環境変数、ファイル存在、YAML パース等をチェック）。

- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV によって本番/ペーパーを切り替え。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔指定可。

- monitoring/
  - monitoring_db.py — SQLite ベースの監視ログ永続化（テーブル作成・CRUD）。
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック等。
  - trade_monitor.py — （注文ログの監視: 滞留注文、約定異常等。※ソース参照）
  - risk_monitor.py — ドローダウン、ポジション数上限の監視。
  - kill_switch.py — 条件に基づく kill.flag 書き込み。
  - monitoring_engine.py — 監視各コンポーネントの纏め。

- execution/
  - 発注関連コンポーネント（BrokerFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など）
  - run_execution がこれらを組み立てて起動。

- portfolio/
  - portfolio_builder.py — 候補選定、等配分・スコア配分
  - position_sizing.py — 発注株数決定（単元丸め、リスク制約、aggregate cap）
  - risk_adjustment.py — セクターキャップ、レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - feature_exploration.py — 将来リターン計算、IC（スピアマン）など

- ai/
  - news_nlp.py — raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に書き込む
  - regime_detector.py — ma200 とマクロニュースの LLM スコアを合成して market_regime を算出

- tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成スクリプト

- utils/
  - logging_setup.py — 統一的なロギング設定（コンソール + 日次ローテートファイル）
  - process_priority.py — プラットフォーム差異を吸収するプロセス優先度設定（psutil 使用）

---

## 開発・運用上の注意

- .env ファイルは機密情報を含むため必ず .gitignore に追加し、リポジトリにコミットしないでください。
- OpenAI を使用する機能は API キーが必須です。API の利用制限・コストに注意してください。
- データベース（DuckDB / SQLite）は事前に適切なスキーマ・データを用意する必要があります（research, ai モジュールは特定テーブルを参照します）。
- run_monitoring は Monitoring 用の SQLite（SQLITE_PATH）を参照して永続化します。init_monitoring_db によりテーブルは自動作成されます。
- 実行中は logs/<app_name>.log にログが出力されます（デフォルト logs/、日次ローテーション・30日保持）。

---

必要があれば README を英語版にしたり、実際の requirements.txt、systemd ユニットファイル例、Dockerfile、サンプル .env.example を追加します。どの形式を優先しますか？