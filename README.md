# KabuSys

日本株向け自動売買システム（ライブラリ/実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注・監視・研究用ユーティリティを含む自動売買基盤の一部実装です。モジュールはなるべく副作用を避ける設計（純粋関数や DB 層を分離）になっており、実行スクリプトは環境変数で挙動を切り替えられます。

---
目次
- プロジェクト概要
- 主な機能一覧
- 必要要件
- セットアップ手順
- 環境変数（主要）
- 使い方（起動スクリプト・ツール）
- ディレクトリ構成
- 備考 / 運用上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群です。主に以下を提供します。

- 研究用ファクター計算（DuckDB 経由）
- ポートフォリオ構築・資金配分・ポジションサイジング（純粋関数）
- ExecutionEngine（ブローカークライアント経由の発注制御。ペーパートレードモードあり）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- AI を使ったニュースセンチメント評価（OpenAI）
- 各種 CLI（環境ウィザード、設定検証、ペーパートレード検証レポート生成）

設計上、本番用 DB とペーパートレード DB は分離されます（KABUSYS_ENV により切替）。

---

## 主な機能一覧

- Execution
  - 実際の取引（live）／ペーパートレード（paper_trading）切替
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - リスク管理（RiskManager）、OrderManager、Reconciler 等
- Monitoring
  - システム状態（CPU/メモリ/ディスク）、プロセス稼働監視
  - 注文ログ・滞留注文検出・約定異常検出
  - ドローダウン・ポジション上限監視と Kill Switch の発動
  - 監視結果を SQLite に永続化
- Research / Data
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - Forward returns / IC 計算 / 統計サマリー
- AI
  - OpenAI を使ったニュースセンチメント（銘柄別）集計・格納
  - 市場レジーム判定モジュール（ETF MA + マクロニュースの LLM 評価）
- Tools
  - 環境設定ウィザード（.env 作成）
  - 設定検証 CLI（環境変数や config/*.yaml の存在・パース検証）
  - Paper Trading 検証レポート生成

---

## 必要要件

- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (設定ファイル検証で利用される)
- SQLite（標準ライブラリ）
- さらに利用するブローカークライアントがあればその依存

（requirements.txt は付属していないので、必要に応じて pip インストールしてください。例: pip install duckdb psutil openai pyyaml）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. デフォルトのデータディレクトリ等は実行時に自動生成されます（logs/ や data/）。
5. .env を作成
   - 対話的ウィザード: python -m kabusys.config_setup
   - もしくは .env ファイルを手動作成（下記「環境変数」参照）
6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用に影響する主なもの（デフォルト値あり）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使い data/paper_trading.db に記録
  - live: 本番挙動（発注が行われる）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を利用する場合に必要
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject, デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch の flag ファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

.env の自動読み込み:
- プロジェクトルートに .env / .env.local がある場合、自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 使い方

ここでは主要な実行スクリプトとツールの使用例を示します。

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（実運用 / ペーパートレード）
  - python -m kabusys.run_execution
  - 挙動は KABUSYS_ENV に依存。paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用し、MockBrokerClient による記録となる。
  - 起動時、data/stop_requested.flag が存在すると起動をスキップします。実行中は data/stop_requested.flag や data/kill.flag で停止制御します。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視は常に「本番 SQLite（SQLITE_PATH）」を使用して監視データを永続化します（環境に依らず）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - プログラム的に使用する場合は kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出す
  - 例（スクリプト的に）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=os.environ["OPENAI_API_KEY"])

ログ:
- setup_logging により stdout と logs/<app_name>.log（日次ローテーション、30 日保持）に出力されます。
- log ディレクトリの作成に失敗した場合はコンソールのみで動作します。

停止制御:
- data/stop_requested.flag — run_execution / run_monitoring が検知して安全に終了します（運用ツール用）
- Kill Switch（data/kill.flag） — RiskMonitor の条件で書き込まれ、ExecutionEngine 側が存在検知して停止します

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイルとディレクトリ（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話的ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）集計ロジック
    - regime_detector.py     — 市場レジーム判定
  - research/
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       —（存在）取引の状態監視（抜粋では一部省略）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       —（アラート送信の抽象）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注ループ等）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/                    — 実行時に logs/ や data/ 下に DB / flag / pid 等が生成されます
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity ヘルパ

（上記はコードベースの主要ファイルのみ抜粋しています。詳細はソースツリーをご確認ください。）

---

## 備考 / 運用上の注意

- 本リポジトリは取引システムの一部実装です。live 環境での実行は重大なリスクを伴います。必ず設定検証（python -m kabusys.validate_config）を行い、KILL スイッチ / ログ / モニタリングを整備した上で運用してください。
- .env は絶対に Git に含めないでください（config_setup.py でも注意喚起あり）。
- OpenAI 等外部 API を利用する機能は API キーが必要であり、料金・レート制限に注意してください。API の失敗は多くの場所でフェイルセーフ（スコアを 0 にする、部分失敗を他データに影響させない等）になっていますが、運用前に十分に試験してください。
- run_execution / run_monitoring は PID / flag ファイルを使用して制御します。CI / デプロイ先のプロセス監視（systemd / supervisor / Docker 等）と組み合わせて運用することを推奨します。

---

不明点や README に追加してほしい具体的な情報（例: 実行ログ例、API クライアント設定、テスト手順など）があれば教えてください。必要に応じて追記・拡張します。