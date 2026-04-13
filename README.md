README.md

プロジェクト概要
-------------
KabuSys は日本株の自動売買を想定したモジュール群です。価格ファイル（DuckDB）や監視用 SQLite を使って、シグナル生成・ポートフォリオ構築・発注管理・監視・AI によるニュース評価などを行うためのライブラリ／実行スクリプトを含みます。  
本リポジトリは実運用を想定したフェーズ構成（development / paper_trading / live）に対応しており、Paper Trading 環境では本番 DB と分離してモックブローカーを使う設計になっています。

主な特徴（機能一覧）
-----------------
- ポートフォリオ構築
  - 候補選定（score / rank ベース）、等分配・スコア配分の重み計算
  - 単元株丸め、リスクベースサイズ計算、セクター集中制限、レジーム乗数
- 発注系
  - OrderManager / Reconciler による注文状態管理と再帰的リコンシリエーション
  - ExecutionEngine 起動スクリプト（run_execution）により BrokerClient を用いた発注処理
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor による定期ポーリング、監視ログ保存（SQLite）
  - KillSwitch によるフラグファイルを使った ExecutionEngine 停止シグナル
  - AlertManager による LINE Push 通知（オプション）
  - Streamlit ベースの監視ダッシュボード（read-only 接続）
- 研究・解析
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 予測リターン計算、IC 計算、特徴量サマリ
- AI（LLM）
  - ニュース記事を OpenAI に送って銘柄ごとのセンチメントを ai_scores テーブルへ保存
  - マクロ記事を用いた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. Python と仮想環境
   - Python 3.10+ を推奨（コード上の型ヒントと構文に準拠）
   - 仮想環境を作成して有効化しておくこと。

     python -m venv .venv
     source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージ（例）
   - 必要な主要パッケージ（実際の requirements.txt がある場合はそちらを使用してください）:

     pip install duckdb psutil requests openai streamlit

   - （SQLite は標準ライブラリで利用可能）

3. データディレクトリ
   - デフォルトの DB パスはプロジェクト相対の data/ 以下です。必要に応じて作成してください。

     mkdir -p data

環境変数（.env）
----------------
本ライブラリはプロジェクトルートにある .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（主要なもの）
- KABUSYS_ENV: 実行環境（"development" / "paper_trading" / "live"）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な場合あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の成行充足モード（"instant"|"partial"|"never"|"reject"。デフォルト: "instant"）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（"DEBUG","INFO",...）

例（.env の一部）
- .env.example を参考に作成してください。最低限必要な場合:
  JQUANTS_REFRESH_TOKEN=your_token
  KABU_API_PASSWORD=your_password
  OPENAI_API_KEY=sk-...

使い方
-------

1) 監視プロセスの起動（SystemMonitor 単体）
   - 監視ループを起動して system_status / risk_logs / trade_logs 等を定期的に記録します。

     KABUSYS_ENV=development python -m kabusys.run_monitoring

   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（例: 30秒）:

     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   - run_monitoring は Settings を読み、監視 DB（sqlite）と duckdb に接続して動きます。監視は本番 sqlite_path を使用します（環境に関わらず）。

2) 実行エンジン（発注）起動
   - ExecutionEngine を起動します（実際のブローカーまたは Paper Trading のモックが使用されます）:

     python -m kabusys.run_execution

   - KABUSYS_ENV=paper_trading にすると MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。これにより本番 DB と分離されます。
   - 起動時にプロセス優先度（high）を設定します。PID ファイルは Settings.pid_file_path（data/execution.pid）に書かれます。

3) Streamlit 監視ダッシュボード
   - read-only で監視 SQLite を参照するダッシュボード：

     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

   - 引数 --db で監視 DB を指定できます。

4) Paper Trading 検証レポート生成
   - 過去の paper_trading DB を集計してレポートを stdout に出力します。

     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

   - レポートは稼働率・注文成功率・送信率・レイテンシ等を評価し PASS/FAIL を判定します。

5) AI 機能（ニューススコアリング / レジーム判定）
   - OpenAI API キーが必要です（OPENAI_API_KEY または api_key を直接渡す）。
   - ニューススコアリング関数（プログラムから呼ぶ例）:

     from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect('data/kabusys.duckdb')
     score_news(conn, date(2026,4,10), api_key='sk-...')

   - レジーム判定:

     from kabusys.ai.regime_detector import score_regime
     score_regime(conn, date(2026,4,10), api_key='sk-...')

注意点 / 運用メモ
- Paper Trading は本番 DB と分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は MONITOR_POLL_INTERVAL と KABUSYS_ENV を参照しますが、Monitoring は環境にかかわらず本番 sqlite_path を使う点に注意してください（監視は常に本番を監視）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）から行われます。CWD に依存しない実装です。
- プロセス優先度や CPU affinity の設定はプラットフォームに依存します（psutil を使用）。権限不足の場合は警告を出してスキップします。
- OpenAI コールはリトライとバックオフを実装していますが、API キー未設定や恒常的な API エラー時は AI 機能は失敗またはスキップされる場合があります。

ディレクトリ構成（主なファイルと説明）
-----------------------------------
- src/kabusys/
  - __init__.py — パッケージの基本情報（バージョン等）
  - config.py — 環境変数 / .env 自動読み込み・Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（発注エンジン）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出（単元丸め・集約 cap）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite 用の監視テーブル初期化・永続化 API
    - system_monitor.py — CPU / メモリ / データ鮮度 / PID チェック
    - trade_monitor.py — 滞留注文・約定異常検知
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込み（Execution 停止シグナル）
    - alert_manager.py — LINE Push 通知ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるループ（テスト用 run_once あり）
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動コマンドあり）
  - execution/
    - order_manager.py — Order State Machine の外向き API
    - reconciler.py — 起動時自動復旧・ポジション照合
    - （その他: broker_factory, execution_engine, order_repository 等が存在）
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース記事の LLM センチメント集計、ai_scores 書込み
    - regime_detector.py — マクロ + ma200 で市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

開発者向けメモ
----------------
- DuckDB 接続はリード専用クエリや複雑な集計を効率的に処理するために使われます。prices_daily / raw_financials / raw_news 等のテーブルが前提です。
- monitoring_db.init_monitoring_db() は冪等でテーブルと必要なマイグレーション（カラム追加）を行います。
- AI 関連は OpenAI の JSON Mode を使って厳密な JSON 応答を期待する実装になっています。API レスポンスのパース・検証ロジックを含みます。
- 単体テストの実行やモック注入のために各所で外部呼び出し（OpenAI クライアント / psutil / requests）を差し替えやすく設計しています（関数分離 / private wrapper）。

ライセンス
----------
（リポジトリに合わせてライセンス情報を記載してください）

以上。必要であれば README にサンプル .env.example、requirements.txt、起動スクリプトの systemd ユニット例、デバッグの方法（ログ出力の増やし方）などを追加します。どの情報を優先して追加しますか？