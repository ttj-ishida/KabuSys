# KabuSys — 日本株自動売買システム (README)

このリポジトリは、国内株自動売買のための小規模なフレームワークです。監視（Monitoring）、実行エンジン（Execution）、ポートフォリオ構築、研究用ファクター計算、AI（ニュースセンチメント / レジーム判定）などを含みます。本 README はコードベースの主要な使い方・セットアップ手順とディレクトリ構成をまとめたものです。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件
- セットアップ手順
- 実行方法（使い方）
- 環境変数 / .env の例
- 停止・安全装置について
- ディレクトリ構成（主要ファイルの説明）
- 補足・注意事項

---

プロジェクト概要
- KabuSys は日本株の自動売買に必要なコンポーネント群（注文エンジン、監視、リスク管理、ポートフォリオ構築、研究用分析、AI を用いたニュース処理など）を含むモジュール群です。
- コードは実運用（live）・ペーパートレード（paper_trading）・開発（development）を想定した設定に対応しています。ペーパートレード時は本番の注文 API を模擬する MockBrokerClient と専用の SQLite DB に分離して記録します。

主な機能一覧
- Execution（発注エンジン）
  - OrderManager, ExecutionEngine（起動・セッション実行）
  - Reconciler による再起動時の自動復旧（OrderSent 照合・ポジション差分検出）
  - RiskManager（発注前の制約チェックなど）
- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス存在チェック、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン / ポジション上限の監視、ダッシュボード更新
  - MonitoringEngine：これらを束ねてポーリング実行
  - AlertManager：LINE への通知（オプション）
  - KillSwitch：リスク条件到達時に ExecutionEngine を停止させるフラグ生成
  - Streamlit ダッシュボード（読み取り専用で監視状況表示）
- Portfolio（銘柄選定・ウェイト・ポジションサイジング）
  - 候補選定、等重/スコア重み、リスク調整（セクター上限・レジーム乗数）、株数計算（lot 単位）
- Research（DuckDB ベースのファクター計算・特徴量解析）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC 計算、統計サマリー
- AI（ニュースセンチメント・レジーム判定）
  - news_nlp.score_news：OpenAI を使ってニュースを銘柄別にセンチメント評価し ai_scores テーブルへ書き込む
  - regime_detector.score_regime：ETF（1321）MA とマクロニュースの LLM センチメントを合成して日次レジーム判定を行い market_regime テーブルに書き込む
- ユーティリティ
  - 環境変数自動ロード (.env / .env.local)、プロセス優先度 / CPU affinity 設定ユーティリティ

前提条件
- Python 3.9+（型ヒントの使用やモダンライブラリ前提。実際の環境に合わせてください）
- 必要パッケージ（主要なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- OS: Linux / macOS / Windows（プロセス優先度の扱いは OS に依存）

セットアップ手順（開発環境想定）
1. リポジトリをクローンし、仮想環境を作成・有効化する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows PowerShell の場合は .venv\Scripts\Activate.ps1)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （requirements.txt があれば）pip install -r requirements.txt

3. .env を作成（下の「環境変数 / .env の例」参照）
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. DB ディレクトリの準備
   - デフォルトの DB は data/ 以下を使用します。必要なら作成してください（例: mkdir -p data）。
   - monitoring 用 SQLite：data/monitoring.db（Settings.sqlite_path のデフォルト）
   - DuckDB：data/kabusys.duckdb（Settings.duckdb_path のデフォルト）
   - PaperTrading 用 SQLite（ペーパートレード時）：data/paper_trading.db

使い方（起動 / 実行例）
- ExecutionEngine を起動（実取引／ペーパー切替）
  - 本番環境相当（KABUSYS_ENV=live または development）:
    - python -m kabusys.run_execution
  - ペーパートレード（Mock ブローカー、専用 DB に記録）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行開始時にプロセス優先度を "high" に設定します。起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - ExecutionEngine の PID は data/execution.pid に書き込まれます。

