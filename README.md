README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なPythonライブラリ／アプリケーション群です。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注／注文管理／リコンシリエーション）
- Monitoring（システム稼働状況、注文滞留、リスク監視、アラート）
- Research（ファクター計算・特徴量探索）
- AI（ニュース NLP を利用したセンチメントスコアリング、レジーム判定）
- Portfolio（候補選定・配分・株数決定の純粋関数群）
- Tools（Paper Trading 検証レポート等の補助スクリプト）

主な機能
--------
- 実運用・Paper Trading 切替対応（KABUSYS_ENV）
- ExecutionEngine：ブローカークライアントを抽象化し注文の作成／管理・リスクチェックを実行
- Reconciler：再起動後の注文状態同期とポジション差分検出
- Monitoring：CPU/メモリ/ディスク、プロセス生存確認、データ鮮度、滞留注文・約定異常の検出
- Kill Switch：閾値トリガーで停止フラグを発行して ExecutionEngine を即時停止
- AlertManager：LINE Messaging API によるアラート送信（クールダウン管理）
- Research：モメンタム／ボラティリティ／バリュー等のファクター計算、IC計算、統計サマリ
- AI：OpenAI を用いたニュースセンチメント評価（ai.score_news）と市場レジーム判定（ai.score_regime）
- Portfolio：候補選定、等金額／スコア加重配分、リスク調整、株数算出（単元丸めを含む）
- ユーティリティ：プロセス優先度・CPU affinity 設定、.env 自動読み込みロジック
- Streamlit ダッシュボード（監視 DB の可視化）
- Paper Trading 検証レポート生成スクリプト

前提・依存
-----------
- Python >= 3.10
- 主な依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- DB:
  - SQLite（監視ログ、orders 等）
  - DuckDB（時系列価格・ファクター計算等）
- 環境変数を .env/.env.local から自動読み込み（プロジェクトルートに .git または pyproject.toml がある場合）
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
- PID_FILE_PATH, KILL_FLAG_PATH 等（監視／停止制御用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

セットアップ手順
----------------
1. Python 環境を用意（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - あるいは要件ファイルがある場合は pip install -r requirements.txt

3. プロジェクトルートに .env を作成（.env.example を参照）
   - 例（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  # AI 機能を使う場合
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

   注: Settings モジュールは .env/.env.local を自動読み込みします（ただし OS 環境変数が優先されます）。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリを作成
   - mkdir -p data

5. （任意）DuckDB / SQLite に必要なテーブルや価格データを投入
   - research / ai / monitoring の多くは DuckDB 側に prices_daily や raw_news 等のテーブルを期待します。

使い方（よく使うコマンド）
-------------------------
- 監視プロセス起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 停止: data/stop_requested.flag を作成するとループが検知して終了します

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、Mock ブローカーを使用して paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使います
    - 停止: data/stop_requested.flag を作成するとエンジンに停止信号が送られます
    - ExecutionEngine 起動時に kill.flag（Settings.kill_flag_path）が存在する場合は起動をスキップします

- Streamlit ダッシュボード（監視 DB 可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI（ニュースセンチメント、レジーム判定）をプログラムから呼ぶ
  - 例（DuckDB 接続がある場合）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

- Research API（ファクター計算等）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - 各関数は duckdb 接続と target_date 等を受け取り結果リストを返します

停止／強制停止フロー
--------------------
- 正常停止（監視／実行）のために使用されるフラグ:
  - data/stop_requested.flag — run_monitoring / run_execution がポーリングで確認し、存在すれば終了する
  - data/kill.flag — KillSwitch によって生成され、ExecutionEngine に対する停止シグナルとして利用されます
- KillSwitch はリスク監視（ドローダウン、ポジション上限等）によりフラグを書き込み、アラートを送信できます

主要ファイルとディレクトリ構成
------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数／設定管理（.env 自動読み込み、Settings クラス）
- run_monitoring.py — SystemMonitor ポーリングループのエントリポイント
- run_execution.py — ExecutionEngine のエントリポイント

サブパッケージ（主な要素）
- ai/
  - news_nlp.py — ニュース記事を OpenAI に投げて銘柄別スコアを生成（ai.score_news）
  - regime_detector.py — マクロ + ETF MA200 を組合せて市場レジーム判定（ai.score_regime）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化レイヤ（テーブル初期化・CRUD）
  - system_monitor.py — CPU/メモリ/Disk・データ鮮度・PID チェック
  - trade_monitor.py — 注文滞留・約定価格異常の検出
  - risk_monitor.py — ドローダウン／ポジション上限監視
  - kill_switch.py — kill.flag 管理（書込・削除・評価）
  - alert_manager.py — LINE 送信ロジック（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, ... — 発注・注文履歴・リコンシリエーション関連
  - broker_factory.py, broker_api.py — ブローカ抽象化／Mock ブローカーサポート
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数（単元）計算、リスク／キャッシュ制約適用
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラ/バリュー等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定（psutil を使用）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力スクリプト

補足・運用上の注意
-----------------
- Paper Trading は本番 DB と完全に分離して動作する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- Settings は一部の環境変数を必須としており、未設定の場合は ValueError を投げます（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- OpenAI API を使う機能は API の料金／レート制限に依存します。score_news/score_regime はリトライとフォールバック（失敗時はスコア 0.0 等）を備えていますが、使用時は API キーの管理を行ってください。
- process_priority（psutil を利用）は環境により設定できない場合があります。その場合は警告ログを出してスキップします。

トラブルシューティング
----------------------
- DB が見つからない／開けない
  - DuckDB/SQLite のパスが正しいか、ファイルが存在するか、パーミッションを確認してください。
- LINE アラートが送信されない
  - LINE チャネルアクセストークンとユーザーIDが正しく設定されているか確認してください。
- AI 呼び出しが失敗する
  - OPENAI_API_KEY が正しく設定されているか、ネットワーク接続・レート制限を確認してください。

ライセンス・貢献
----------------
（ここにライセンス情報や貢献ルールを追記してください）

以上。開発・運用で追加して欲しい情報（例: デプロイ手順、Dockerfile、CI 設定、詳細な .env.example）等があれば教えてください。