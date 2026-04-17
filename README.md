KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量なシステム群です。本リポジトリには以下の主要コンポーネントが含まれます。

- Execution: ブローカーとの発注・注文管理・リコンシリエーション（ExecutionEngine / OrderManager 等）
- Monitoring: システム稼働・注文異常・リスク監視、アラート送信（LINE）や Streamlit ダッシュボード
- Research: DuckDB を用いたファクター計算・特徴量解析モジュール
- AI: OpenAI を用いたニュースのセンチメント解析・市場レジーム判定
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算（PortfolioConstruction に準拠）
- Tools: Paper Trading の検証レポート等ユーティリティスクリプト

主な機能
--------
- 実発注と Paper Trading の切り替え（KABUSYS_ENV）
  - paper_trading 環境では MockBroker を使用し、Paper 用の DB（data/paper_trading.db）に記録して本番 DB と分離
- ExecutionEngine：注文の発行、管理、リスク管理、Reconciler による自動復旧
- Monitoring：定期ポーリングによるシステム状態記録（CPU/Memory/Disk）、データ鮮度チェック、注文滞留/約定異常検出、リスク監視（ドローダウン・ポジション上限）
- AlertManager：LINE Messaging API による通知（クールダウン機構付き）
- KillSwitch：しきい値超過時にフラグファイルを書き込み ExecutionEngine を安全に停止
- Research：モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC 計算
- AI：OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）と市場レジーム推定（market_regime）
- Streamlit ダッシュボード：監視 DB（data/monitoring.db）からダッシュボード表示
- ツール：Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提 / 依存関係
--------------
推奨 Python バージョン: 3.10+（typing の新構文や最新ライブラリ互換性のため）

主要依存ライブラリ（代表例）
- duckdb
- psutil
- openai
- requests
- streamlit（ダッシュボード使用時）
- そのほか実行環境に依存するライブラリ（例: Broker クライアント実装）

インストール例（仮の requirements が存在しない場合の手動インストール）
- pip install duckdb psutil openai requests
- streamlit はダッシュボードを使う場合にインストール: pip install streamlit

セットアップ手順
--------------
1. リポジトリをクローンして Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt  （もし requirements.txt を用意している場合）
   - または上記の主要依存ライブラリを個別に pip install で導入

3. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き可）
   - 主要な環境変数（例）
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=... （アラート用）
     - LINE_USER_ID=... （アラート送信先）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60 （監視ポーリング間隔秒、デフォルト 60）
     - PAPER_FILL_MODE=instant | partial | never | reject

   - Settings モジュールは .env(.local) を自動ロードしますが、自動ロードを無効にする場合は:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリを作成
   - mkdir -p data

起動方法（主要コマンド）
---------------------
- Monitoring をデーモン的に動かす（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き可能（秒、デフォルト 60）
  - run_monitoring は Monitoring DB（settings.sqlite_path）を使用。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を参照します

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。停止は同フラグの作成で行えます

- Paper Trading 検証レポート（標準出力）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます（存在しない場合は MonitoringEngine を先に起動）

停止 / Kill / フラグファイル
------------------------
- ExecutionEngine 停止のために KillSwitch（data/kill.flag）を使用します。KillSwitch は監視ロジックが条件を満たすと kill.flag を書き込みます。手動で停止シグナルを出す場合は data/kill.flag を作成します（中身は理由テキスト）。
- run_execution / run_monitoring は data/stop_requested.flag を検知して安全に終了します（stop フラグを作成すると次のループで終了します）。
- kill.flag をクリアするにはファイルを削除してください（例: rm data/kill.flag）。KillSwitch クラスは clear() を提供します。

設定値（主なもの）
-----------------
- KABUSYS_ENV: development | paper_trading | live
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager による LINE 通知

ディレクトリ構成（主なファイルと役割）
----------------------------------
- src/kabusys/__init__.py
  - パッケージ初期化、バージョン定義

- src/kabusys/config.py
  - 環境変数・設定管理（.env 自動読み込み・Settings クラス）

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading は専用 DB を使用）

- src/kabusys/monitoring/
  - monitoring_db.py : SQLite テーブル初期化・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py  : CPU/メモリ/Disk/プロセスPID/データ鮮度監視
  - trade_monitor.py   : 注文滞留・約定異常価格検出
  - risk_monitor.py    : ドローダウン／ポジション上限監視
  - kill_switch.py     : kill.flag 書込みロジック
  - alert_manager.py   : LINE 通知ラッパー
  - monitoring_engine.py : 各モニタを束ねるエンジン
  - streamlit_dashboard.py : Streamlit ベースの監視ダッシュボード

- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py 等
  - 発注ロジック、注文状態管理、ブローカー抽象化、起動時リコンシリエーション

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 銘柄候補選定、重み付け、単位株丸め、セクター制限、レジーム乗数

- src/kabusys/research/
  - factor_research.py, feature_exploration.py
  - DuckDB を用いたファクター計算、将来リターン・IC 計算、統計サマリ

- src/kabusys/ai/
  - news_nlp.py         : ニュース記事を OpenAI で解析し ai_scores を作成
  - regime_detector.py  : ma200 とマクロニュースを合成した市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py : Paper Trading 検証レポート生成

- src/kabusys/utils/
  - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - デフォルトで使用される DB / PID / フラグファイル置き場（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）

運用上の注意
------------
- OpenAI を用いる機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）を要求します。API のエラーはリトライやフォールバック（0.0）で安全に扱う設計になっていますが、API 利用にはコストとレート制限があります。
- Monitoring は本番 sqlite_path を参照します（環境にかかわらず本番用監視DBを使用）。Execution は paper_trading 環境時に DB を分離します。
- process priority / cpu affinity の設定は OS の権限に依存します。設定に失敗した場合はログに WARN が出て処理は継続します。
- データの鮮度判定やファクター計算は DuckDB の prices_daily / raw_financials テーブルに依存します。事前にパイプラインでデータを投入してください。

貢献 / 開発
-----------
- テストやローカル開発では .env.example を基に .env を作成してください（config._require は必須環境変数の不足時にエラーを投げます）。
- モジュール単位での実行（python -m <module>）やユニットテストを推奨します。外部 API 呼び出し部分（OpenAI など）はモック可能な設計になっています（内部 _call_openai_api を patch する等）。

参考コマンドまとめ
------------------
- 実行エンジン起動:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 監視エンジン起動:
  - python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

最後に
------
本 README はコードベースの主要な使い方と構成をまとめたものです。細かな挙動や設計の補足はソース内の docstring / コメントを参照してください。必要であれば .env.example のテンプレートや requirements.txt、運用手順書の追加作成を支援します。