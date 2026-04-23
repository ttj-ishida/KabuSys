# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ + 実行用スクリプト群）。  
本ドキュメントはコードベースの主要コンポーネント、セットアップ方法、実行方法、およびディレクトリ構成をまとめた README です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト / CLI）
- 環境変数（主要）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買のためのコンポーネント群（シグナル / ポートフォリオ構築 / 発注エンジン / 監視 / 研究用ツール / AI ベースのニューススコアリング）を提供します。  
設計方針のポイント:
- 本番とペーパートレードは DB を分離（ペーパートレードは data/paper_trading.db）。
- モジュールは副作用を最小化した純粋関数・小さなクラスに分割。
- DuckDB を分析 / 研究用途、SQLite を監視・発注ログの永続化に使用。
- OpenAI（gpt-4o-mini）によるニュース NLP を用いたセンチメント評価 / レジーム判定機能を提供（APIキー必須）。

推奨 Python バージョン: 3.10+（型注釈に `|` を使用しているため）。

---

## 機能一覧

- 実行（Execution）
  - ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し data/paper_trading.db に記録
  - リスクマネージャ、オーダーマネージャ、再突合ロジックを内包

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine（監視ループ）
  - SQLite に監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）を永続化
  - Kill Switch（条件を満たしたら data/kill.flag を書き込み ExecutionEngine を停止誘導）
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL による間隔指定）

- ポートフォリオ構築（Portfolio）
  - 候補選定、等配分・スコア加重、リスク調整（セクターキャップ・レジーム乗数）
  - 発注株数算出（単元株丸め、リスクベース / 等配分 / スコア配分）

- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算 / IC（Information Coefficient）計算 / 統計サマリ

- AI（ニュース NLP / レジーム検出）
  - raw_news を LLM（OpenAI）に投げて銘柄別センチメントを算出し ai_scores テーブルへ保存（news_nlp.py）
  - ETF（1321）MA200乖離 + マクロニュースセンチメントを合成して日次の市場レジームを判定・保存（regime_detector.py）
  - API 呼び出しはリトライ・バックオフ、失敗時は安全側フォールバックを採用

- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity ユーティリティ（utils/process_priority.py）

---

## セットアップ手順

1. リポジトリをクローンしプロジェクトルートに移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 依存例（少なくとも以下が必要になります）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証を行う場合）
   - インストール例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt

4. Python パッケージとしてインストール（開発用）
   - プロジェクトが src レイアウトになっているため、以下のいずれかを実行してください:
     - pip install -e .  （setup.py / pyproject が用意されている場合）
     - または、PYTHONPATH を設定して実行:
       - export PYTHONPATH=src  （Windows: set PYTHONPATH=src）

5. .env（環境変数）を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルートに `.env`）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を環境変数にセット（news_nlp / regime_detector が必要とする）

6. 設定検証（任意・起動前推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

7. データディレクトリの準備（必要に応じて）
   - デフォルトでは data/ 配下に DB や PID/フラグファイルを作成します（実行時に自動作成される箇所あり）。

---

## 使い方（主要スクリプト / CLI）

実行時は、パッケージが import 可能な状態である必要があります（PYTHONPATH=src または pip install -e .）。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - 起動前に環境変数や config/*.yaml をチェックします。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モード: KABUSYS_ENV により挙動が変わります。
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 本番ブローカークライアントを使用（必須設定の確認に注意）
  - ストップ制御:
    - data/stop_requested.flag を検知すると起動中のエンジンを停止します。
    - 実行はデーモン的にスレッドで行われ、PID は data/execution.pid（デフォルト）に書かれます。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 監視間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は MonitoringDB（SQLite）へ常に production の sqlite_path を使って書き込みします（run_monitoring の仕様）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 簡易レポートを標準出力に出します。
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news を解析して ai_scores に書き込む（OpenAI API キー必須）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - レジーム判定を実行し market_regime テーブルに書き込む（OpenAI API キー必須）。

ログの出力設定は共通ユーティリティを通して行われ、デフォルトで stdout と logs/<app_name>.log（日次ローテーション）へ出力します。

---

## 環境変数（主要）

代表的な環境変数を列挙します（詳細は kabusys.config.Settings を参照）。

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用 / 動作
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。例: 60）

Kill Switch / 制御ファイル
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0/1。デフォルト 0)

その他
- PAPER_FILL_MODE: paper_trading 時の Mock の約定挙動（instant/partial/never/reject）

---

## ディレクトリ構成（抜粋）

（プロジェクトルートの src/kabusys をベースに抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル初期化 + CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                      — （ランタイムに作成される可能性がある）DB / flag / pid 等
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - その他

（上記は主要ファイルのみ。実際のツリーは追加ファイルやサンプル設定ファイル等が存在する可能性があります）

---

## 運用上の注意 / 補足

- 本番（KABUSYS_ENV=live）で起動する前に必ず `python -m kabusys.validate_config` で設定を検証してください。`--strict` モードで警告も許容しない設定確認ができます。
- OpenAI を利用する場合、API の利用料金・リクエスト回数に注意してください。news_nlp / regime_detector はバッチ化やリトライを行いますが、API 利用はコストが発生します。
- run_monitoring は「監視用 DB（SQLITE_PATH）」を使用して常に記録します（環境に依存せず本番の sqlite_path を使う実装になっています）。
- run_execution は KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離します。
- 停止制御:
  - data/stop_requested.flag: run_execution / run_monitoring がチェックする停止フラグ（手動で作成するとループ停止を促す）。
  - data/kill.flag: KillSwitch によって作成され、ExecutionEngine を完全停止させるためのフラグ（危険な条件で発行）。

---

必要に応じて本 README をベースに、環境固有のセットアップ手順（systemd サービスや Dockerfile、CI/CD 用の設定）を追加してください。README に補足してほしい点（例: Docker 化手順、systemd のユニットサンプル、詳しい環境変数一覧など）があれば教えてください。