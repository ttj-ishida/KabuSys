KabuSys — 日本株自動売買システム
=================================

※本 README は提供されたコードベース（src/kabusys 以下）を元に作成しています。実行環境やパッケージはプロジェクト固有の requirements.txt があればそちらを優先してください。

概要
----
KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な目的は以下です。

- シグナルに基づく発注処理（Execution Engine）
- 発注・約定状況やシステム状態の監視（Monitoring）
- ポートフォリオ構築・ポジションサイジング・リスク調整（Portfolio）
- ファクター計算やリサーチ用ユーティリティ（Research）
- ニュースベースの NLP スコアリング・市場レジーム判定（AI）
- 検証レポートやダッシュボードなどの運用補助ツール

主な機能
--------
- Execution
  - 起動時に BrokerClient を生成し発注セッションを実行（run_execution.py）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使い本番 DB と分離
  - Reconciler による起動時の注文状態整合（OrderSent などの自動復旧）
  - OrderManager / OrderRepository による注文状態管理

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID / データ鮮度の監視
  - TradeMonitor: 滞留注文（stale orders）や約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視と kill.flag による停止指示
  - AlertManager: LINE Messaging API による通知（クールダウン機能あり）
  - MonitoringEngine: 上記モニタをまとめてポーリング
  - SQLite ベースの監視ログ（monitoring_db.init_monitoring_db でスキーマ作成・マイグレーション対応）

- Research / Portfolio
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDBを使用）
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリ
  - portfolio: 候補選定、等配分／スコア加重配分、ポジションサイズ計算、セクター制限、レジーム乗数

- AI
  - news_nlp: raw_news を OpenAI (gpt-4o-mini) に投げて銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を作成

- 運用ツール
  - streamlit_dashboard.py: 監視データを表示するダッシュボード（Streamlit）
  - tools/paper_verification_report.py: Paper Trading DB から検証レポートを生成

セットアップ
----------
1. Python
   - 推奨: Python 3.9 以上（DuckDB / psutil / openai 等の組み合わせに応じて調整）

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （その他: sqlite3 は標準モジュール）
   - 実際はプロジェクトの requirements.txt を使用してください:
     pip install -r requirements.txt

3. プロジェクトルートの .env 自動読み込み
   - config モジュールはプロジェクトルート（.git または pyproject.toml）を探索し、
     .env, .env.local を自動で読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（Settings）
-------------------------
主な環境変数（Settings クラス参照）:

- KABUSYS_ENV: 起動環境。valid: development, paper_trading, live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定なら送信をスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を消すか（"1" で有効）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒、デフォルト 60）

使い方（主なエントリポイント）
----------------------------

- Execution Engine（発注プロセス起動）
  - 本番または paper_trading を切り替えて起動します。
  - 例（本番/デフォルト環境）:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - 例（Paper Trading、別 DB に書き込む）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動処理:
    - プロセス優先度を high に設定（psutil 経由）
    - SQLite / DuckDB を開き、BrokerClient を生成して ExecutionEngine.run_session() を実行
    - Paper Trading 時は settings.paper_sqlite_path を使用して本番 DB と分離

- Monitoring（ポーリング監視）
  - run_monitoring.py は SystemMonitor のポーリングループを起動します。
  - 例:
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を上書き可能（秒、最小 1 秒）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを書きます

- Streamlit ダッシュボード（監視 UI）
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視 SQLite（URI ?mode=ro）を開いて表示します

- Paper Trading 検証レポート
  - tools/paper_verification_report.py で Paper Trading DB（デフォルト data/paper_trading.db）からレポートを出力
  - 例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または代替 DB:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / リサーチ系（プログラム API として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、news_nlp が raw_news を集約して OpenAI に問い合わせ ai_scores を書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime に regime_score を格納
  - research モジュールには calc_momentum / calc_volatility / calc_value などが含まれ、DuckDB 接続と日付を渡してファクターを計算できます

モニタリング DB（スキーマ）
-------------------------
- init_monitoring_db(conn) を呼ぶと以下のテーブルを作成（冪等）
  - system_status (cpu, memory, disk, process_ok, recorded_at)
  - trade_logs (発注イベントログ、latency_ms カラムを含む)
  - positions
  - risk_logs
  - dashboard (id=1 の1行のみで集計を保持)
- 既存 DB に対する簡易マイグレーション（dashboard に peak_value がない場合の追加、trade_logs に latency_ms がない場合の追加）を行います

運用上の注意
------------
- PID / Kill flag
  - ExecutionEngine は settings.pid_file_path を書き、SystemMonitor はそれをチェックします。
  - KillSwitch は settings.kill_flag_path に理由テキストを書き、ExecutionEngine に安全停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に既存の kill.flag を削除します。

- プロセス優先度 / CPU affinity
  - 起動スクリプトは set_process_priority("high") を呼びます（psutil を使用）。権限不足や未サポート OS の場合は警告を出してスキップします。

- Paper Trading 分離
  - KABUSYS_ENV=paper_trading のときは settings.paper_sqlite_path にアクセスし、本番 monitoring DB と完全分離されます。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御します（instant, partial, never, reject）

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定読み込みロジック
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- order_manager.py
- order_repository.py
- execution_engine.py
- reconciler.py
- broker_factory.py
- broker_api.py
- ...（発注関連の実装）

src/kabusys/monitoring/
- monitoring_db.py                — SQLite 永続化層（init / CRUD）
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- alert_manager.py
- monitoring_engine.py
- streamlit_dashboard.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py                     — OpenAI を使ったニュースセンチメント
- regime_detector.py              — レジーム判定（MA200 + マクロセンチメント）
- __init__.py

src/kabusys/tools/
- paper_verification_report.py    — Paper Trading 検証レポート生成ツール
- __init__.py

src/kabusys/utils/
- process_priority.py             — psutil を用いた優先度 / affinity ユーティリティ

テスト / 開発向けヒント
-----------------------
- .env.example を参考に .env を作成して環境変数を設定してください
- 自動読み込みを一時的に抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DuckDB / SQLite の接続はそれぞれファイルパスを settings で切り替え可能（デフォルト: data/*.db）
- OpenAI API を使う機能をテストする場合は環境変数 OPENAI_API_KEY を設定してください
- 外部サービス（kabu API / Broker）をモックする実装が整っているので、paper_trading 機能でローカル検証可能です

最後に
-------
この README はコードに含まれるドキュメンテーション文字列と設定を元にまとめています。実際に運用する際は以下を確認してください。

- requirements.txt / poetry / pyproject.toml に記載の依存関係
- 実行環境（OS、権限）による psutil の挙動
- 本番運用時の監視・ログ保管ポリシー（ログローテーション・バックアップ）
- OpenAI 利用時のコストとレイテンシ考慮、および API キー管理

必要であれば、この README をベースに「デプロイ手順」「監視運用マニュアル」「テストガイド」などの追加ドキュメントも作成できます。どのドキュメントを優先するか教えてください。