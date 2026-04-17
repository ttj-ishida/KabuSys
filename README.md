KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を想定した小規模なフレームワークです。本リポジトリは以下を含みます。

- 発注エンジン起動スクリプト（ExecutionEngine）
- 監視ループ（System / Trade / Risk の監視）とアラート・Kill Switch
- ポートフォリオ構築・ポジションサイジングの純粋関数群
- リサーチ（ファクター計算・特徴量解析）
- ニュースの NLP スコアリング（OpenAI API を利用）
- ペーパートレード検証用レポート生成ツール
- 環境設定ウィザードと設定検証ツール

主な特徴
--------
- 環境変数 (.env/.env.local) から設定を自動読み込み（任意で無効化可能）
- Execution / Monitoring をプロセス優先度を上げて起動
- Paper Trading 環境では本番 DB と分離（data/paper_trading.db）
- 監視：CPU/メモリ/ディスク、プロセス生存、株価データ鮮度、滞留注文、約定異常、ドローダウン等
- Kill Switch：危険閾値を超えた場合に data/kill.flag を書き込み ExecutionEngine を停止
- AI モジュール（OpenAI）でニュースをスコアリングし ai_scores に保存
- DuckDB を用いたリサーチ/ファクター計算（prices_daily / raw_financials などを前提）

動作要件
--------
- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
- 任意（YAML 検証用）:
  - PyYAML

（インストール例）
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai requests PyYAML

セットアップ手順
----------------
1. リポジトリをクローンしてルートに移動
2. 仮想環境を作成・有効化し依存ライブラリをインストール
3. 初期の .env を作成
   - 対話型ウィザードを使う:
     python -m kabusys.config_setup
   - あるいは .env.example を参照して手動作成
4. 作成した .env を検証:
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いになります
5. 必要なデータディレクトリを作成（例: data/）
   mkdir -p data

重要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API のトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境:
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DB パス:
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパー取引用 SQLite（デフォルト: data/paper_trading.db）
- ログ・プロセス:
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - PID_FILE_PATH — ExecutionEngine の PID 保存先（デフォルト: data/execution.pid）
- 監視ループ:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- OpenAI:
  - OPENAI_API_KEY — news_nlp / regime_detector が利用（必要に応じて）

自動 .env 読み込み
------------------
プロジェクトルート（.git または pyproject.toml を検出）を基に、以下の順で環境変数を読み込みます（OS 環境変数が優先）:
- .env
- .env.local（.env を上書き）
自動ロードを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

実行方法（主なコマンド）
----------------------
- 環境設定ウィザード（.env 作成）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor をポーリング）:
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を秒単位で上書き可能
  - 監視ループ停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了

- ExecutionEngine 起動（発注エンジン）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録（data/paper_trading.db）
  - 起動中の停止は data/stop_requested.flag を作成すると Engine.stop() が呼ばれます

- ペーパートレード検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムから利用）:
  - ニュース NLP スコアリング:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

監視・Kill Switch の仕組み（簡易）
--------------------------------
- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、MonitoringDB（SQLite）にログを残します。
- RiskMonitor がドローダウンやポジション上限の異常を検知すると risk_logs を残し、KillSwitch が条件を満たせば data/kill.flag に停止理由を書き込みます。
- ExecutionEngine は起動時およびループ中に kill.flag の存在や stop_requested.flag をチェックして安全停止します。

注意（Paper Trading と本番の分離）
----------------------------------
- KABUSYS_ENV=paper_trading のとき、run_execution は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使います。本番監視（monitoring）は環境に関わらずデフォルトの sqlite_path（SQLITE_PATH）を使用する箇所がありますので運用時は設定を確認してください。

ディレクトリ構成（概要）
----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み・Settings
- config_setup.py          — .env 対話式生成ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

modules:
- execution/               — 発注 / エンジン関連 (OrderManager, BrokerFactory, Reconciler, RiskManager, ExecutionEngine 等)  ※詳細はコード参照
- monitoring/
  - monitoring_db.py       — SQLite テーブル定義・読み書きラッパ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py            — ニュースを OpenAI に投げてスコア化
  - regime_detector.py     — ma200 + マクロニュースでレジーム判定
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/ (上にある通り)
- その他（data/ 等は実行時に使用）

運用上の注意
------------
- .env は決して Git に含めないでください（config_setup の出力にも注意書きあり）。
- OpenAI API を利用する機能は API キー必須です。API コストとレート制限に注意してください。news_nlp / regime_detector はリトライやフェイルセーフを備えていますが、運用時はログを監視してください。
- psutil によるプロセス優先度設定や CPU affinity はプラットフォーム依存です。権限不足で設定できない場合は警告を出してスキップします。
- DuckDB / SQLite のパスや親ディレクトリの存在を validate_config で事前確認してください。

参考コマンドまとめ
------------------
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視開始: python -m kabusys.run_monitoring
- エンジン起動: python -m kabusys.run_execution
- ペーパーレポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

その他
-----
より詳しい実装の振る舞いや各モジュールの仕様はソース内の docstring / コメントを参照してください。必要であれば、特定モジュールの使い方や API 仕様ドキュメントを追加で作成できます。