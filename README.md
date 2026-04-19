README
=====

概要
----
KabuSys は日本株の自動売買および運用支援を目的とした小規模なフレームワークです。  
主な機能は以下です。

- 実行エンジン（ExecutionEngine）による発注／注文管理（本番 / ペーパートレード対応）
- 監視サブシステム（Monitoring）によるシステムヘルス、注文・リスク監視、Kill Switch
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ計算）
- リサーチ用ファクター計算（Momentum / Value / Volatility 等）
- AI 支援モジュール（ニュース NLP、レジーム判定） — OpenAI を用いたセンチメント評価
- ツール類（ペーパートレード検証レポートなど）
- 設定ウィザードと起動前検証 CLI

機能一覧
--------
主要な機能（モジュール単位）:

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により paper_trading と live を切替）
  - run_monitoring.py — SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で調整）
- 設定管理
  - config_setup.py — 対話式で .env を作成/更新
  - validate_config.py — .env と config/*.yaml の起動前チェック
  - config.py — 環境変数を読み込み・ラップする Settings クラス
- 監視
  - monitoring/monitoring_db.py — SQLite による監視データ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring/system_monitor.py — CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存監視
  - monitoring/trade_monitor.py —（注文の滞留や約定異常検出。参照のみ）
  - monitoring/risk_monitor.py — ドローダウン、ポジション上限監視・リスクログ出力
  - monitoring/kill_switch.py — kill.flag によるエンジン停止トリガー
  - monitoring/monitoring_engine.py — 各モニタの統合・アラート送出
- 実行・注文関連（execution パッケージ）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（発注・トラッキング・リスク）
  - paper_trading の場合は MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用
- ポートフォリオ（portfolio パッケージ）
  - portfolio_builder, position_sizing, risk_adjustment（候補選択・重み・株数計算・セクター制約）
- リサーチ（research パッケージ）
  - factor_research, feature_exploration（ファクター計算、将来リターン・IC 計算など）
- AI（ai パッケージ）
  - news_nlp.py — ニュース記事を集約して OpenAI へ送り銘柄ごとにセンチメントを取得、ai_scores テーブルへ書込み
  - regime_detector.py — ETF の MA とマクロ記事の LLM センチメントを合成して market_regime を判定
- ユーティリティ
  - utils/logging_setup.py — 統一ログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py — プロセス優先度の設定（Windows / POSIX を吸収）

セットアップ手順
----------------
1. リポジトリをクローンし、作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 基本的に以下をインストールしてください（requirements.txt がある場合はそちらを使用）
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証用、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 追加（AI を使う場合）:
     - OPENAI_API_KEY を環境変数に設定するか .env に記載

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. ディレクトリと DB
   - デフォルトでは data/、logs/ を使用します。必要に応じて .env のパスを変更してください。
   - 初回起動時に monitoring 用の SQLite および DuckDB ファイルは自動作成／マイグレーションされます。

基本的な使い方
--------------
- ExecutionEngine（実行エンジン）を起動
  - 本番/ペーパートレードは KABUSYS_ENV で切替:
    - export KABUSYS_ENV=paper_trading
    - export KABUSYS_ENV=live
  - 起動:
    - python -m kabusys.run_execution
  - ペーパートレード時は専用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）へ記録されます。

- Monitoring（監視）を起動
  - ポーリング間隔を環境変数で変更可能:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - 起動:
    - python -m kabusys.run_monitoring
  - 停止フラグ:
    - プロセスを優雅に停止するにはプロジェクトルートの data/stop_requested.flag を作成してください（起動処理はこのファイルを参照して終了します）。
  - Kill Switch:
    - 監視モジュールが条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱い

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH で DB 指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラム的使用）
  - OpenAI API キーを設定後、モジュール関数を呼ぶ:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます（logs ディレクトリを作成できない場合は stdout のみ）。
- 起動スクリプトはそれぞれ app_name を "execution" / "monitoring" として setup_logging を呼びます。

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（開発時のみ注意）

停止・強制停止
--------------
- 優雅な停止:
  - 作業ディレクトリに data/stop_requested.flag を作成 → run_monitoring / run_execution のループが検出して終了します。
- Kill Switch:
  - 監視が条件を満たすと data/kill.flag を作成して ExecutionEngine に停止を促します（.env の KILL_FLAG_CLEAR_ON_START=1 の設定があると起動時に自動クリアされるため、本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はパッケージ内部の主要ファイル構成（src/kabusys 配下）です。実際のツリーはリポジトリに依存します。

- src/kabusys/
  - __init__.py
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        (参照あり)
  - execution/
    - broker_factory.py       (参照あり)
    - execution_engine.py     (参照あり)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                    (runtime: DB/flag/pid ファイル etc.)
  - logs/                    (ログ出力先)

補足 / 注意事項
--------------
- 本リポジトリには DB スキーマ作成・マイグレーション処理が含まれており、起動時に必要テーブルが作成されます（monitoring_db.init_monitoring_db）。
- OpenAI 連携機能を利用するには API キーの設定が必須です。API 呼び出しは外部ネットワークを使用します。
- 本番環境での起動時は KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch をクリアしないため）。
- ペーパートレード（paper_trading）は本番データと分離された専用 SQLite を使用します。KABUSYS_ENV=paper_trading を設定してください。
- ロギングはアプリケーション全体で統一的に設定されます。ログ出力先やログレベルは .env の LOG_DIR / LOG_LEVEL で調整可能です。

ライセンスと貢献
----------------
- （ここにライセンス情報やコントリビュート方法を記載してください。プロジェクトに応じて追記してください。）

以上。README に載せるべき追加情報（例：実行時のシステム要件、サンプル .env、CI 設定等）があれば教えてください。必要に応じて追記・改善します。