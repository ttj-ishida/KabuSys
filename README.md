KabuSys — 日本株自動売買システム (README)
====================================

概要
----
KabuSys は日本株の自動売買・バックテスト・研究・監視を行うための小規模なシステム群です。本リポジトリは以下の役割を持つモジュールで構成されています。

- 取引実行エンジン（ExecutionEngine）
- 監視・アラートシステム（Monitoring）
- ポートフォリオ構築（選定・配分・株数計算）
- 研究用ファクター計算・特徴量解析（Research）
- ニュース NLP / レジーム判定（AI）
- 運用補助ツール（レポート生成、Streamlit ダッシュボード 等）

この README はコードベースの主要コンポーネント、セットアップ、実行方法、ディレクトリ構成を説明します。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading 切替（KABUSYS_ENV）
  - Broker クライアントの抽象化（Mock を含む）
  - リコンシリエーション（再起動時の注文・ポジション同期）
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）による安全停止

- 監視（Monitoring）
  - SystemMonitor: CPU・メモリ・ディスク・プロセス死活・データ鮮度監視
  - TradeMonitor: 注文滞留検出、約定価格異常検出
  - RiskMonitor: ドローダウン/ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じて停止フラグ書き込み（Execution を停止）
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）

- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算 / IC（Information Coefficient）計算
  - 統計サマリー補助関数

- ポートフォリオ構築（Portfolio）
  - 候補選定、等配分・スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - 株数決定（risk_based / equal / score）・単元（lot）丸め・aggregate cap

- AI（news_nlp / regime_detector）
  - OpenAI（gpt-4o-mini）呼び出しでニュースを銘柄ごとにセンチメント評価
  - マクロニュース + ETF MA200 による市場レジーム判定
  - OpenAI 呼び出しに対するリトライ・バリデーションの実装

- 運用ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - Streamlit による監視ダッシュボード（monitoring/streamlit_dashboard.py）

前提・依存
-----------
- Python 3.10+
  - 型ヒント（PEP 604）の使用により Python 3.10 以降を想定
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（組み込み）
- ネットワーク（OpenAI / LINE API を使う場合）

例:
pip install duckdb psutil requests openai streamlit

環境変数（主なもの）
--------------------
システムは .env / .env.local / 環境変数から設定を読み込みます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要キー（デフォルトや役割を簡潔に示します）:
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- SQLITE_PATH: 監視 DB（data/monitoring.db がデフォルト）
- DUCKDB_PATH: DuckDB ファイル（data/kabusys.duckdb がデフォルト）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード (instant|partial|never|reject) — default: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等は Settings で確認可能

セットアップ手順
---------------
1. リポジトリをクローンし、作業ディレクトリへ移動
   - リポジトリルートには pyproject.toml/.git を置くと .env 自動ロードが有効になります

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （実際の要件はプロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

4. data ディレクトリ作成（DB の出力先）
   - mkdir -p data

5. .env を作成（例: .env.example を参照して必要なキーを設定）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を設定
   - LINE 通知を使う場合: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID を設定

6. DuckDB / SQLite DB 初期化
   - 多くのスクリプトは起動時に必要なテーブルを作成するので、data ディレクトリと DB 書き込み権限があれば起動時に初期化されます。

簡単な実行例（ローカル）
------------------------
- 監視ループを起動（監視は MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能、デフォルト 60秒）
  - python -m kabusys.run_monitoring
  - または KABUSYS_ENV=development MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  補足:
  - run_monitoring は monitoring DB を init します（init_monitoring_db）。
  - 監視ループ内では data/stop_requested.flag を検知すると終了します。

- ExecutionEngine を起動（本番 / paper_trading 切替あり）
  - 本番:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（Mock ブローカーを使用、専用 DB に書き込まれる）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  補足:
  - 起動時に data/execution.pid を作成してプロセスの存在を監視します。
  - 停止は data/stop_requested.flag（または kill.flag による停止シグナル）で行われます。

- Streamlit ダッシュボード（監視 DB を参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で別 DB を指定可能（PAPER_TRADING_SQLITE_PATH 環境変数も利用可）

停止・制御
---------
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring / run_execution のループを安全に終了させるために存在をチェックします。
  - 運用上はこのファイルを作成することで両プロセスを順次停止させられます。

- kill.flag（Settings.kill_flag_path, デフォルト: data/kill.flag）
  - KillSwitch が条件を満たすとこのファイルを書き込み、ExecutionEngine に停止シグナルを出します。
  - Execution 起動時に Settings.kill_flag_clear_on_start が True であれば起動時に自動クリアできます。

