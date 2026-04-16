KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量な Python コードベースです。  
主な機能群は以下の通りです。

- 注文管理 / 発注エンジン（Execution）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リサーチ（ファクター計算・特徴量解析）
- AI を用いたニュースセンチメント（OpenAI）およびレジーム判定
- Paper Trading 用の分離された SQLite DB と検証レポート生成
- DuckDB を使った価格データ集計・特徴量計算
- Streamlit ベースの監視ダッシュボード

特徴
----
- 設定は .env（または環境変数）で管理。配布後もカレントディレクトリに依存しない設定読み込みロジックを採用。
- Execution と Monitoring は別プロセスで稼働する設計。監視は本番 DB（monitoring.db）を用いる（環境に依らない）。
- Paper Trading モードを持ち、本番 DB と完全分離して動作できる。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント & レジーム判定を内蔵。API 呼び出しのリトライやレスポンス検証を実装済み。
- 単体関数（純粋関数）で構成されたポートフォリオ構築ユーティリティ。テストしやすい設計。

セットアップ
----------
※ 以下はガイドです。プロジェクトの運用環境に合わせて適宜調整してください。

1. Python 環境（推奨: Python 3.10+）を用意する
   - virtualenv / venv を推奨

   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストールする（代表的な依存）
   - duckdb, psutil, requests, openai, streamlit

   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

   ※ プロジェクトに requirements.txt がある場合はそれを使用してください。

3. データディレクトリ作成
   ```
   mkdir -p data
   ```

4. 環境変数 / .env を作成
   - ルートに .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主なキー（必要に応じて設定してください）:

     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development | paper_trading | live
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO
     - MONITOR_POLL_INTERVAL=60  (監視ポーリング間隔 秒)

使い方
------

起動／停止の概念
- run_monitoring: SystemMonitor を定期実行して監視ログを SQLite に書き込む（デフォルト 60 秒）。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可。
  - 監視プロセスは data/stop_requested.flag が存在するとループを終了します。

- run_execution: ExecutionEngine を起動して発注処理を行う（スレッドで実行）。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading.db に記録され本番 DB と分離されます。
  - 停止は data/stop_requested.flag を作成するか、KillSwitch（監視側）から data/kill.flag が書き込まれることでトリガーします。
  - run_execution は起動時に data/execution.pid に PID を保存（PID ファイルの検査により stale 判定を行う処理が存在します）。

主なコマンド
- 監視プロセス起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を制御可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
  - 環境変数でモード切替:
    - 本番: export KABUSYS_ENV=live
    - Paper Trading: export KABUSYS_ENV=paper_trading

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを明示する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit 監視ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

プロセス停止 / フラグ管理
- 即時停止（手動ループ終了）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のポーリングループが検知して終了します。
    例: touch data/stop_requested.flag
- ExecutionEngine に対する安全停止（KillSwitch）:
  - 監視ロジックが DRAWDOWN や POSITION_LIMIT 等を検出した場合、kill.flag を書き込んで ExecutionEngine に停止信号を送ります（data/kill.flag）。
- フラグのクリア:
  - 起動時に kill.flag を削除したい場合は:
    ```
    rm -f data/kill.flag
    rm -f data/stop_requested.flag
    ```

主要モジュール要約
-----------------
- kabusys.config
  - Settings クラスで環境変数を集約。自動でプロジェクトルートの .env / .env.local を読み込み。
  - KABUSYS_ENV（development/paper_trading/live）、DB パス、LINE / OpenAI 等の設定を提供。

- kabusys.monitoring
  - monitoring_db: SQLite のテーブル作成 / 永続化ロジック（system_status, trade_logs, positions, risk_logs, dashboard）。
  - system_monitor: CPU/MEM/DISK、プロセス生存チェック、価格データ鮮度チェック。
  - trade_monitor: 滞留注文・約定異常を検出。
  - risk_monitor: ドローダウン・ポジション上限の評価と dashboard 更新。
  - kill_switch: kill.flag の書き込み / クリアロジック。
  - alert_manager: LINE Messaging API への通知（クールダウン機構あり）。
  - monitoring_engine: 上記モニタをまとめてポーリング実行。

- kabusys.execution
  - OrderManager, OrderRepository, Reconciler など発注・同期・復旧に関するコンポーネント（run_execution スクリプトから起動）。

- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment: 候補選定、重み付け、株数算出、セクター制限、レジーム乗数など純粋関数群。

- kabusys.research
  - factor_research: momentum/volatility/value ファクター計算（DuckDB を利用）。
  - feature_exploration: 将来リターン計算、IC（情報係数）など。

- kabusys.ai
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄ごとの ai_score を生成・ai_scores テーブルに書き込む。
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM 結果を組み合わせて market_regime テーブルへ書き込む。

ディレクトリ構成（主要部分）
----------------------------
src/
  kabusys/
    __init__.py
    config.py
    run_monitoring.py
    run_execution.py
    tools/
      __init__.py
      paper_verification_report.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    monitoring/
      __init__.py
      monitoring_db.py
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      ... (OrderRepository 等)
    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    utils/
      __init__.py
      process_priority.py
    data/         (運用時にプロジェクトルート直下に作成される想定)
      monitoring.db
      paper_trading.db
      kabusys.duckdb
      execution.pid
      stop_requested.flag
      kill.flag

追加メモ / 運用上の注意
---------------------
- Paper Trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring.db と明確に分離されます。
- OpenAI API の呼び出しはコストとレイテンシを伴います。API キー管理・レートに注意してください。score_news / score_regime はリトライロジックとフェイルセーフ（失敗時はスコア 0.0 など）を備えていますが、運用時は適切な監視を行ってください。
- process priority / cpu affinity を設定するユーティリティ（kabusys.utils.process_priority）を利用しています。権限不足で設定に失敗する場合は警告ログが出ますがプロセスは継続します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報・貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
---------
問題報告や改善提案は Issue を通じてお願いします。README に記載した動作や設定で不明点があれば具体的な実行例（環境変数・コマンド・ログ出力）を添えて問い合わせてください。