- Monitoring を起動（backgroun ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - 監視は Settings の sqlite_path（本番 DB）を常に使用します（環境に依らず）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いてダッシュボード表示します。

- Paper Trading 検証レポート出力ツール
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラム内から呼び出す）
  - news_nlp.score_news を呼んでニュースセンチメントを ai_scores に書き込めます。引数に DuckDB 接続と target_date, api_key（または環境変数 OPENAI_API_KEY）を渡します。
  - regime_detector.score_regime で日次の市場レジームを算出し market_regime テーブルへ保存します。

環境変数 / .env の例
- 必須（少なくとも実行するモジュールで要求されるものを設定してください）
  - JQUANTS_REFRESH_TOKEN — J-Quants API のトークン（research 周りで使用）
  - KABU_API_PASSWORD — kabuステーション API のパスワード（実注文時）
- オプション / その他
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG / INFO / ...
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE 通知）用

例 (.env)
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

停止・安全装置について
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py / run_execution.py はループ中にこのファイルの存在を検知すると平常終了します。安全に停止させたい場合はこのファイルを作成してください（中身は任意）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch がリスク閾値到達時に書き込むフラグです。ExecutionEngine は起動時にこのフラグの存在を確認し、存在する場合は起動を拒否します。フラグは意図的にクリアする必要があります（KillSwitch.clear や手動削除）。
- PID ファイル（data/execution.pid）
  - ExecutionEngine は起動時に PID を書きます。SystemMonitor はこの PID ファイルを見てプロセス生存チェックを行います。古い（stale）PID が検出されると削除してアラートをログします。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — 環境変数 / 設定読み込みロジック（.env の自動読み込みを含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（ペーパートレード切替対応）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite 永続化層（テーブル作成・アップサート等）
    - system_monitor.py — システム状態・データ鮮度のチェック
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag の書き込み・評価ロジック
    - alert_manager.py — LINE へのプッシュ通知ロジック
    - monitoring_engine.py — 複数 Monitor を束ねる実行ループ（テスト用 run_once / 本番 run）
    - streamlit_dashboard.py — Streamlit を使った監視ダッシュボード（読み取り専用）
  - execution/
    - order_manager.py — 注文作成・同期等の外向き API
    - reconciler.py — 起動時の照合・復旧ロジック
    - order_repository.py, order_record.py, その他（注文管理・DB 層）
    - execution_engine.py, broker_factory.py, broker_api.py, 等
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定・スケーリング（lot 単位）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - ai/
    - news_nlp.py — raw_news を OpenAI で評価して ai_scores に書き込む処理
    - regime_detector.py — MA200 とマクロニュースを合成して market_regime を作成
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力 CLI

補足・注意事項
- DB のマイグレーションは monitoring_db.init_monitoring_db() 内で簡単なカラム追加を行います（冪等）。実際の運用では完全なマイグレーション戦略が必要です。
- AI モジュールは OpenAI API に依存します。API レート制限・エラーに対してはリトライやフェイルセーフ（スコア 0 にフォールバック等）を実装していますが、キーは必ず安全に管理してください。
- 設定は環境変数を基本とし、.env/.env.local を自動読み込みします（プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存しません）。
- MONITOR_POLL_INTERVAL（秒）で監視ループのインターバルを調整できます（0 以下の値は無視されデフォルト適用）。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（権限不足で失敗する場合は警告ログのみ）。

---

さらに詳しい開発ドキュメントや API 仕様（Engine の設定、OrderRequest フォーマット、Broker API 実装ガイド、ポートフォリオ構築の理論的背景など）は別途ドキュメント（例えば PortfolioConstruction.md, StrategyModel.md など）を参照してください（コード内コメントに参照先が記載されています）。

必要であれば、この README にデプロイ手順や Dockerfile / systemd ユニットのサンプル、より詳細な .env.example のテンプレート、運用チェックリスト等を追加で作成します。どの情報を優先して追加しますか？