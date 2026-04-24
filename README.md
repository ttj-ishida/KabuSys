README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を収めた Python パッケージです。本リポジトリは以下の主要機能を提供します。

- 注文実行エンジン（ExecutionEngine）の起動・管理（本番 / ペーパートレード切替）
- システム監視ループ（SystemMonitor）と監視データ永続化（SQLite）
- リスク監視（ドローダウン・ポジション上限）と Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算・特徴量解析（DuckDB 上で動作）
- ニュース NLP / レジーム判定（OpenAI を使ったセンチメント集計）
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証、レポート生成）

本ドキュメントは開発者・運用者向けにセットアップ手順、起動方法、ディレクトリ構成などをまとめたものです。

主な機能一覧
-------------
- 実行（Execution）
  - BrokerClientFactory により実口座 / モック（paper_trading）を切り替え
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine を起動
  - ペーパートレード時は専用 SQLite を使用（デフォルト: data/paper_trading.db）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセスの存在を監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン・ポジション上限の監視
  - MonitoringEngine: 各 monitor を束ねて定期実行、アラート送出、Kill Switch 評価
  - 監視ログを SQLite に永続化（data/monitoring.db）
- ポートフォリオ（Portfolio）
  - 候補選択、等配分 / スコア加重配分、リスクベースの株数算出、セクターキャップ適用
- 研究（Research）
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- AI（News NLP / Regime Detector）
  - OpenAI を使ってニュースセンチメントを銘柄ごとにスコア化し ai_scores に書き込み
  - マクロニュース + ETF ma200 乖離で市場レジーム（bull/neutral/bear）を判定
- ツール
  - 設定ウィザード（config_setup）: 対話式に .env を生成
  - 設定検証（validate_config）: 起動前の環境チェック
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

必要条件
--------
- Python 3.10+
- 推奨（実行時に必要な外部パッケージの例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML チェックを行う場合）
- その他、使用するブローカークライアントに依存するパッケージがある場合があります。

セットアップ手順
---------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. パッケージをインストール（開発モード）
   - pip install -e .

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成（.env は Git にコミットしないこと）

5. 設定検証（起動前の確認）
   - python -m kabusys.validate_config
   - 本番相当の厳密チェックを行う場合:
     - python -m kabusys.validate_config --strict

環境変数（主なもの）
-------------------
設定は .env や環境変数から読み込まれます。代表的なキー:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading の場合はペーパートレード用モックを使用し DB を分離
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- OPENAI_API_KEY (news_nlp / regime_detector が必要時)
- MONITOR_POLL_INTERVAL (SystemMonitor のポーリング間隔秒、デフォルト 60)
- PAPER_FILL_MODE (paper_trading 時の成行・約定挙動: instant|partial|never|reject)

使い方（起動コマンド）
--------------------

- Execution Engine 起動
  - デフォルト（KABUSYS_ENV に従う）
    - python -m kabusys.run_execution
  - ペーパートレード起動例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行時、data/execution.pid に PID を書き、data/stop_requested.flag があれば起動しない／停止する挙動があります。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

停止 / フラグファイル
-------------------
- 停止要求（外部から Engine を停止したい場合）
  - data/stop_requested.flag を作成すると run_execution / run_monitoring が検知して終了します（両スクリプト内で監視）。
- Kill Switch（運用上の強制停止）
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に対する停止シグナルを送ります。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアします（本番では 0 推奨）。
- PID ファイル
  - 実行エンジンは data/execution.pid に PID を出力します。

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging によって統一管理されます。
- デフォルトでコンソール出力（stdout）と日次ローテーションのファイル出力（logs/<app_name>.log）を行います。
- LOG_DIR 環境変数で出力ディレクトリを変更可能です。

開発ノート / 注意点
-------------------
- .env は機密情報を含むため決してリポジトリにコミットしないでください。
- DuckDB は分析用途、SQLite は監視・トレードログ永続化で使い分けています（デフォルトファイルは data/ 以下）。
- AI を使う処理（news_nlp / regime_detector）は OpenAI API キーが必要です。API 呼び出しはリトライ・フェイルセーフの実装がありますが、キー未設定時は例外になります。
- config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env 自動読み込みを行います。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。

ディレクトリ構成
----------------
以下は主要ファイル／パッケージの構成（src/kabusys 以下）です。実際のプロジェクトルートでは src/ をパッケージルートとして想定しています。

- kabusys/
  - __init__.py (バージョン定義等)
  - config.py (環境変数 / 設定取得)
  - config_setup.py (対話式 .env 生成ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor 起動スクリプト)
  - execution/        (注文実行関連コンポーネント)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/       (監視関連)
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/        (ポートフォリオ構築)
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/         (ファクター計算・解析)
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/               (ニュース NLP / レジーム判定)
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/             (ランタイム生成・運用ファイルが置かれる想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパー時)
    - kabusys.duckdb (DuckDB 既定位置)
    - execution.pid
    - stop_requested.flag
    - kill.flag
  - logs/             (デフォルトのログ出力先)

よくある操作例
--------------
- 簡単な起動（開発用）
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

- ペーパートレードで検証
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 設定の検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

サポート / 拡張
----------------
- ブローカー実装や risk 設定、strategy の接続は execution パッケージを拡張してください。
- 研究用途のクエリは DuckDB のスキーマ（prices_daily / raw_financials 等）に依存します。実データ投入スクリプトは別途用意してください。
- AI 周りは OpenAI SDK のバージョン変更でインターフェースが変わる可能性があるため、テストで _call_openai_api をモックできる設計になっています。

免責
----
この README はコードベースのコメントおよび実装から要点をまとめたものです。実稼働環境で使用する前に、必ず設定検証と適切なテストを実施してください。

（必要であれば、起動時のログ出力例や .env.example のテンプレートを別ファイルとして追加できます。）