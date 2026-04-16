KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株自動売買システム KabuSys のコアライブラリ群です。
モニタリング、発注実行、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュース NLP / レジーム判定）などの機能を含みます。本 README はコードベースから抜粋した主要機能と使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

概要
----
KabuSys は次の主要コンポーネントで構成されます。

- Execution（注文発行・リスク管理・再同期）
- Monitoring（システム健全性・注文監視・リスク監視・アラート）
- Portfolio（候補選定・重み計算・株数決定）
- Research（ファクター計算・特徴量解析）
- AI（ニュースセンチメントスコアリング・レジーム判定）
- Tools（検証レポート生成などのユーティリティスクリプト）
- Utils（プロセス優先度やユーティリティ関数）
- 設定管理（環境変数/.env の読み込みと Settings クラス）

主な特徴
--------
- 実行エンジンと監視エンジンの分離（run_execution / run_monitoring）
- Paper trading モード（KABUSYS_ENV=paper_trading）では本番 DB と分離して専用 SQLite を使用
- 監視ログは SQLite（monitoring.db）へ永続化し、Streamlit ダッシュボードで可視化可能
- ニュースを LLM（OpenAI）でスコアリングし ai_scores テーブルへ格納
- マーケットレジーム（bull/neutral/bear）を price + マクロニュースで判定し DB に書き込み
- レコンシリエーション機能により再起動後の注文状態同期・ポジション差分検出
- ポートフォリオ構築用の純粋関数群（候補選定・等重/スコア重み・リスク基づく株数決定）
- LINE を使ったアラート通知（AlertManager）

前提・依存
-----------
推奨 Python 環境（このリポジトリに明示的な requirement ファイルは含まれていないため参考）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- sqlite3 （標準ライブラリ）
- その他（開発で必要なパッケージがあれば適宜追加）

例: 必要パッケージの一括インストール（お手元の環境に合わせて調整してください）
pip install duckdb psutil requests openai streamlit

設定（環境変数 / .env）
---------------------
設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

主要な環境変数（一部、デフォルト値あり）:
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文約定モード（instant|partial|never|reject。デフォルト: instant）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行系で使用するファイルパス（デフォルト data/execution.pid, data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト: 60）

セットアップ手順
----------------
1. リポジトリをチェックアウトして仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリをインストール
   pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成して必要な環境変数を定義します。
   - 例（.env）:
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     JQUANTS_REFRESH_TOKEN=...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

   自動ロードが働くと .env/.env.local は起動時に読み込まれます（ただし OS 環境変数が優先）。

4. データディレクトリを作成
   mkdir -p data

5. DuckDB / SQLite 用の初期データ準備
   - prices_daily / raw_financials などのテーブルを含む DuckDB はデータ取り込み処理が別途必要です（この README では省略）。
   - 監視 DB（monitoring.db）は起動時に init_monitoring_db() により必要テーブルを作成します。

使い方（主要スクリプト）
------------------------

1) 監視ループ（Monitoring）
- 機能: SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度）、TradeMonitor、RiskMonitor を定期実行しログ/アラート/kill flag を管理
- 実行:
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）をオーバーライド可能（デフォルト 60）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用（環境にかかわらず本番 sqlite_path を使用）

- 停止:
  - プロセスは data/stop_requested.flag の存在を検知して終了します（停止用フラグファイル）

2) 実行エンジン（Execution）
- 機能: ブローカークライアント生成、OrderManager / RiskManager / ExecutionEngine 起動、再同期（Reconciler）
- Paper trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）
- 実行:
  python -m kabusys.run_execution
  - 起動時に data/execution.pid への PID 書き込みや data/stop_requested.flag のチェックを行います
- 停止:
  - data/stop_requested.flag を作成すると実行ループは検知して停止処理を実行します
  - kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）は監視側の KillSwitch により作成され、ExecutionEngine に停止シグナルを送る用途に使われます

3) Streamlit ダッシュボード（監視 UI）
- 実行:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 読み取り専用で monitoring DB を開き、ダッシュボード表示（Overview / Positions / Orders / System）

