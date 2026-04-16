README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視ライブラリ群です。本コードベースは以下の主要機能を含みます。

- ExecutionEngine（発注・注文管理・リコンシリエーション）
- Monitoring（システム監視・注文監視・リスク監視・アラート）
- Portfolio construction（銘柄選定・配分・ポジションサイズ算出）
- Research（ファクター計算・特徴量探索）
- AI ユーティリティ（ニュースセンチメント評価、レジーム判定）
- Tools（Paper Trading 検証レポート、Streamlit ダッシュボード）

本リポジトリはライブラリと実行用スクリプトを含み、実運用（live）と Paper Trading（paper_trading）を環境変数で切り替えられる設計です。

主な機能
--------
- 発注フロー管理（OrderManager / OrderRepository / Reconciler）
- ExecutionEngine：ブローカーと連携して取引セッションを実行
- Monitoring：CPU/メモリ/ディスク/データ鮮度/プロセス死活の定期チェック
- Alerting：LINE Messaging API を使った一方向通知（クールダウンあり）
- Kill Switch：ドローダウンやポジション上限超過で Execution を停止するフラグ機能
- Portfolio Construction：候補選定、等配分/スコア配分、リスク調整、ポジションサイズ計算
- Research：DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）と IC 等の解析
- AI：OpenAI を利用したニュースのセンチメント評価（score_news）と市場レジーム判定（score_regime）
- Tools：Paper Trading 検証レポート生成、Streamlit ダッシュボード表示

前提（Prerequisites）
--------------------
- Python 3.10 以上（型ヒントに | ユニオンなどを使用しているため）
- 任意パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリ）
- ネットワーク接続（LINE / OpenAI API 利用時）

インストール例
--------------
プロジェクトルートで（仮想環境を推奨）:

pip install -U pip
pip install duckdb psutil requests openai streamlit

（将来的に requirements.txt があれば）
pip install -r requirements.txt

環境変数・設定
--------------
設定は環境変数またはプロジェクトルートの .env / .env.local から自動読み込みされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。Settings クラスで参照される主な環境変数:

- KABUSYS_ENV: execution モード。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定時は通知送信をスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行時に使用するファイルパス

データ / フラグファイル
- data/monitoring.db: 監視ログ（SQLite）
- data/paper_trading.db: Paper Trading 用 DB（環境が paper_trading の場合に使用）
- data/kabusys.duckdb: 価格等の時系列マスター（DuckDB）
- data/execution.pid: ExecutionEngine の PID（実行時生成）
- data/stop_requested.flag: run_monitoring/run_execution が監視する停止指示ファイル
- data/kill.flag: KillSwitch が書き込む停止トリガーファイル

セットアップ手順（簡易）
---------------------
1. リポジトリをクローンし作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. .env を作成して必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定
   - .env.example を参照して作成してください（リポジトリに例ファイルがある場合）
5. DuckDB / SQLite の初期データは各モジュールが起動時に必要なら作成・初期化されます

使い方（主要スクリプト）
-----------------------

注: ここではプロジェクトをパッケージとしてインストール済みか、プロジェクトルートで src を PYTHONPATH に含めていることを前提とします。
（例: export PYTHONPATH=$(pwd)/src）

1) 監視ループを起動
- 目的: システム状態や注文ログをポーリングして monitoring DB に記録、アラートや KillSwitch を発動
- 実行:
  python -m kabusys.run_monitoring
- オプション:
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- 停止:
  data/stop_requested.flag を作成するとループが停止します

2) ExecutionEngine を起動
- 目的: ブローカーとの発注処理を行うエンジンを起動
- 実行:
  python -m kabusys.run_execution
- 動作:
  KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離
- 停止:
  data/stop_requested.flag または kill.flag による停止を検知して安全に停止します

3) Streamlit 監視ダッシュボード
- 実行例（プロジェクトルートから）:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  監視 DB を読み取り専用で表示。MonitoringEngine を先に起動してデータを蓄積しておくこと。

