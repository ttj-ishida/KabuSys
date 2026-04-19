KabuSys — 日本株自動売買システム
=================================

このリポジトリは、日本株の自動売買・研究・監視に関するモジュール群を含むプロジェクトです。
主要コンポーネントは Execution（発注エンジン）、Monitoring（監視・アラート）、Research（ファクター計算）、
Portfolio（銘柄選定・配分・株数決定）、AI（ニュース NLP / レジーム判定）、および各種ユーティリティです。

以下は簡易 README。起動・設定手順や各機能の概要、ディレクトリ構成を日本語でまとめます。

前提
----
- Python 3.10 以上（型注釈に | 演算子を多用しているため）
- 必要な主要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合に必要）
- SQLite は標準ライブラリで利用します。

インストール（例）
-----------------
仮想環境作成後に必要パッケージをインストールしてください（プロジェクトに requirements.txt が無い場合の例）:

    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai PyYAML

プロジェクト概要
--------------
KabuSys は以下の領域をカバーします。

- Execution（実行エンジン）
  - Broker クライアント経由で発注を行う ExecutionEngine と補助コンポーネント（OrderManager, OrderRepository, RiskManager, Reconciler 等）。
  - KABUSYS_ENV によって paper_trading（モックブローカー）と live（実発注）を切り替え可能。
  - paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に記録し、本番 DB と分離。

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine。
  - 監視結果は SQLite（デフォルト: data/monitoring.db）に永続化。
  - Kill Switch（条件に応じ data/kill.flag を書き込み Execution を停止）や stop フラグ（data/stop_requested.flag）での安全停止。
  - run_monitoring.py によるポーリング起動。MONITOR_POLL_INTERVAL 環境変数で間隔変更可（デフォルト 60 秒）。

- Research（リサーチ）
  - DuckDB 上でのファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ。
  - 汎用的に prices_daily / raw_financials テーブルを参照。

- Portfolio（ポートフォリオ構築）
  - 銘柄選定（スコア/ランク）、等分配・スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元株丸め、aggregate cap調整等）。

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を利用したニュースの銘柄別センチメント集約（ai_scores テーブルへ書込）。
  - マクロニュース + ETF（1321）MA200 を合成した日次の市場レジーム判定（market_regime テーブルへ書込）。
  - APIキーは OPENAI_API_KEY に設定。失敗時はフェイルセーフ（例: macro_sentiment=0.0）で継続。

- ユーティリティ
  - ログ設定（logs/<app>.log、日次ローテーション）
  - プロセス優先度 / CPU affinity 設定 utilities
  - .env ウィザード（config_setup.py） / 設定検証（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

主な機能一覧
--------------
- run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は mock broker を使用し DB を分離。
- run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定）。
- config_setup.py: .env を対話式に作成・更新するウィザード。
- validate_config.py: .env と config/*.yaml を事前検証（--strict オプションあり）。
- ai.news_nlp: ニュース記事を LLM でスコアリングし ai_scores に書き込む。
- ai.regime_detector: ETF + マクロニュースでレジーム判定を行い market_regime に書き込む。
- monitoring: MonitoringDB、RiskMonitor、KillSwitch、MonitoringEngine、SystemMonitor など。
- portfolio: 銘柄選定・重み計算・リスク制御・株数決定ロジック。
- research: ファクター計算、将来リターン計算、IC（Information Coefficient）など。
- tools/paper_verification_report.py: ペーパートレード DB から検証レポートを出力する CLI。

環境変数（主なもの）
-------------------
自動ロード:
- プロジェクトルートの .env と .env.local を自動読み込み（既存 OS 環境変数は保護）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 主要:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（paper_trading 時に利用、デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/...
- OPENAI_API_KEY: AI モジュール使用時必須
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

.env の作成
-----------
対話式ウィザードで .env を生成:

    python -m kabusys.config_setup

ウィザード完了後、設定検証:

    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict  # 警告も失敗扱い

起動手順（簡易）
----------------

1) 監視（Monitoring）を起動（推奨: 監視を先に起動してから Execution を起動）:

    python -m kabusys.run_monitoring

- MONITOR_POLL_INTERVAL を変更する例（30秒間隔）:

    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 監視は default で本番 sqlite_path を使用します（監視ログは本番 DB に保存されます）。

2) 実行エンジン（Execution）を起動:

    python -m kabusys.run_execution

- ペーパートレードで起動する例:

    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Execution 起動時に data/execution.pid を作成し、停止は stop フラグや kill.flag により行われます。

停止方法:
- 監視ループ / 実行ループの即時停止（開発用）:
  - プロジェクトルートの data/stop_requested.flag を作成すると、run_monitoring と run_execution のループが検知して終了します。
- システム的な Kill Switch:
  - Monitoring の KillSwitch は条件が満たされると data/kill.flag を書き込み、ExecutionEngine を停止させます。
  - Execution 起動時の設定 KILL_FLAG_CLEAR_ON_START により起動時に kill.flag をクリアするか制御できます（本番では 0 推奨）。

ログ
---
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（過去 30 日保持）。
- スクリプト起動時に setup_logging(app_name="execution" | "monitoring") が呼ばれ、コンソール出力（stdout）とファイル出力を統一して設定します。

データベース
-----------
- 監視 DB（SQLite）: デフォルト data/monitoring.db。init_monitoring_db() により必要なテーブルを冪等に作成・マイグレーションします。
- DuckDB: 分析用データベース（data/kabusys.duckdb がデフォルト）。research と AI モジュールで参照。
- ペーパートレード DB: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離して記録。

使い方（ツール）
----------------
- Paper Trading 検証レポート:

    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
    # または DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI のニューススコア・レジーム判定はそれぞれモジュール関数を呼び出して利用できます（スクリプト / スケジューラから daily 実行等を想定）。
  - 必要に応じ OPENAI_API_KEY を環境変数に設定してください。

ディレクトリ構成（概要）
-----------------------
以下は src/kabusys 以下の主要ファイル・ディレクトリ（抜粋）：

- kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・Settings クラス
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 構成検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor 起動スクリプト

  - execution/               # 発注エンジン関連（OrderManager 等、実装は別ファイル）
  - monitoring/
    - monitoring_db.py       # SQLite access layer（init / MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

設定・運用上の注意
-----------------
- 本番（KABUSYS_ENV=live）で実行する前に validate_config.py で全設定を確認してください。
- .env は絶対にソース管理にコミットしないでください。
- OpenAI の呼び出しは API コスト・レート制限の対象です。production での運用時は適切なリトライ・バックオフおよびバッチサイズ設定を確認してください（news_nlp と regime_detector に実装済）。
- Monitoring はプロセス優先度を上げ、system の健全性やデータ鮮度を監視して Kill Switch を発動する仕組みを備えています。kill.flag の自動クリアは本番環境で危険なのでデフォルトで無効にしてください。

開発向けヒント
---------------
- .env を作成したらまず:

    python -m kabusys.validate_config

- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）は research / ai が前提としているため、テスト用データを用意してください。
- 単体テストや CI を追加する場合、環境変数自動ロードを抑制するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用の環境を明示的に構築すると安定します。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期設定）
- ライセンス情報がリポジトリに存在する場合はそちらを参照してください（このサマリにはライセンス記述なし）。

最後に
------
この README はコードベースから主要な設計・運用情報をまとめたものです。実際の導入時は .env、config/*.yaml（存在する場合）を正しく設定し、validate_config の結果を確認してから本番稼働してください。必要であれば README をプロジェクト固有の運用手順（systemd ユニット、コンテナ化、バックアップ方針など）に沿って拡張してください。