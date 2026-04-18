README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームの一部を切り出したコードベースです。  
主な目的は以下のとおりです。

- 日次のファクター計算（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 発注実行エンジン（execution） — 本番 / ペーパートレード対応
- 監視（monitoring）・リスク検知・Kill Switch
- ニュースに対する LLM ベースのセンチメント評価（ai）
- 運用補助ツール（config ウィザード・検証・レポート生成）

主要機能
--------
- execution
  - ExecutionEngine を起動して発注処理を実行（KABUSYS_ENV により本番/ペーパー切替）
  - BrokerClientFactory によるブローカークライアント抽象化
  - RiskManager / OrderManager / Reconciler による堅牢な実行フロー

- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウンなどを検出
  - MonitoringEngine: 各 Monitor をまとめてポーリング、KillSwitch 判定、AlertManager 連携（通知）
  - SQLite ベースの永続化（monitoring.db）

- portfolio
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（ロット調整・利用可能現金によるスケーリング）

- research
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC 計算、特徴量サマリ

- ai
  - ニュースの LLM（OpenAI）によるセンチメントスコア化（ai_scores への書込み）
  - 市場レジーム判定（ETF MA200 + マクロニュース LLM）

- tools
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト

セットアップ手順
----------------
前提:
- Python 3.10 以上（ソースで | 型注釈を使用）
- Git, SQLite（標準ライブラリで利用可能）
- DuckDB（Python パッケージ）
- OpenAI API（ai 機能を使う場合）
- psutil（プロセス優先度 / CPU affinity 用）

推奨パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config 検証で YAML 検査を行う場合）
インストール例:
    pip install duckdb psutil openai PyYAML

.env の準備:
1. プロジェクトルートに .env を用意（.env.example を参照できる場合はそれをコピー）
2. 対話式に作成する場合:
    python -m kabusys.config_setup
3. 作成後、設定を検証:
    python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

よく使う環境変数（抜粋）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う際に必要）
- LOG_LEVEL（例: INFO、DEBUG）
- MONITOR_POLL_INTERVAL（monitoring のポーリング間隔（秒） — デフォルト 60）

使い方
------
起動スクリプト（モジュールとして実行）:
- ExecutionEngine（発注エンジン）を起動:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    KABUSYS_ENV=live python -m kabusys.run_execution

  ペーパートレード時は MockBrokerClient が使用され、デフォルトで data/paper_trading.db に記録されます。

- Monitoring（監視ループ）を起動:
    MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring

  MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書きできます（デフォルト 60 秒）。
  監視は常に本番の sqlite_path を参照して監視ログを記録します（KABUSYS_ENV の影響を受けません）。

停止 / Kill スイッチ:
- run_execution/run_monitoring はプロジェクトの data/stop_requested.flag を監視します。
  このファイルがあると起動ループは終了します。
- KillSwitch（自動停止）は Settings.kill_flag_path（デフォルト data/kill.flag）にフラグを書き込み、
  実行中の ExecutionEngine に停止シグナルを送ります。

ツール:
- .env ウィザード:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションや環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能。

AI 機能:
- ニュースセンチメント（score_news）やレジーム判定（score_regime）は OpenAI API キーを必要とします。
  簡単な呼び出し例（Python から）:
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=<date_object>, api_key="sk-...")

ロギング:
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使い、
  コンソール（stdout）と日次ローテーションされるログファイル（logs/<app>.log）に出力します。
  ログディレクトリは環境変数 LOG_DIR またはデフォルト "logs"。

注意事項 / 運用上のポイント
-------------------------
- KABUSYS_ENV によって発注動作が変化します。live を指定すると実際に発注されるため注意してください。
- OPENAI_API_KEY が未設定だと ai 関連機能は動作しません（例外またはスキップ動作を行う実装箇所あり）。
- monitoring は常に「本番」監視 DB（settings.sqlite_path）を使用します。ペーパートレード DB は execution 側で切替えます。
- process_priority でプロセス優先度を上げようとしますが、権限や OS により設定できない場合があります（警告のみ）。
- DuckDB / SQLite のファイルパスの親ディレクトリが無い場合は起動時に自動作成されることがありますが、事前に作成しておくと安全です。
- .env は絶対にバージョン管理にコミットしないでください（README 内の config_setup でもその旨を注意喚起しています）。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理、自動 .env ロード
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

サブパッケージ / モジュール:
- ai/
  - news_nlp.py              — ニュース NLP（OpenAI）によるスコアリング
  - regime_detector.py       — マーケットレジーム判定（MA200 + マクロニュース）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - monitoring_db.py         — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py         — （コードベースに含まれる想定モジュール）
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py         — （実際の通知実装が存在する想定）
- execution/
  - execution_engine.py      — ExecutionEngine（エンジン本体）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（注）実際のリポジトリでは上記に加えて細かいモジュールや依存ファイルが存在します。ここでは主要な構成を抜粋しています。

ライセンス / 貢献
----------------
本ドキュメントはコードベースのヘッダ・コメントに基づいて作成されています。ライセンス情報や貢献ガイドラインはリポジトリのルートにある LICENSE / CONTRIBUTING ファイルを参照してください（存在する場合）。

補足（トラブルシュート）
----------------------
- PyYAML 未インストール時は validate_config の YAML 検査がスキップされます（警告が出ます）。config ファイルの静的検証が必要なら PyYAML を入れてください。
- OpenAI 呼び出しで 429 / タイムアウト / 一時的なエラーが発生した場合は内部で指数バックオフリトライが実装されていますが、API クォータや接続状況に注意してください。
- ログディレクトリの作成に失敗するとファイル出力は無効化され、コンソールのみの出力になります（stderr に警告）。

以上。README の追加要望（例: 具体的な設定例、requirements.txt、CI 設定など）があればお知らせください。