注意事項・運用上のポイント
--------------------------
- 監視（monitoring）は Settings.env に関係なく常に "本番 sqlite_path"（SQLITE_PATH）を使用する実装になっています（run_monitoring のコメント参照）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path に書き込み、本番 DB と分離します。
- OpenAI / LINE 等の外部 API を利用する機能は API キーやトークンが未設定だと動作しないか、フェイルセーフ（スコア=0 等）で継続しますが、運用では必ず環境変数を用意してください。
- プロセス優先度や CPU affinity の設定は psutil を用いて行います。権限がない場合は警告を出してスキップします。
- DuckDB 接続は研究モジュールや AI モジュールで使用されます。prices_daily / raw_financials / raw_news 等のテーブル設計に従って入力データを用意してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと役割の簡単な一覧です。

- kabusys/__init__.py
  - パッケージ定義、バージョン

- kabusys/config.py
  - 環境変数・設定管理（.env 自動読み込み、Settings クラス）

- run スクリプト
  - kabusys/run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - kabusys/run_execution.py         — ExecutionEngine 起動スクリプト

- monitoring/
  - monitoring/monitoring_db.py      — SQLite ベースの永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring/system_monitor.py     — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - monitoring/trade_monitor.py      — 注文滞留／約定異常検出
  - monitoring/risk_monitor.py       — ドローダウン／ポジション上限監視
  - monitoring/kill_switch.py        — kill.flag 書き込みロジック
  - monitoring/alert_manager.py      — LINE 通知（クールダウン管理）
  - monitoring/monitoring_engine.py  — 各 Monitor を束ねてポーリングするエンジン
  - monitoring/streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - monitoring/__init__.py

- execution/
  - execution/order_manager.py      — 注文作成／状態遷移の外向き API
  - execution/reconciler.py         — 起動時の自動復旧・リコンシリエーション
  - （他: broker_factory, execution_engine, order_repository などのファイルが想定）

- portfolio/
  - portfolio/portfolio_builder.py   — 候補選定・重み計算
  - portfolio/position_sizing.py     — 株数計算・リスク制限・単元丸め
  - portfolio/risk_adjustment.py     — セクター制限・レジーム乗数
  - portfolio/__init__.py

- research/
  - research/factor_research.py      — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - research/feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - research/__init__.py

- ai/
  - ai/news_nlp.py                   — raw_news を LLM で評価して ai_scores に書き込み
  - ai/regime_detector.py            — ETF MA200 + LLM で市場レジーム判定
  - ai/__init__.py

- tools/
  - tools/paper_verification_report.py — Paper Trading 検証レポート生成ツール（CLI）

- utils/
  - utils/process_priority.py        — プロセス優先度 / CPU affinity の抽象ユーティリティ
  - utils/__init__.py

- data/ （実行時に使用）
  - monitoring.db (デフォルト SQLITE_PATH)
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - execution.pid / stop_requested.flag / kill.flag などの運用フラグや PID

開発・テストのヒント
--------------------
- Settings は .env 自動ロードを行いますが、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効にできます。
- MonitoringEngine には run_once() がありユニットテストで個別 monitor を1回だけ実行して挙動を検証できます。
- OpenAI 呼び出し箇所は内部で _call_openai_api を抽象化しているため、テスト時は unittest.mock.patch で差し替えてレスポンスを模擬できます。
- DuckDB を利用する研究モジュールは入力テーブル（prices_daily, raw_financials, raw_news 等）を用意して結果を確認してください。

よくある運用タスク
------------------
- 監視の即時停止: touch data/stop_requested.flag
- Execution を外部から停止（KillSwitch による自動生成を待つ）: KillSwitch ロジックが作成する data/kill.flag を使用
- kill.flag を手動でクリア: rm data/kill.flag（起動時に自動クリアを有効にしている場合もあり）
- Paper 検証: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

ライセンス・貢献
----------------
- 本 README ではライセンス情報を提供していません。実際のリポジトリで LICENSE ファイルを確認してください。
- バグ報告・機能提案は issue を立ててください。

補足（実装上の要点）
-------------------
- run_monitoring は MonitoringDB の init を実行し、Monitoring は常に SQLITE_PATH を使う点に注意してください（コメント参照）。
- run_execution は KABUSYS_ENV=paper_trading の場合 data/paper_trading.db を利用して本番 DB と完全分離します。
- AI モジュールは OpenAI API とのやり取りで JSON mode を使用し、厳格なレスポンス検証とクリッピング（±1.0）を行います。
- process_priority や cpu_affinity の設定はプラットフォーム差分を吸収し、失敗時は警告のみで継続します。

問い合わせ
----------
不明点や実行に関する質問があれば、プロジェクトの issue またはメンテナに問い合わせてください。