4) Paper Trading 検証レポート
- 実行例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  --db で DB パス、--from / --to で期間フィルタを指定できます
- 出力:
  稼働率・注文成功率・送信率・レイテンシ等の要約と PASS/FAIL 判定

5) AI（ニューススコアリング / レジーム判定）
- ニューススコアリング（プログラムから呼び出し）:
  from kabusys.ai import score_news
  score_news(conn, target_date, api_key="...")
- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="...")

- 注意:
  OPENAI_API_KEY が未設定の場合は ValueError が発生します（関数の引数でキーを渡すことも可能）。API 呼び出しはリトライロジックを持ち、失敗時は安全側のフォールバックを行うよう設計されています。

運用上の注意
------------
- Paper Trading は production DB を汚さないように分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Settings は自動で .env/.env.local を読み込みます（プロジェクトルートは .git または pyproject.toml を基準に検出）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KillSwitch による停止は data/kill.flag を書き込むことで実行エンジンに停止命令を送ります。KillSwitch は drawdown またはポジション上限超過を検知した際に flag を書き込みます。
- process priority / CPU affinity 設定は utils/process_priority.py を通じて行われ、権限不足時は警告を出してスキップします。
- MonitoringDB のスキーマは init_monitoring_db により冪等で初期化されます。既存 DB に対する簡単なマイグレーションも含まれます（列追加等）。

ディレクトリ構成
----------------
以下は主要ファイルと役割の概観（src/kabusys 以下）:

- __init__.py
  - パッケージ定義

- config.py
  - 環境変数 / .env 読み込み、Settings クラス（アプリ設定）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔上書き可）

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 環境では MockBroker を使用）

- monitoring/
  - monitoring_db.py: SQLite 監視ログスキーマと MonitoringDB ラッパー
  - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度のチェック
  - trade_monitor.py: 注文滞留 / 約定価格異常の検出
  - risk_monitor.py: ドローダウン / ポジション上限の監視
  - kill_switch.py: kill.flag の生成/管理
  - alert_manager.py: LINE Push 通知クライアント（クールダウン管理）
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

- execution/
  - order_manager.py: 発注フロー管理（OrderManager）
  - reconciler.py: 起動時のリコンシリエーション・ポジション差分照合
  - order_repository.py, order_record.py, broker_api.py, など（発注 DB/API 関連）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - risk_adjustment.py: セクターキャップ・レジーム乗数
  - position_sizing.py: 株数算出・丸め・利用可能資金に合わせたスケーリング

- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー計算（DuckDB 使用）
  - feature_exploration.py: 将来リターン計算・IC・統計サマリ

- ai/
  - news_nlp.py: ニュース記事を OpenAI で評価し ai_scores テーブルへ書込む
  - regime_detector.py: ETF MA とマクロセンチメントを組み合わせて市場レジーム判定

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

ローカル開発のヒント
--------------------
- tests を書く際は .env 自動ロードを妨げたい場合 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとよいです。
- OpenAI への実際の HTTP 呼び出しはテストでモックすることが想定されています（各モジュールに API 呼び出しをラップする関数があり、patch 可能）。
- DuckDB は高速な分析向けに設計されており、research / ai の処理は DuckDB 接続を引数に取るため、テスト時にインメモリ・小データセットで検証可能です。

ライセンス / 貢献
-----------------
（ここにライセンスや貢献方法を記載してください。リポジトリに LICENSE がある場合は参照を追加）

問い合わせ
----------
バグ報告や仕様に関する問い合わせはリポジトリの Issues を使ってください。

--- 
以上。必要であれば README に追記するサンプル .env.example、docker / systemd ユニットファイルのテンプレート、より詳しい運用手順（バックアップ、DB リストア、ログ管理）なども作成できます。ご希望があれば教えてください。