KabuSys — 日本株自動売買システム
====================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリは下記の主要機能を含みます。

- 注文送信・管理（ExecutionEngine / OrderManager / Reconciler 等）
- モニタリング（システム状態、注文滞留、リスク監視、アラート送信）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI ツール群（ニュースセンチメントスコア / 市場レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な特徴
-------
- モジュール化された純粋関数（portfolio / research）と永続化層（SQLite / DuckDB）の分離
- Paper Trading（テスト環境）を本番 DB と完全に分離できる設計
- OpenAI を使ったニュース NLP による銘柄ごとのセンチメント評価・レジーム判定（任意）
- LINE への一方向通知（AlertManager）による運用アラート
- モニタリングループと KillSwitch による自動停止シグナル発行

前提 / 必須ソフトウェア
-----------------
- Python 3.10+（typing の | 記法や新しい型ヒントを使用）
- SQLite（標準ライブラリで利用）
- 主要外部パッケージ（概ね次をインストールしてください）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
（requirements.txt は本コードには含まれていませんが、上記パッケージ群が必要になります）

環境変数（主なもの）
-------------------
- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
  - paper_trading のとき、ExecutionEngine は MockBrokerClient を使用し、paper 用 SQLite に書き込む
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）デフォルト "instant"
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB データパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH: 各種フラグ/ファイルパス（デフォルトは data/ 配下）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

セットアップ手順（ローカル）
-------------------------
1. リポジトリを取得
   - git clone ... && cd repo

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じてバージョン固定や追加パッケージをインストールしてください）

4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くことで自動読み込みされます。
   - 例（.env）:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  （AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...

5. data ディレクトリを作成（必要に応じて）
   - mkdir -p data

起動方法 / 使い方
-----------------

基本的なスクリプト起動
- 監視ループ（SystemMonitor）を起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
  - 実行:
    - python -m kabusys.run_monitoring

  注意:
  - run_monitoring は Monitoring 用の SQLite（Settings.sqlite_path）を環境にかかわらず本番 sqlite_path を使う設計になっています。

- ExecutionEngine（注文実行エンジン）を起動:
  - paper_trading モード（KABUSYS_ENV=paper_trading）のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込みます（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution

停止・フラグ
- graceful stop: run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を監視しており、ファイルが存在するとループを終了します。
  - 停止を要求するには: touch data/stop_requested.flag（Windows では空ファイルを作成）
- KillSwitch による停止（自動トリガ）:
  - KillSwitch は条件に応じて data/kill.flag を書き込みます（ExecutionEngine 停止シグナル）。kill.flag が書かれると運用側はそれを確認して適宜処理を行います。

運用ツール
- Streamlit ダッシュボード（監視 UI）:
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB にアクセスします（読み取り URI を使って開く）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間フィルタ:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db data/paper_trading.db （または環境変数 PAPER_TRADING_SQLITE_PATH）

- AI 系（ニュースセンチメント / レジーム判定）
  - score_news: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
  - score_regime: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - どちらも OPENAI_API_KEY が必要（引数で渡すか環境変数で設定）。
  - これらは DuckDB 接続を受け取り DB の raw_news / prices_daily 等のテーブルを参照して結果を書き込みます。

ライブラリの利用例（簡易）
- DuckDB 接続を作ってニューススコアを付ける例（Python REPL 等）:
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, datetime.date(2026, 4, 10), api_key="sk-...")

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- monitoring/
  - monitoring_db.py — SQLite を用いた監視ログ永続化層（テーブル作成・読み書き）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス存在チェック
  - trade_monitor.py — 注文滞留 / 約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理と発行ロジック
  - alert_manager.py — LINE への通知
  - monitoring_engine.py — 複数モニタをまとめて定期実行するエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py — 注文作成・状態遷移の外向け API
  - reconciler.py — 起動時の自動リコンシリエーション（ブローカーと照合）
  - （その他: broker_factory 等、ブローカー抽象）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算（単元丸め、リスク制限、aggregate cap）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー算出
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py — raw_news を LLM で評価して ai_scores に保存
  - regime_detector.py — マクロ + MA200 から市場レジームを判定して保存
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity セットユーティリティ

重要なファイル/フラグ（デフォルトパス）
------------------------------------
- data/monitoring.db         — 監視ログ SQLite（Settings.sqlite_path デフォルト）
- data/paper_trading.db      — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb        — DuckDB（Prices / Financials / raw_news 等）
- data/execution.pid         — ExecutionEngine の PID（Settings.pid_file_path デフォルト）
- data/kill.flag             — KillSwitch が書き込む停止フラグ（Settings.kill_flag_path）
- data/stop_requested.flag   — 起動スクリプト（run_*）が参照する停止フラグ

運用上の注意
------------
- Paper Trading と本番 DB は意図的に分離される設計ですが、環境設定ミスは重大な事故につながります。環境変数（特に SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / KABU_API_PASSWORD）を起動前に必ず確認してください。
- OpenAI や外部 API を使う処理はネットワークエラーやレート制限に備えてリトライやフェイルセーフが実装されていますが、運用監視（AlertManager）を有効にしておくことを推奨します。
- process priority / cpu affinity の設定は OS により権限や挙動が異なります。set_process_priority は失敗時に警告を出してスキップします。

貢献・拡張ポイント（参考）
-------------------------
- stocks マスタや銘柄別 lot_size の導入（position_sizing の拡張）
- paper_trading の約定ロジックの高度化（fill モデルの拡張）
- Streamlit ダッシュボードのグラフ化・長期履歴表示
- テストカバレッジの拡充（特に AI 呼び出し部はモックでの単体テスト推奨）

ライセンス / 著作権
------------------
本 README にはライセンス情報を記載していません。実際の配布時は LICENSE ファイルをプロジェクトルートに追加してください。

終わりに
--------
この README はコードベースから抽出した実行方法・構成説明です。実運用前に .env の内容やデータベースのバックアップ・アクセス権限、テストを十分に行ってください。必要であれば、各モジュールの詳細なドキュメント（API 仕様・テーブルスキーマ等）を別途作成できます。