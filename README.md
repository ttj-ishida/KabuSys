KabuSys — 日本株自動売買ライブラリ / 実行フレームワーク
=====================================================

概要
----
KabuSys は日本株向けの自動売買システム（ライブラリ + 実行コンポーネント）のコードベースです。  
主な役割は以下のとおりです。

- 発注エンジン（ExecutionEngine）による注文管理・発注・リスク管理
- 監視コンポーネント（Monitoring）によるプロセス・データ鮮度・リスク監視および Kill Switch
- ポートフォリオ構築（候補選定、重み計算、株数決定、セクター制約など）の純粋関数群
- リサーチモジュール（ファクター計算・特徴量探索）
- AI 支援（ニュースのセンチメント解析、マーケットレジーム判定） — OpenAI を利用
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

主な特徴
--------
- 実行環境分離:
  - KABUSYS_ENV により development / paper_trading / live を切り替え
  - paper_trading は paper 用 SQLite DB を用い、本番 DB と分離
- モジュール化:
  - 監視（system, trade, risk）やアラート、Kill Switch を独立実装
  - ポートフォリオ構築／サイズ計算は副作用のない純粋関数群
- DuckDB を用いたリサーチ（prices_daily / raw_financials 等に対する高速 SQL 処理）
- OpenAI（gpt-4o-mini）を使ったニュース NLP / マクロセンチメント（失敗時はフェイルセーフ）
- ロギングと日次ローテーション（logs/ 配下、TimedRotatingFileHandler）
- 運用用 CLI:
  - .env 設定ウィザード（config_setup）
  - 起動前設定チェック（validate_config）
  - 実行・監視スクリプト（run_execution, run_monitoring）
  - ペーパートレード検証レポート出力ツール

セットアップ手順
----------------
1. Python (推奨 3.10+) を用意してください。

2. 依存ライブラリをインストールします（requirements.txt があればそれを使用してください）。
   例（最小）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config/.yaml の検証に必要だが任意）

   pip の例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   （実際のプロジェクトでは requirements.txt / poetry / pipenv 等を利用してください）

3. プロジェクトルートに .env を作成します（.env.example を参照）。  
   対話式ウィザード:
   ```
   python -m kabusys.config_setup
   ```
   自動ロード:
   - デフォルトでプロジェクトルートの .env と .env.local を自動で読み込みます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   その他よく使う環境変数（抜粋）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 環境時に使用）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール実行に必須）
   - LOG_LEVEL / LOG_DIR
   - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか）

5. DB ディレクトリ（data/）やログディレクトリ（logs/）は通常自動作成されますが、権限に注意してください。

使い方（主なエントリポイント）
----------------------------

- 環境設定ウィザード（.env の作成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - 本番/開発/ペーパーは KABUSYS_ENV に依存
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading 環境では MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
  - 実行を外部から停止するには data/kill.flag を作成してください（KillSwitch により検出して停止）。

- 監視プロセス起動（SystemMonitor 単体のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60）。
  - 監視は monitoring DB（Settings.sqlite_path）を使用します（環境に関係なく本番 sqlite_path を参照する挙動）。

- Paper Trading 検証レポート（CSV ではなく標準出力テキスト）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。--db で指定可能。

- AI 関連（API キー必須）
  - ニュース NLP（ai.score_news）/ レジーム判定（ai.regime_detector.score_regime）はライブラリ API として呼び出せます。CLI ラッパーはありませんのでスクリプトから呼び出してください。
  - 例（簡易）:
    >>> from kabusys.ai.news_nlp import score_news
    >>> score_news(conn, target_date, api_key="sk-...")

運用メモ / フラグファイル
-----------------------
- 停止フラグ:
  - run_execution/run_monitoring はプロジェクトの data/stop_requested.flag を見て停止します（停止フラグが存在すると起動・継続を止めます）。
- Kill Switch:
  - RiskMonitor / KillSwitch により条件が満たされると data/kill.flag を書き込み、ExecutionEngine の停止を促します。
  - 起動時に kill.flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）がありますが、本番では 0 を推奨。

ロギング
--------
- 共通 setup_logging を使い、コンソール（stdout）とファイル（logs/<app_name>.log）に出力します。
- LOG_DIR / LOG_LEVEL 環境変数で制御可能。ログは日次ローテーション（30日保持）。

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 以下の主要なファイル／モジュールです（抜粋）。

- src/kabusys/
  - __init__.py (バージョン等)
  - config.py
    - Settings クラス：環境変数の集中管理、自動 .env ロード機構
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて挙動変更）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py
      - raw_news を OpenAI でスコアリングし ai_scores に書き込む
    - regime_detector.py
      - ETF（1321）MA とマクロニュースを組み合わせて日次レジーム判定
  - research/
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算（DuckDB SQL ベース）
    - feature_exploration.py
      - 将来リターン、IC 計算、統計サマリー
  - portfolio/
    - portfolio_builder.py
      - シグナル選定・重み付け（等金額・スコア加重）
    - position_sizing.py
      - 株数決定・aggregate cap・lot 単位の丸め
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py
      - SQLite を使った監視ログの永続化層（テーブル作成／マイグレーション含む）
    - system_monitor.py
      - システム状態・データ鮮度監視（psutil, DuckDB 利用）
    - trade_monitor.py (実装あり)
      - 発注ログチェック／滞留注文検出 等（コードベース内に存在）
    - risk_monitor.py
      - ドローダウン / ポジション上限監視
    - kill_switch.py
      - kill.flag の作成・管理
    - monitoring_engine.py
      - 複数モニタを束ねてポーリングするエンジン
  - execution/
    - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, risk_manager.py 等
      - 発注フロー / リスク管理 / 注文レポジトリ等（Execution のコア）
  - utils/
    - logging_setup.py
      - ルートロガー設定ユーティリティ
    - process_priority.py
      - プロセス優先度設定ラッパー（Windows / POSIX 対応）
  - data/ （実行時生成・デフォルトパス）
    - monitoring.db（SQLITE_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - kabusys.duckdb（DUCKDB_PATH）
    - kill.flag / stop_requested.flag / execution.pid などの運用ファイル

注意事項 / トラブルシューティング
--------------------------------
- OpenAI 関連:
  - AI モジュールを利用するには OPENAI_API_KEY（または API キー引数）が必須です。無い場合は ValueError を投げます。
  - API の 429 / ネットワーク切断 / 5xx は指数バックオフでリトライする設計です（ただし上限あり）。
- DB の初期化:
  - run_execution/run_monitoring は起動時に必要なテーブルの作成（マイグレーション）を行います（init_monitoring_db）。
- PyYAML が無い場合、validate_config の YAML 検証はスキップされ警告が出ます。
- ログディレクトリ作成に失敗した場合はコンソール出力（stdout）のみで継続します。
- process_priority の設定は OS によって動作が異なります。権限不足で警告が出る可能性があります。

開発者向けメモ
---------------
- 多くのモジュールは副作用がない純粋関数を心がけており、ユニットテストが書きやすくなっています（例: portfolio/*, research/*）。
- MonitoringEngine.run_once はテスト用に単発実行できるように設計されています。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。配布後に CWD に依存せず動作するよう配慮されています。

ライセンス / 貢献
----------------
- 本リポジトリにライセンスファイルがあればそれに従ってください。  
- バグ報告や改善提案は issue を立ててください。

最後に
------
この README はリポジトリ内のモジュール実装（config, execution, monitoring, ai, research, portfolio, utils 等）を元に作成しています。実行時の詳細な挙動や追加の CLI オプションはソースコード（各モジュールの docstring / ヘルプ）を参照してください。