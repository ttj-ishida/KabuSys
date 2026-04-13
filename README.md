README
======

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を行うための軽量な Python コードベースです。本リポジトリは以下の主要機能を含みます:

- 注文発行・状態管理（ExecutionEngine / OrderManager / Reconciler）
- ポートフォリオ構築（候補選定、重み算出、数量算出、セクター制限等）
- ファクター計算・研究用ユーティリティ（モメンタム、ボラティリティ、バリュー等）
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI API 経由）
- 監視（System / Trade / Risk モニタ）および通知（LINE Push）、ストリームリットによるダッシュボード
- Paper Trading 用の分離された DB / モックブローカー、検証レポート出力ツール

本 README ではセットアップ方法、主要な使い方、環境変数、ディレクトリ構成を日本語でまとめます。

主な機能
--------
- Execution
  - ExecutionEngine による実行セッション管理
  - Broker クライアントの抽象化（本番・Paper Trading 切替）
  - OrderManager / OrderRepository による注文状態管理・永続化
  - 起動時の自動リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ算出（risk_based / equal / score）
  - セクター集中制限、レジーム乗数
- Research
  - ファクター算出（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores テーブルへ保存
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム判定
- Monitoring
  - System / Trade / Risk の監視ロジック
  - 監視ログ（SQLite）への永続化
  - kill.flag による ExecutionEngine の停止シグナル発行
  - LINE への一方向プッシュ通知（AlertManager）
  - Streamlit ダッシュボード（read-only 接続）
- Tools
  - Paper Trading 検証レポート生成スクリプト

前提・依存
-----------
推奨 Python バージョン: 3.9+

主な依存ライブラリ（pip インストール対象）:
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例:
    python -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt がある場合はそれを使ってください）

環境変数（主要項目）
-------------------
設定は .env / .env.local / OS 環境変数 から読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須（使用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必要に応じて）
- KABU_API_PASSWORD — kabuステーション API パスワード（実運用時）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）

その他（デフォルト値あり / 説明）:
- KABUSYS_ENV — 起動環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視の閾値
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定

セットアップ手順
----------------
1. リポジトリをクローン:
    git clone <repo-url>
    cd <repo>

2. 仮想環境作成・有効化（任意だが推奨）:
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存関係インストール:
    pip install duckdb psutil requests openai streamlit

4. データディレクトリ作成（既定のパスを使用する場合）:
    mkdir -p data

5. .env を作成（必要な環境変数を設定）
   例 (.env.example を参考):
       KABUSYS_ENV=development
       OPENAI_API_KEY=your_openai_key_here
       KABU_API_PASSWORD=...
       JQUANTS_REFRESH_TOKEN=...
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db

6. 初回起動時の DB 作成は各 run スクリプトが自動で実行します（init_monitoring_db を呼ぶため特別な初期化は不要）。

使い方
------
実行スクリプト:
- 実行エンジン（リアルまたは Paper Trading）を起動:
    python -m kabusys.run_execution

  説明:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）にデータを書き込みます。本番/本番DBとは分離されます。
  - 起動時にプロセス優先度を "high" に設定します（プラットフォームに応じて適用できない場合は警告を出して継続します）。
  - ExecutionEngine は duckdb / sqlite に接続し、実行セッションを run_session() で開始します。

- 監視ループを起動:
    python -m kabusys.run_monitoring

  説明:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト: 60秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を監視する仕様）。
  - run_monitoring は SystemMonitor.check_once() をポーリングで呼び続け、MonitoringDB にログを書き込みます。

- Streamlit ダッシュボード（read-only）:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  説明:
  - read-only URI を使って SQLite を開きます。MonitoringEngine が書き込み中でも安全に参照できます（ただし DB が存在しない場合はエラー表示）。

- Paper Trading 検証レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # または DB パスを指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

  説明:
  - 指定期間の system_status / trade_logs / risk_logs などを集計し、PASS/FAIL を判定して標準出力へレポートを出力します。
  - しきい値はスクリプト内定数（例: 稼働率 >= 99%、P95 レイテンシ <= 200 ms など）で定義されています。

