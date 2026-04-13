README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群のモジュール群です。本リポジトリは以下の機能を備えています。

- 注文の作成／送信／状態管理（ExecutionEngine / OrderManager / Reconciler）
- ポートフォリオ構築（候補選定・重み算出・サイズ決定・セクター制限）
- ファクター計算・リサーチ（モメンタム / ボラティリティ / バリュー 等）
- ニュースの LLM によるセンチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF MA + マクロニュースの LLM 結果）
- 監視（システム状態、注文滞留、リスク監視）と LINE 通知
- Paper Trading 用検証レポート生成・Streamlit ダッシュボード

重要設計方針の抜粋
- 設定は環境変数（.env / .env.local）から読み込み。配布後も動作するようプロジェクトルートを自動検出。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB から分離（data/paper_trading.db 等）。
- LLM（OpenAI）呼び出しはリトライやレスポンス検証を含む堅牢化処理あり。失敗時はフェイルセーフ（0.0 等）で継続。
- 監視は SQLite（monitoring.db）へ永続化し、Streamlit で可視化可能。

主な機能一覧
----------------
- 実行（Execution）
  - run_execution.py: ExecutionEngine を起動。ブローカークライアント生成、リスク管理、オーダー管理、リコンシリエーションを行う。
  - Paper Trading モードでは MockBroker を使用し、paper_trading 専用 SQLite に記録。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）。
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine によりシステム状態・注文・ドローダウン等を監視。
  - AlertManager: LINE Push によるアラート送信（トークン未設定時はログ出力のみ）。
  - KillSwitch: 条件達成時に flag ファイルを書き ExecutionEngine 停止シグナルを発行。
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード。

- リサーチ・ポートフォリオ構築
  - research: calc_momentum, calc_volatility, calc_value 等のファクター計算。
  - portfolio: 候補選定、等重／スコア重み、リスク調整（セクター上限／レジーム乗数）、発注株数決定。

- AI（LLM）
  - ai.news_nlp.score_news: raw_news を集約し OpenAI で各銘柄のセンチメントを算出して ai_scores に保存。
  - ai.regime_detector.score_regime: ETF MA200 とマクロニュースの LLM 結果を合成して market_regime に書き込む。

- ツール
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率、注文成功率、レイテンシ等）。

セットアップ手順
----------------
1. Python と仮想環境
   - Python 3.10+ を推奨。
   - 仮想環境を作成し有効化する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - 必要な主要パッケージ（一例）:
     - duckdb, psutil, openai, requests, streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （実際のプロジェクトでは requirements.txt を用意して pip install -r requirements.txt を実行してください）

3. 環境変数（.env）設定
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（必須／任意）:
     - 必須（利用する機能に応じて）:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 任意 / デフォルトあり:
       - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
       - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (監視用デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (Paper Trading: data/paper_trading.db)
       - PAPER_FILL_MODE (instant|partial|never|reject、デフォルト: instant)
       - PID_FILE_PATH (デフォルト: data/execution.pid)
       - KILL_FLAG_PATH (デフォルト: data/kill.flag)
       - KABUSYS_ENV (development|paper_trading|live、デフォルト: development)
       - LOG_LEVEL (DEBUG|INFO|...)
       - OPENAI_API_KEY（AI 機能を使う場合）

   - 例 (.env):
     - KABUSYS_ENV=development
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

4. データベース初期化
   - run_monitoring.py / run_execution.py は起動時に monitoring DB の初期化（テーブル作成・マイグレーション）を行います。手動で初期化する必要は通常ありません。

基本的な使い方
----------------
- 監視ループを起動
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（正の整数を指定）。
  - 実行:
    - python -m kabusys.run_monitoring
  - ログレベルは Settings.log_level / logging.basicConfig によって制御されます。

- ExecutionEngine を起動（注文実行）
  - Paper Trading（モックブローカー）で起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番ブローカーで起動する場合は KABUSYS_ENV=live を設定し、必要な API 認証情報を環境変数で用意してください。

- Streamlit ダッシュボード
  - 監視 DB（読み取り専用）を指定して起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - デフォルト DB: data/paper_trading.db。オプションで --db で指定可能。
  - 実行例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュールの呼び出し（ライブラリ利用）
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続と対象日を与えてスコアを ai_scores テーブルへ書き込み。
  - regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルへ結果を書き込み。
  - これらは自動的に OPENAI_API_KEY を参照しますが、関数引数で明示的にキーを渡すことも可能です。

- モニタリングとキルスイッチ
  - RiskMonitor はダッシュボードの portfolio_value / peak_value を参照してドローダウン監視を行い、しきい値を超えると kill.flag を書き込みます（Settings.kill_flag_path でパス指定）。
  - KillSwitch が書き込んだ flag は ExecutionEngine 側で検知して安全に停止する仕組みになっています。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
  - パッケージのメタデータ（__version__ 等）

- config.py
  - 環境変数読み込み、Settings クラス（全設定管理）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モードに対応）

- monitoring/
  - monitoring_db.py — SQLite テーブル定義・永続化用 API（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン／ポジション上限監視
  - kill_switch.py — flag による停止シグナル発行
  - alert_manager.py — LINE への一方向通知
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード

- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py など（注文管理・再同期・実行ロジック）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数決定ロジック
  - risk_adjustment.py — セクター上限・レジーム乗数

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB ベース）
  - feature_exploration.py — 将来リターン計算・IC・統計サマリ

- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.py — MA200 とマクロニュースセンチメントの合成でレジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

ユーティリティ
- utils/process_priority.py — OS に依存しないプロセス優先度／CPU affinity 設定ラッパー

運用上の注意
--------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に行われます。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring/run_execution は起動直後にプロセス優先度を上げようとします（set_process_priority("high")）。権限がない場合は警告が出ますが処理は継続します。
- Paper Trading と本番は DB を明確に分離する設計です。KABUSYS_ENV を適切に設定して運用してください。
- OpenAI API を利用する機能は API キーの関与・課金が発生します。実行前に OPENAI_API_KEY を設定し、費用やレート制限を理解してください。

FAQ（よくある質問）
-------------------
Q: 監視間隔を変更したい
A: MONITOR_POLL_INTERVAL 環境変数に秒数（正の整数）を設定してください。例: export MONITOR_POLL_INTERVAL=30

Q: Paper Trading の DB はどこにある？
A: デフォルトは data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH で変更可能。

Q: LINE 通知を有効にするには？
A: LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を .env に設定してください。未設定時は通知は送信されずログのみ出ます。

Q: LLM コールの失敗時はどうなる？
A: 本実装は 429 / ネットワーク断 / タイムアウト / 5xx をリトライしますが、最終的に失敗した場合はフェイルセーフ（例: macro_sentiment=0.0）で処理を継続します。部分的な失敗は既存データを消去しないよう書込みロジックを工夫しています。

付記
----
この README は現行ソースコードに基づいて作成しています。実運用前に環境変数や依存関係（特に外部 API キーと DB パス）を必ず確認してください。必要に応じて requirements.txt、デプロイ手順、監視・バックアップ設計を追加してください。