KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリには以下の主要機能が含まれます。

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視サブシステム（System / Trade / Risk モニタ、アラート、Kill Switch）
- ポートフォリオ構築ロジック（候補選定、重み計算、ポジションサイズ算出）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- AI ベースのニュース NLP（OpenAI を用いたセンチメント算出）
- Paper Trading 用ツール（検証レポート生成）
- Streamlit ベースの監視ダッシュボード

主な特徴
-------
- モジュール化された監視 (monitoring) と実行 (execution) の分離
- Paper Trading モードでは本番 DB と分離された SQLite を利用
- DuckDB を用いた時系列ファクター計算 / リサーチ機能
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定（任意）
- LINE Push を用いたアラート送信（任意）
- フラグファイルによる安全停止（kill.flag / stop_requested.flag）
- テストしやすい純粋関数群（ポートフォリオ計算等）

前提・依存関係
--------------
- Python 3.10+
- 外部ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリ sqlite3 を使用）
- 必要なパッケージは requirements.txt を作るか pip で個別インストールしてください。

例:
  pip install duckdb psutil requests openai streamlit

環境設定
--------
設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。自動読み込みはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

重要な環境変数（主なもの）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の執行モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行時の pid/kill フラグファイルパス

例（.env の抜粋）
  KABUSYS_ENV=development
  JQUANTS_REFRESH_TOKEN=your_jquants_token
  KABU_API_PASSWORD=your_kabu_password
  OPENAI_API_KEY=sk-...
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  PAPER_FILL_MODE=instant
  LOG_LEVEL=INFO

起動・セットアップ手順
---------------------
1. リポジトリをクローンし、必要パッケージをインストールします。
   - 推奨: 仮想環境を作成してからインストールしてください。

2. 環境変数を設定するか、プロジェクトルートに .env/.env.local を用意します。
   - .env.example をもとに作成してください（本リポジトリに例ファイルがある想定）。

3. 必要に応じて DuckDB / SQLite の初期データを投入してください。
   - 監視用 DB のスキーマは init_monitoring_db() が自動で作成・マイグレーションします。
   - run_execution/run_monitoring の起動時に init_monitoring_db が呼ばれます。

基本的な使い方
--------------

起動スクリプト
- 監視ループを起動（SystemMonitor のポーリング）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関係なく monitoring.db（settings.sqlite_path）を参照します。

- 実行エンジン（ExecutionEngine）を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と完全分離）。
  - 実行はバックグラウンドスレッドで動き、stop フラグや stop_requested.flag により安全停止します。

停止 / フラグ
- data/stop_requested.flag（run_* スクリプトで使用）を作成すると、ポーリング/エンジンは検知して終了します。
- KillSwitch は監視結果に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます。KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を使用します。

Paper Trading 検証レポート
- ツール: kabusys.tools.paper_verification_report
- 実行例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  --db PATH: Paper Trading SQLite のパス（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

Streamlit ダッシュボード
- 起動方法:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only で SQLite に接続し、ダッシュボードを表示します。

AI 関連機能
- kabusys.ai.news_nlp.score_news(target_date) / kabusys.ai.regime_detector.score_regime(target_date)
- OPENAI_API_KEY が必要（引数で渡すことも可能）。
- レート制限・接続エラーはエクスポネンシャルバックオフでリトライします。失敗時はフェイルセーフ（多くは 0.0 やスキップ）で継続します。

主要モジュール・ディレクトリ構成
------------------------------
以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- kabusys/
  - __init__.py                 — パッケージ宣言、バージョン
  - config.py                   — Settings クラス（環境変数 / .env 管理）
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト

  - monitoring/
    - __init__.py
    - monitoring_db.py          — SQLite スキーマ / 永続化レイヤ
    - system_monitor.py         — CPU/メモリ/ディスク / データ鮮度 / PID チェック
    - trade_monitor.py          — 注文滞留 / 約定異常チェック
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag の作成 / 管理
    - alert_manager.py          — LINE Push API 経由のアラート
    - monitoring_engine.py      — 複数モニタの統合ループ
    - streamlit_dashboard.py    — Streamlit ダッシュボード

  - execution/
    - order_manager.py          — 注文作成 / 管理の外向 API
    - order_repository.py       — Orders DB アクセス（SQLite）
    - reconciler.py             — 起動時の注文・ポジション突合せ
    - reconciler などの他サブモジュール（broker_factory 等は実装想定）

  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算（等重・スコア重み）
    - position_sizing.py        — 発注株数計算（リスクベース / 等配分等）
    - risk_adjustment.py        — セクター上限・レジーム乗数

  - research/
    - factor_research.py        — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py    — 将来リターン計算・IC・統計サマリ

  - ai/
    - news_nlp.py               — ニュースセンチメント集約・OpenAI 呼び出し
    - regime_detector.py        — ma200 + マクロセンチメントで市場レジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

  - utils/
    - process_priority.py       — プロセス優先度／CPU affinity ユーティリティ

注意事項 / 運用上のヒント
-----------------------
- 実行時にプロセス優先度を変更します（psutil を利用）。権限が必要な場合は設定に失敗して警告のみになります。
- Paper Trading モードは本番 DB と明示的に分離されるため、検証時は KABUSYS_ENV=paper_trading を利用してください。
- OpenAI/API キーや kabu API 情報は秘匿してください。CI 等での利用は環境変数注入を推奨します。
- monitoring_db.init_monitoring_db() は冪等にテーブル・カラムを作成/マイグレーションします。run_* 起動時に自動で呼ばれます。
- stop/kill フラグは data/ 以下のファイルを利用します（data ディレクトリは自動作成されます）。プロダクション運用では監視・復旧運用ルールを整備してください。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）はリサーチ / AI モジュールが前提とするスキーマに従ってデータ投入してください。

連絡・貢献
-----------
本 README はコードベースの注釈に基づく概要説明です。実装の追加・修正、ドキュメント改善は PR を歓迎します。

--- 

必要であれば、README に含める具体的な .env.sample、requirements.txt の例、コマンド実行手順の詳細（systemd ユニット例や docker-compose 例）などを追記できます。どの情報を優先して追加しましょうか？