- AI 系バッチ処理（プログラムから呼ぶ）:
  - ニュースセンチメントの算出:
        from datetime import date
        from kabusys.ai.news_nlp import score_news
        import duckdb
        conn = duckdb.connect("data/kabusys.duckdb")
        score_news(conn, target_date=date(2026,4,10), api_key="...")

  - レジーム判定:
        from kabusys.ai.regime_detector import score_regime
        score_regime(conn, target_date=date(2026,4,10), api_key="...")

  どちらも OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）。

開発メモ / 運用上の注意
-----------------------
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在する場所）を基に .env / .env.local を自動ロードします。
  - OS 環境変数は保護され、.env.local の override 設定でも上書きされません。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Paper Trading は本番 DB と完全分離:
  - KABUSYS_ENV=paper_trading の場合、設定により PAPER_TRADING_SQLITE_PATH を使用します。

- kill.flag:
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止する仕組みがあります。起動時にこれを自動で消すには KILL_FLAG_CLEAR_ON_START=1 を設定してください。

- プロセス優先度 / CPU affinity:
  - set_process_priority() / set_cpu_affinity() で OS に依存した最適化を試みます。権限不足等で失敗しても警告に留めて継続します。

ディレクトリ構成
----------------
以下は主要ソースの概観（src/kabusys 配下）。

- src/kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - run_execution.py           — ExecutionEngine 起動スクリプト（CLI エントリ）
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py         — 注文管理（OrderManager）
    - order_repository.py      — 注文永続化（SQLite） ※コードベースに存在
    - reconciler.py           — 起動時リコンシリエーション
    - broker_factory.py       — ブローカークライアント生成（Mock / 実ブローカー）
    - execution_engine.py     — ExecutionEngine 本体（run_session 等）
    - ...                     — その他 execution 関連モジュール
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算
    - risk_adjustment.py       — セクター制限・レジーム乗数
  - research/
    - factor_research.py       — momentum / value / volatility 等のファクター計算
    - feature_exploration.py   — 将来リターン・IC・統計サマリ等
    - __init__.py
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI 呼び出し、batch / retry /検証）
    - regime_detector.py       — マクロ＋ETF を用いたレジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ定義・低レイヤ DB 操作
    - system_monitor.py        — システム / データ鮮度監視
    - trade_monitor.py         — 注文滞留 / 約定異常監視
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - alert_manager.py         — LINE 通知送信（cooldown 管理）
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン（ポーリングループ）
    - streamlit_dashboard.py   — Streamlit ダッシュボード（read-only）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
    - __init__.py

（上記は主要ファイルの抜粋です。細部のモジュールはリポジトリツリーを参照してください）

トラブルシューティング
---------------------
- DB が開けない / ファイルが無い:
  - run_monitoring / run_execution は起動時に必要なテーブルを作成しますが、DuckDB/SQLite ファイル自体が存在しない場合は path のディレクトリが存在するか確認してください（data/ ディレクトリ等）。
- OpenAI API 例外・レートリミット:
  - news_nlp / regime_detector はリトライ実装がありますが、API キーの設定および課金・リミットに注意してください。
- LINE 通知が届かない:
  - LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID が正しく設定されていることを確認してください。設定が空の場合はログに警告を出して送信をスキップします。

ライセンス・貢献
----------------
ライセンス情報やコントリビューション方法はリポジトリのトップレベル（LICENSE / CONTRIBUTING.md 等）を参照してください。

補足
----
- ここに記載のコマンド・挙動はソース内の docstring / ログ出力に基づき要約しています。実際の運用前に各スクリプトをテスト環境で検証してください。
- 本 README はコードベースの主要機能・操作方法を簡潔にまとめたものであり、詳細設計（PortfolioConstruction.md / StrategyModel.md 等）が別ファイルにある場合はそちらも参照してください。