4) Paper Trading 検証レポート
- スクリプト:
  python -m kabusys.tools.paper_verification_report
  例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  --from, --to: レポート期間
  --db: SQLite DB パス（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- 出力: 稼働率 / 注文成功率 / 送信率 / レイテンシ統計 等を標準出力に表示し PASS/FAIL 判定を行う

5) AI 関連ユーティリティ（ニュース NLP / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols から記事を集約し OpenAI へ送信、ai_scores テーブルへ書き込む
  - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ記録
- いずれも OpenAI の呼び出しでリトライやエラーハンドリングを組み込んでいるが、API キーは必須

運用上のファイル/フラグ
-----------------------
- data/stop_requested.flag: run_monitoring / run_execution が存在チェックして graceful shutdown を行うための停止フラグ
- data/execution.pid: run_execution が PID を書き込む（SystemMonitor はこの PID ファイルを見てプロセス存否を検知）
- data/kill.flag: KillSwitch が書き込む停止フラグ（監視がトリガーした強制停止）
- monitoring DB（SQLite）: デフォルト data/monitoring.db（init_monitoring_db でスキーマ作成）
- paper trading DB（SQLite）: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

監視 DB スキーマ（自動作成）
---------------------------
init_monitoring_db() は以下テーブルを作成します（冪等）:
- system_status: cpu/memory/disk/process_ok の履歴
- trade_logs: 発注ログ（latency_ms カラムあり）
- positions: 保有ポジション
- risk_logs: リスクイベントログ
- dashboard: ダッシュボード集計（id=1 の単一行保持）

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョン情報）
- config.py — 環境変数/.env の読み込みと Settings クラス
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント付与（OpenAI）
  - regime_detector.py — 市場レジーム判定（OpenAI + price）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層と MonitoringDB クラス
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイルによるエンジン停止ロジック
  - alert_manager.py — LINE push 通知ユーティリティ
  - monitoring_engine.py — 各モニターの統合ポーリング（テスト用 run_once / 本番用 run）
  - streamlit_dashboard.py — Streamlit ダッシュボード（UI）
- execution/
  - reconciler.py — 起動時のリコンシリエーション（注文・ポジション同期）
  - order_manager.py — 発注の高レベル API（Order State Machine）
  - order_repository.py, order_record.py, execution_engine.py, broker_factory.py, risk_manager.py 等（発注・ブローカー抽象化）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター制限・レジーム乗数
  - position_sizing.py — 株数計算・lot 丸め・aggregate cap
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC・統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発メモ / 注意点
-----------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- Monitoring は settings.env に関わらず Settings.sqlite_path（本番 DB）を使用します。paper_trading モードでは run_execution が PAPER_TRADING_SQLITE_PATH を使って DB を分離します。
- OpenAI を使う機能は API キー必須、かつ API 呼び出しの失敗時はフェイルセーフ動作（スコア 0.0、部分的スキップなど）を実装していますが、本番環境では注意して運用してください。
- CPU / Process priority 設定は set_process_priority() で行われます。権限不足や未対応 OS では警告を出してスキップします。
- DuckDB クエリは prices_daily / raw_financials / raw_news 等のテーブルを前提としています。データ投入パイプラインは別途必要です。

問い合わせ / 貢献
-----------------
バグ報告や機能要望は Issue を立ててください。機能拡張や改善の PR も歓迎します。

ライセンス
----------
（このリポジトリにライセンスファイルがある場合はそちらに従ってください。ここでは明示しません。）

付録: よく使うコマンドまとめ
---------------------------
- 監視起動:
  python -m kabusys.run_monitoring

- 実行エンジン起動:
  python -m kabusys.run_execution

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper report:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Python REPL でモジュールを使う（例: AI スコアリング / レジーム判定 を手動実行）:
  >>> import duckdb, sqlite3, datetime
  >>> conn = duckdb.connect("data/kabusys.duckdb")
  >>> from kabusys.ai.regime_detector import score_regime
  >>> score_regime(conn, datetime.date(2026,4,1), api_key="sk-...")

以上がこのコードベースの概要と基本的な使い方です。必要ならば各モジュールの詳細ドキュメント（関数引数/戻り値、DB スキーマ）を別途作成します。どの部分を優先して詳述したいか教えてください。