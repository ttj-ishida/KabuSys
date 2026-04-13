KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量なPythonパッケージ群です。  
コードベースは次の主要機能に分かれており、ローカル SQLite / DuckDB をデータ永続化層として使用します。

主な特徴
--------
- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で注文を発行し、リスク管理・リコンシリエーションを行う。
- 監視（Monitoring）: システム状態、注文滞留、約定異常、ドローダウン等を定期ポーリングしてログ・アラート（LINE）出力を行う。
- ポートフォリオ構築: 候補選定、等重・スコア重み、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算の純粋関数群。
- リサーチ: DuckDB 上でファクター（モメンタム、バリュー、ボラティリティ）計算、将来リターン・IC 計算、統計要約。
- AI モジュール: OpenAI を用いたニュースセンチメント（ai_scores）と市場レジーム判定（market_regime）。
- 運用ツール: Paper Trading 検証レポート生成、Streamlit ベース監視ダッシュボードなど。

セットアップ
-----------
1. Python
   - Python 3.9+（プロジェクトは typing の近代機能を利用しています。お手元の環境に合わせてください）

2. 依存パッケージ（例）
   pip install duckdb psutil requests openai streamlit

   ※ 実行環境に合わせて requirements.txt を用意して運用してください。

3. 環境変数（.env）
   プロジェクトは .env / .env.local / OS 環境変数を読み込みます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数とデフォルト:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
   - KABU_API_PASSWORD: （必須）kabuステーション API 用パスワード
   - OPENAI_API_KEY: OpenAI 利用時に必要
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 監視アラート送信用
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の専用 DB）
   - PID_FILE_PATH: data/execution.pid（ExecutionEngine 用）
   - KILL_FLAG_PATH: data/kill.flag（ExecutionEngine 停止フラグ）
   - KILL_FLAG_CLEAR_ON_START: "1" にすると ExecutionEngine 起動時に kill.flag を削除
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の MockBroker 行動）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT：監視閾値（%）

   例 (.env):
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

初期データベース
- 監視用 SQLite（monitoring.db）は実行スクリプト内で init_monitoring_db() により必要なテーブルを冪等的に作成します。手動で初期化する必要は通常ありません。

使い方
------

1) 監視ループを起動
- 監視（SystemMonitor のポーリングループ）を単独で動かすスクリプト:

  python -m kabusys.run_monitoring

- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用します。

2) 実行エンジンを起動（注文発行）
- ExecutionEngine 起動スクリプト:

  python -m kabusys.run_execution

- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と完全分離されます。

- 起動時にプロセス優先度を "high" に設定しようとします（プラットフォームに依存、権限がない場合は警告でスキップ）。

- 起動時に kill.flag のクリーンアップを行いたい場合は環境変数 KILL_FLAG_CLEAR_ON_START=1 を設定して ExecutionEngine の起動ロジック（Settings.kill_flag_clear_on_start を参照）を活用してください（実際の ExecutionEngine 実装で参照されます）。

3) Paper Trading 検証レポート
- ツールスクリプトで paper_trading DB の集計／判定レポートを標準出力に出します。

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- 出力内容: 稼働率、注文成功率、送信率、P95 レイテンシ等。閾値を満たしているか PASS/FAIL を表示します。

4) Streamlit ダッシュボード（監視用）
- 監視 DB を読み取り専用で表示する Streamlit アプリ:

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ダッシュボードは positions / recent orders / latest system status / recent risk logs を表示します。

5) AI モジュール（ニュースセンチメント / レジーム判定）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行（OpenAI API キーは引数または環境変数 OPENAI_API_KEY）
  - LLM 呼び出しはバッチ化・リトライ・バリデーション済み

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の ma200 とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込み

注意:
- OpenAI を使用する機能は API キー必須です。API の失敗時はフェイルセーフ（多くは 0.0 にフォールバック）する実装になっていますが、API コスト/レート制限に注意してください。

プロセス優先度・CPU affinity
-------------------------
- 実行スクリプト起動時に set_process_priority("high") が呼ばれます（psutil を利用）。権限不足や未サポートOSでは警告が出てスキップします。
- set_cpu_affinity() も utils に実装されています。必要に応じて呼び出してプロセスの CPU ピニングが可能です。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py                 # パッケージ定義
    config.py                   # 環境変数／設定管理（Settings クラス）
    run_monitoring.py           # SystemMonitor ポーリング起動スクリプト
    run_execution.py            # ExecutionEngine 起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py
    monitoring/
      __init__.py
      monitoring_db.py          # SQLite 永続化層（init + MonitoringDB）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      ... (他に broker_factory, execution_engine, order_repository など)
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    data/
      ... (data パイプライン・統計ユーティリティ等。DuckDB 参照用)
    ai/
      news_nlp.py
      regime_detector.py
      __init__.py
    utils/
      process_priority.py
      __init__.py

開発・運用上の注意
-----------------
- DB マイグレーション: monitoring_db.init_monitoring_db() は既存 DB に対しカラム追加マイグレーション（例: peak_value, latency_ms）を行います。互換性を考慮していますが、運用時はバックアップを推奨します。
- Paper Trading: paper_trading モードは本番とデータを分離します。テスト／検証時はこちらを使用してください。
- Kill Switch: RiskMonitor 等が条件を満たすと kill.flag を書き込み、ExecutionEngine に対して停止を促します（KillSwitch による判定・ファイル書き込み）。冪等性が考慮されています。
- ログレベル: Settings.log_level を設定してログ出力を制御してください。

拡張ポイント
-------------
- ブローカープラグイン: BrokerClientFactory 経由で実装を差し替えられる設計です。外部ブローカーやモックを容易に組み込めます。
- ポートフォリオ構築やファクター群は純粋関数群として実装されており、ユニットテストしやすく、別の戦略に差し替え可能です。
- DuckDB ベースのデータ処理は高速で、研究用途に適しています。

問い合わせ／貢献
----------------
- 問題報告・機能要望は Issue を作成してください。コード変更は PR ベースでお願いします。
- 開発時は .env.example を参考に env を用意し、ローカルで paper_trading モードを使って検証するのが安全です。

以上。必要であれば README に含めるコマンド例や .env.example のテンプレート、よくあるトラブルシュート（OpenAI 関係、psutil の権限問題、SQLite のロック等）も追加で作成します。どの情報を追記しますか？