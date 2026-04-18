KabuSys — 日本株自動売買システム
================================

本ドキュメントは、このリポジトリ（src/kabusys 以下）の概要、主要機能、セットアップ方法、使い方、ディレクトリ構成をまとめた README です。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主な目的は以下です。

- データ蓄積・分析（DuckDB / prices_daily, raw_financials など）
- ファクター計算・特徴量探索（research モジュール）
- ポートフォリオ構築・ポジションサイジング（portfolio モジュール）
- 発注エンジン（ExecutionEngine）とペーパートレード分離
- システム監視・リスク監視・Kill Switch（monitoring モジュール）
- ニュース NLP によるセンチメント評価・レジーム判定（AI モジュール）
- 各種ユーティリティ（ロギング／プロセス優先度設定 等）

機能一覧
--------
主な機能群と役割：

- config / config_setup.py / validate_config.py
  - 環境変数管理、自動 .env ロード、対話式ウィザードで .env を生成
  - 起動前チェック（必須環境変数・ファイル・YAML 構文など）

- 実行スクリプト
  - run_execution.py: 発注エンジン（ExecutionEngine）を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading DB を利用（本番 DB と分離）。
  - run_monitoring.py: SystemMonitor のポーリングループを実行。監視ログは sqlite（monitoring DB）へ記録。

- monitoring
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db
  - システム資源・データ鮮度、発注ログやリスク（ドローダウン・ポジション上限）監視、Kill Switch の発動

- execution
  - ブローカーファクトリ、ExecutionEngine、OrderManager/Repository、RiskManager、Reconciler（発注ロジックの主要部は execution 配下）

- portfolio
  - 銘柄選定、等重・スコア重み付け、ポジション決定、セクター上限・レジーム補正（純粋関数群で副作用なし）

- research
  - ファクター計算（momentum / volatility / value）、将来リターン、IC 計算、統計サマリー

- ai
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（ai_scores への書き込み）
  - regime_detector: ETF + マクロニュースを合わせて市場レジーム判定・書き込み

- tools
  - paper_verification_report: ペーパートレード DB を元に検証レポートを標準出力に出力

- utils
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定

前提・依存関係
--------------
推奨環境：
- Python 3.10+（型ヒントの union 表記などを使用）
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合に任意）
（requirements.txt は本リポジトリに含まれていないため、必要に応じて上記をインストールしてください。）

セットアップ手順
----------------
1. リポジトリをクローン（または展開）
   - 任意の場所に展開し、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を確認します。

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロダクション利用に合わせて追加パッケージをインストールしてください）

4. .env の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
   - 対話式で J-Quants トークンや KABU_API_PASSWORD、KABUSYS_ENV などを設定して .env を生成します。
   - 生成後は .env を絶対にリポジトリにコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL として exit(1) になります。

主要環境変数（代表）
-------------------
Settings や config_setup で使われる主要な環境変数（抜粋）：

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 専用 DB、デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート通知）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）

使い方
------

1) ExecutionEngine（発注エンジン）起動
- 通常:
  - python -m kabusys.run_execution
- 動作：
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag（プロジェクトルート/data/stop_requested.flag）が存在すると起動せず終了します。
  - 実行中は pid ファイル（デフォルト data/execution.pid）を生成します。

2) Monitoring（監視ループ）起動
- python -m kabusys.run_monitoring
- 動作：
  - SystemMonitor を定期実行して system_status / trade_logs / risk_logs / dashboard などに記録します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 停止フラグ（data/stop_requested.flag）を検出するとループを終了します。
  - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path（SQLITE_PATH）を使用します。

3) .env 操作
- 環境変数の作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告で失敗扱いになります。

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルトの DB は 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
- レポートは稼働率、注文成功率、送信率、レイテンシ（P95）などを表示し、PASS/FAIL を判定します。

5) AI 機能
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と日付を渡してニューススコアを ai_scores テーブルへ書き込みます。OpenAI API キーが必要です。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - レジーム判定（bull/neutral/bear）を market_regime テーブルへ書き込みます。

運用上の注意
-------------
- Paper Trading と Live（本番）は DB を分離する設計です。KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使うため本番データと混ざりません。
- Kill Switch（data/kill.flag）は ExecutionEngine に停止信号を送るために使用します。KillSwitch は条件評価により書き込みを行います。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨します。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。logging_setup.setup_logging を各スクリプトが呼び出しています。
- OpenAI API を利用する機能は API エラーやレート制限を考慮してリトライやフェイルセーフを備えていますが、API キーと利用量に注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要な構成（抜粋）です。実装の詳細は各モジュールの docstring を参照してください。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - execution/                — 発注関連
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - risk_manager.py
    - reconciler.py
    ...

  - monitoring/               — 監視・Kill Switch
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    ...

  - portfolio/                — ポートフォリオ構築・サイズ計算
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/                 — ファクター・解析
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py

  - data/                     — （データファイルを配置する想定）
    - monitoring.db (SQLITE_PATH のデフォルト)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb (DuckDB のデフォルト)
    - kill.flag, stop_requested.flag, execution.pid など

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py

追加情報・開発メモ
-----------------
- モジュールの多くは副作用を避ける純粋関数で実装されており、単体テストが容易です（例: portfolio/*.py, research/*.py）。
- DuckDB を分析用のローカル DB として用いており、SQL と Python を組み合わせて高速処理します。
- AI（OpenAI）を利用する箇所は API 呼び出しをラップし、失敗時はフェイルセーフで進める設計です。
- ローカルでの検証・開発時は KABUSYS_ENV=development を使用し、paper_trading で動作確認を行ってから live に切り替えてください。

問い合わせ・貢献
----------------
バグ報告、改善提案、PR はリポジトリの Issue / Pull Request を通じてお願いします。ドキュメントやテストの追加も歓迎します。

以上。README に不足している項目や、特定のモジュール（例: ExecutionEngine の詳細な起動オプション、OrderRepository の API 仕様など）について追記希望があれば教えてください。