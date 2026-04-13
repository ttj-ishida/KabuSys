KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買および検証・監視ツール群です。本リポジトリは以下の主要機能を含みます。

- 実行（ExecutionEngine）: ブローカーへの注文生成・送信・リスク管理・再同期（リコンシリエーション）
- 監視（Monitoring）: システム状態・注文滞留・ドローダウン監視、Kill Switch（フラグファイルで実行停止）
- ポートフォリオ構築: 候補選定・重み算出・ポジションサイズ計算・セクター上限適用
- 研究（Research）: ファクター計算（モメンタム／ボラティリティ／バリュー）・特徴量解析（IC 等）
- AI 支援: ニュースセンチメント（OpenAI）によるスコアリング・市場レジーム判定
- ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード

特徴一覧
--------
- 環境分離: KABUSYS_ENV により development / paper_trading / live を切替。paper_trading は本番 DB と分離された専用 SQLite を使用。
- フェイルセーフ: API エラーや失敗は部分的にフォールバックして継続（LLM 呼び出し時など）。
- 冪等性を意識した DB 書き込み（monitoring DB 初期化・upsert ロジック等）。
- Kill Switch による安全停止（data/kill.flag を書き込み ExecutionEngine に停止指示）。
- Streamlit ダッシュボードで監視状態の可視化。
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP、マクロセンチメントによるレジーム判定。

セットアップ手順
----------------

前提
- Python 3.9+（コードの型や記法に合わせて適宜）
- SQLite（標準ライブラリで可）
- DuckDB（Python パッケージ）
- ネットワーク接続（LINE/ブローカー/OpenAI を利用する場合）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 依存パッケージはプロジェクトに requirements.txt があればそちらを使用してください。

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=<token>
     - KABU_API_PASSWORD=<password>
     - OPENAI_API_KEY=<key>         (AI 機能を使う場合必須)
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60   (run_monitoring のポーリング間隔秒)
     - LOG_LEVEL=INFO
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

   - サンプル .env（README 用）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     PAPER_FILL_MODE=instant
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

4. データディレクトリ
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。必要に応じてディレクトリを作成してください:
     - mkdir -p data

使い方
------

主要スクリプト・コマンド

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作:
    - Settings に基づき DB 接続、ブローカークライアント生成（paper_trading 時は MockBroker を利用して PAPER_TRADING_SQLITE_PATH に記録）
    - ExecutionEngine.run_session() を実行
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - 動作:
    - Monitoring の DB は KABUSYS_ENV に関わらず本番 sqlite_path を使用（ただし paper_trading 実行は専用 DB を使用する実行側の挙動に注意）
    - SystemMonitor.check_once() を呼び、MonitoringDB にログを追加

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（--db で上書き可）
  - 出力: 指定期間の稼働率、注文成功率、送信率、レイテンシ等を標準出力にレポート

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで監視情報（ポートフォリオ、ポジション、注文、システム状態、最近のリスクログ）を確認可能

AI 関連（OpenAI）
- ニュースセンチメントをスコア化して ai_scores に書き込む:
  - モジュール関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY または引数 api_key が必須
- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- リトライ・バックオフやレスポンス検証などが実装されているため、API キーとレート制限に注意してください。

監視と Kill Switch の挙動
- RiskMonitor により drawdown（ドローダウン）やポジション数上限が監視され、基準超過時に risk_logs に記録・アラート発行されます。
- KillSwitch は drawdown や position limit のトリガーが発生した場合に data/kill.flag を書き込み、ExecutionEngine 側はこのフラグを確認して安全に停止できます。
- run_monitoring/run_execution は起動時にプロセス優先度を high に設定するため、OS 権限や環境によっては警告が出力されます。

設定と挙動の注意点
- .env 自動読み込み: config.py はプロジェクトルート（.git または pyproject.toml がある場所）を探索して .env / .env.local を自動読み込みします。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV の有効値: development, paper_trading, live
- PAPER_FILL_MODE の有効値: instant, partial, never, reject（paper trading のモック挙動を制御）
- Paper Trading は本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用（デフォルト data/paper_trading.db）
- MonitoringDB は起動時にテーブルやマイグレーション（列追加）を自動で行います

ディレクトリ構成（主なファイルと役割）
---------------------------------
src/kabusys/
- __init__.py
  - パッケージ定義・バージョン情報

- config.py
  - 環境変数・設定読み込みロジック（.env 自動読み込み・Settings クラス）

- run_execution.py
  - ExecutionEngine 起動スクリプト（ブローカー・リスク管理・実行セッション）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - order_manager.py
    - Order State Machine の外部 API（作成・送信・同期）
  - reconciler.py
    - 起動時の自動リコンシリエーション（注文・ポジション照合）
  - その他（broker_factory 等）: ブローカークライアント生成、OrderRepository など（詳細はコード参照）

- monitoring/
  - monitoring_db.py
    - SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
    - CPU/メモリ/Disk/データ鮮度/実行プロセス監視
  - trade_monitor.py
    - 注文滞留・約定異常検出
  - risk_monitor.py
    - ドローダウン・ポジション数上限監視
  - kill_switch.py
    - kill.flag に基づく停止シグナル生成
  - alert_manager.py
    - LINE Push API を使った通知（クールダウン管理あり）
  - monitoring_engine.py
    - 各 Monitor を束ねてポーリングするエンジン
  - streamlit_dashboard.py
    - Streamlit を用いた監視ダッシュボード

- portfolio/
  - portfolio_builder.py
    - シグナルの候補選定・重み付け
  - position_sizing.py
    - 発注株数計算、リスクベース／等配分／スコア配分
  - risk_adjustment.py
    - セクター上限適用、レジーム乗数

- research/
  - factor_research.py
    - momentum / volatility / value 等のファクター計算（DuckDB 利用）
  - feature_exploration.py
    - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- ai/
  - news_nlp.py
    - ニュースを OpenAI に送って銘柄ごとにセンチメントを算出し ai_scores に書き込む
  - regime_detector.py
    - ETF MA 乖離 + マクロセンチメントを合成して market_regime を算出

- tools/
  - paper_verification_report.py
    - Paper Trading DB の検証レポート生成ツール（稼働率・成功率・レイテンシ等）

- utils/
  - process_priority.py
    - プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）

運用上のヒント
---------------
- 本番環境では KABUSYS_ENV=live とし、ログや DB のバックアップを確実に行ってください。
- OpenAI を用いる処理は API コストとレート制限に注意。事前に API キーと適切なバジェット管理を。
- kill.flag や PID ファイルの配置先は Settings で変更可能。複数インスタンス運用時は競合に注意してください。
- DuckDB 内の市場データ（prices_daily / raw_financials 等）を正しく整備することで research モジュールが正しく動作します。

ライセンス・貢献
----------------
- 本 README ではライセンス表記や貢献ガイドは含めていません。実プロジェクトにする場合は LICENSE と CONTRIBUTING を追加してください。

補足
----
この README はコードベースから主要な点を抜粋してまとめたものです。詳細な挙動や追加オプションは各モジュールの docstring やソースを参照してください。質問や追加説明が必要であれば教えてください。