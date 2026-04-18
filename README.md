# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買／研究基盤のコアモジュール群を含みます。  
本 README はコードベースの主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成された自動売買システムです。

- 取引実行（ExecutionEngine）
- システム監視（Monitoring）
- リスク管理・Kill Switch
- ポートフォリオ構築（選定・重み付け・枚数決定）
- リサーチ（ファクター計算・特徴量解析）
- AI 支援（ニュース NLP によるセンチメント評価、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード／検証）
- ペーパートレード用の分離 DB / 検証ツール

設計上のポイント:
- 本番 / ペーパートレードは DB（SQLite）を分離して運用可能
- DuckDB を分析用 DB として利用（prices_daily / raw_financials 等）
- OpenAI を使った NLP 機能（API キー必須）
- ログは console + 日次ローテートファイル出力（logs/ ディレクトリ）
- .env（環境変数）ベースの設定管理と対話式ウィザードを提供

---

## 主な機能一覧

- run_execution.py: ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading.db に記録
  - PID ファイル / stop フラグにより起動・停止制御
- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - システムリソース監視、データ鮮度確認、監視ログの永続化
- monitoring/:
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / monitoring_db 等
  - Kill Switch（data/kill.flag）による緊急停止の発行
- portfolio/:
  - 銘柄選定（select_candidates）、重み付け（等重・スコア重み）、ポジションサイズ計算
  - セクター制限・レジーム乗数適用
- research/:
  - ファクター計算（momentum/value/volatility）、将来リターン計算、IC 計算、統計サマリー
  - DuckDB を用いた SQL ベースの処理
- ai/:
  - news_nlp: ニュース記事を LLM でセンチメント評価し ai_scores テーブルに書き込む
  - regime_detector: ETF (1321) の MA とマクロニュースで市場レジーム判定
- tools/:
  - paper_verification_report: ペーパートレード結果の検証レポート生成
- utils/:
  - logging_setup: 統一ログ設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定
- config_setup.py: .env の対話式生成ウィザード
- validate_config.py: .env と config/*.yaml の事前検証 CLI

---

## 動作に必要な依存パッケージ（代表例）

最低限必要なもの（pip でインストール）:

- python 3.9+（コードは型注釈に 3.10 以降の表記を含むが、3.9 以降で動作する想定）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config の YAML 検証を行いたい場合。必須ではない）

例:
pip install duckdb psutil openai PyYAML

（requirements.txt は本リポジトリに含まれていないため、プロジェクトで使用する環境に合わせて追加してください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo>
   - cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. 環境変数設定 (.env) の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
     - ウィザードに従って J-Quants トークン、Kabu API パスワード、DB パス等を入力
   - あるいは手動で .env を作成（.env.example を参照する想定）

5. 設定の検証（必須項目・ファイル構成チェック）
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告もエラー扱いになります

6. データディレクトリ（data/）やログディレクトリ（logs/）は自動作成されますが、権限やパスを確認してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- OPENAI_API_KEY（AI 機能用）: OpenAI API キー
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
  - paper_trading の場合、paper 用 sqlite（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch ファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject、デフォルト instant）

---

## 使い方（主要スクリプト例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / paper_trading に応じて .env の KABUSYS_ENV を設定）
  - python -m kabusys.run_execution
  - 起動中は data/execution.pid（デフォルト）が作成され、data/stop_requested.flag により停止できます

- SystemMonitor（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒単位のポーリング間隔を上書き可能

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（コード内 API 呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

- ログ設定は各起動スクリプトから kabusys.utils.logging_setup.setup_logging(app_name=...) を呼び出すことで統一管理されます。ログファイルは logs/<app_name>.log（デフォルト）に日次ローテートで保存されます。

---

## 運用時の注意点

- 本番（KABUSYS_ENV=live）では .env の内容と LINE 通知設定を十分に確認してください。validate_config は本番向けのガード（警告）を出します。
- Kill Switch（data/kill.flag）は ExecutionEngine に対する強力な停止手段です。KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します。
- ペーパートレードは本番データベースと分離されています（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。
- OpenAI API を使う機能は API キーとネットワークアクセスが必要です。API 呼び出しはリトライロジックを持ちフェイルセーフ（失敗時はスコア 0 等）になっていますが、コスト・レート制限に注意してください。
- DuckDB / SQLite ファイルは適切にバックアップ・ディスク容量の監視を行ってください。monitoring がディスク使用率を監視します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主な構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数設定読み込み / Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py            (監視用のトレードチェック)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            (アラート送信を担う想定モジュール)
  - execution/
    - execution_engine.py        (ExecutionEngine 本体)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - data/
    - (実行時に生成される: monitoring.db, paper_trading.db, kill.flag, execution.pid 等)

（上記はコードベースから抜粋した主要モジュール。細かいファイルはソースを参照してください）

---

## よくある操作例

- 監視ループを 30 秒間隔で動かす:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード環境で Execution を起動する:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証レポート（2026-04-01〜2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 参考・補足

- 設定値や動作は多くが環境変数で制御できます。まずは config_setup.py で .env を生成し、validate_config.py で検証する流れを推奨します。
- ログや DB の格納場所は .env で変更できます（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR など）。
- AI 機能を利用する場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライやスコアのクリップ処理が組み込まれています。

---

必要であれば README に含めるサンプル .env のテンプレート、起動スクリプトの systemd / supervisor 用のサンプル unit、あるいはモジュール別の詳細ドキュメント（API、関数仕様）も作成できます。どれを追加したいか教えてください。