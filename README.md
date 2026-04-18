# KabuSys

日本株自動売買システムのサブパッケージ群（ライブラリ＋起動スクリプト群）のREADME。  
ここに含まれるのは主にロジック、監視、ペーパートレード検証、AIを用いたニュース評価、ポートフォリオ構築などのモジュールです。

## プロジェクト概要
KabuSys は日本株の自動売買システム用ライブラリ兼起動スクリプト群です。主な目的は以下の通りです。

- 売買ロジック（シグナル生成 → 銘柄選定 → ポジションサイズ決定）
- ExecutionEngine（発注・注文管理・リスク管理）
- 監視（System / Trade / Risk を定期チェック）と Kill Switch
- Paper Trading（モックブローカー）と検証レポート生成
- DuckDB を用いた研究（ファクター計算、特徴量解析）
- OpenAI を用いたニュースNLP（センチメント）と市場レジーム判定
- 共通ユーティリティ（ログ設定、プロセス優先度設定、設定読み込み）

バージョン: 0.1.0（src/kabusys/__init__.py）

## 主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading を切替）
  - run_monitoring.py: SystemMonitor のポーリングループを実行（監視ログの永続化）
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: 環境変数／config/*.yaml のチェック
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成（期間指定可）
- 監視
  - monitoring/monitoring_db.py: SQLite ベースの監視ログ保存層
  - monitoring/system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス有無監視
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py 等（リスク監視・Kill Switch）
  - monitoring/monitoring_engine.py: 各Monitorを束ねるポーリングエンジン
- Execution
  - execution/*: ブローカー抽象化、注文管理、リスク管理、実行エンジン（Engine）
  - BrokerClientFactory により実運用／Mock（paper_trading）を切替
- ポートフォリオ構築
  - portfolio/: 銘柄選定、重み計算、リスク調整、ポジションサイズ計算（純粋関数）
- 研究・分析
  - research/: DuckDB を用いたファクター算出（momentum/value/volatility）、将来リターン、IC 計算、統計要約
- AI
  - ai/news_nlp.py: raw_news から OpenAI で銘柄別センチメントを算出し ai_scores に書込む
  - ai/regime_detector.py: ETF 1321 の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定（console + 日次ローテートファイル）
  - utils/process_priority.py: psutil を使ったプロセス優先度 / CPU affinity 設定
- スクリプト的ユーティリティ
  - config_setup: .env の対話式作成
  - validate_config: 起動前チェック（必須 env の存在、パス・YAML の検証等）
  - tools/paper_verification_report: ペーパートレードの稼働率/成功率/レイテンシ評価

## セットアップ手順（簡易）
1. Python を用意
   - 推奨: Python 3.10 以上（型注釈等を使用）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合、最低限次を入れてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config で YAML 検証を行う場合）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. .env を準備
   - 対話式で作成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env を直接作成（.env.example を参考に）
   - 自動読み込み仕様:
     - 自動で .env をロード（プロジェクトルートが検出できる場合）
     - 優先順位: OS 環境変数 > .env.local > .env
     - 自動ロードを無効化するには:
       ```
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
       ```
5. DB 初期化・ディレクトリ
   - デフォルトファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログ: logs/ に日次ローテートファイルを出力（書き込み権限が必要）
6. 必須環境変数
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV の値: development / paper_trading / live

## 主要な環境変数（デフォルト）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の fill 動作（instant|partial|never|reject）

必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD

注意: .env の自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml があるディレクトリをルートと判断）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

## 使い方（起動方法・コマンド例）

- ExecutionEngine を起動（通常・paper_trading を auto 切替）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。
  - 実行中は data/execution.pid を利用します。停止には data/stop_requested.flag を作成するか、kill.flag を使う仕組み（監視側）を利用します。

- Monitoring を起動（ポーリングで SystemMonitor を定期実行）:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は production sqlite_path（Settings.sqlite_path）を使います（KABUSYS_ENV に依らず本番 path を参照）。

- 環境設定ウィザード（.env 作成）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証 CLI:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコアリング（プログラム的に呼ぶ例）
  ```py
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
  ```

- 市場レジーム判定（プログラム的に）
  ```py
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

- ライブラリ関数（研究・ポートフォリオ）
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary
  - kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier

## 特記事項・運用注意
- paper_trading モードは本番 DB と分離して設計されています。必ず KABUSYS_ENV を適切に設定してください。
- run_monitoring は停止フラグ（data/stop_requested.flag）でループを終了します。run_execution も stop flag をチェックします。
- Kill Switch はリスク条件（ドローダウンやポジション数超過）で data/kill.flag を書き、ExecutionEngine 側で検出して停止させる仕組みです。KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険です（自動クリアされる）。
- psutil でプロセス優先度を上げる処理があります。権限によっては失敗して警告が出ますが動作は継続します。
- ログは logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリ作成に失敗した場合はコンソールのみとなります。
- OpenAI 呼び出しを含む AI 機能は API 利用料が発生します。テスト・評価は十分注意して行ってください。
- DuckDB／SQLite のスキーマやマイグレーションはコード内である程度自己適応（column 追加等）する実装がありますが、本番移行時はバックアップを推奨します。

## ディレクトリ構成（主要ファイル抜粋）
プロジェクトルートの src/kabusys 以下の主要構成:

- kabusys/
  - __init__.py
  - config.py                 # 環境変数読み込み・Settings
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - monitoring_engine.py
    - risk_monitor.py
    - kill_switch.py
    - (その他: trade_monitor.py, alert_manager など)
  - execution/
    - (execution engine, broker factory, order_manager, risk_manager, reconciler, order_repository 等)
  - utils/
    - logging_setup.py
    - process_priority.py

データ・ログ等の配置（デフォルト）
- data/
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/
  - execution.log
  - monitoring.log
  - その他アプリケーションログ

## 開発時のヒント
- 設定のチェックを行う:
  ```
  python -m kabusys.validate_config
  ```
- .env を対話的に作る:
  ```
  python -m kabusys.config_setup
  ```
- ログ設定はすべての起動スクリプトで setup_logging を呼び出しています。ロギングの挙動を変えたい場合は環境変数 LOG_LEVEL / LOG_DIR を設定してください。
- AI 機能をテストする場合は OPENAI_API_KEY を設定。テスト時は API 呼び出しをモックすることを推奨します（内部で _call_openai_api を patch 可能）。

---

この README はコードベースの主要な使い方・構成をまとめたものです。詳細な設計方針・アルゴリズム（PortfolioConstruction.md 等）が別途ある想定ですので、必要に応じてそれらのドキュメントも参照してください。もし README に追加したい具体的なコマンド例や設定例（.env.example など）があれば教えてください。