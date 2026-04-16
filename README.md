README
=====

概要
----
KabuSys は日本株自動売買向けの内部ライブラリ群と運用用コンポーネント群を含むプロジェクトです。本リポジトリは以下の主要機能を持ちます。

- 実行エンジン（ExecutionEngine）周りの発注管理 / リスク管理 / リコンシリエーション
- 監視（MonitoringEngine）: システム稼働状況、注文滞留、リスク監視、アラート送信（LINE）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・単元調整・セクター制限など）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）および特徴量解析
- AI 支援モジュール: ニュースのセンチメント解析（OpenAI）、市場レジーム判定
- 運用補助ツール: Paper Trading 検証レポート生成、Streamlit ベース監視ダッシュボード

主な設計方針：
- 本番データベースと Paper Trading は分離可能（KABUSYS_ENV により切替）
- ルックアヘッドバイアスを避けるため日付取得の扱いに注意して実装
- 外部 API 呼び出し（OpenAI 等）はフォールバック・リトライ等の堅牢性を考慮

機能一覧
--------
- 実行（run_execution.py）
  - Broker クライアントの生成（paper_trading モードでは MockBroker を利用）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine の起動
  - 停止フラグ検知（data/stop_requested.flag）による安全停止
- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale）や約定価格の異常検出
  - RiskMonitor: ドローダウン/ポジション上限監視、dashboard 更新・リスクログ記録
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine 停止指示
  - AlertManager: LINE によるプッシュ通知（クールダウン制御）
  - streamlit_dashboard: ブラウザで監視ダッシュボード表示
- 研究（research パッケージ）
  - ファクター計算（momentum/volatility/value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- ポートフォリオ（portfolio パッケージ）
  - 銘柄選定、等重/スコア重み、リスク調整（セクター制限 / レジーム乗数）、ポジションサイズ計算（単元丸め、aggregate cap）
- AI（ai パッケージ）
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ銘柄ごとにスコア化し ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA 乖離とマクロ記事の LLM センチメントを合成してレジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading DB を解析して検証レポート出力

セットアップ手順
----------------

1) Python 環境を用意
   - 推奨: Python >= 3.10
   - プロジェクトルートに src/ があり、パッケージは src 配下にある前提です。

2) 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3) 依存パッケージをインストール
   - requirements.txt がない場合は最低限以下をインストールしてください:
     pip install duckdb psutil openai requests streamlit
   - 必要に応じて他の依存（例えば testing 用ライブラリ等）を追加してください。

4) データディレクトリの作成
   - data/ を作成して適切な権限を設定します（デフォルト DB / PID / フラグファイルの格納先）。
     mkdir -p data

5) 環境変数の設定
   - ルートに .env を置くと自動で読み込まれます（OS 環境変数優先）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（Settings で参照されるもの）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定挙動
     - PAPER_TRADING_SQLITE_PATH（Paper Trading DB パス、デフォルト data/paper_trading.db）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知用, 空なら送信はスキップ）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - LOG_LEVEL
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数。デフォルト 60 秒）
   - 最小の .env 例:
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

6) 初期 DB スキーマ作成
   - run_monitoring.run と run_execution.main は起動時に init_monitoring_db() を呼び出し、監視用 SQLite のテーブルを冪等に作成します。特別な初期化は不要です。

使い方
------

※ 実行はプロジェクトルートから行うことを想定しています。src をパッケージとして利用するため、PYTHONPATH=src を指定するかプロジェクトをインストールしてください（開発時は PYTHONPATH=src を推奨）。

例: PYTHONPATH を指定してモジュール実行
- 監視ループ起動（常駐）
  PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は KABUSYS_ENV に関係なく production sqlite_path を使う点に注意。

- 実行エンジン起動（ExecutionEngine）
  PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使い data/paper_trading.db に履歴を記録します。
  - 起動時に既に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行エンジンは data/execution.pid を使ってプロセスの存在チェックを行います。

- Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いてダッシュボードを表示します。

- Paper Trading 検証レポート
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定できます（デフォルト data/paper_trading.db）。

- AI 機能をプログラムから呼ぶ（例）
  from kabusys.ai import score_news
  # duckdb_conn を生成して
  score_news(duckdb_conn, target_date=date(2026,4,15), api_key="sk-...")

停止とフラグ関連
- 実行停止リクエスト:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了処理を行います（run_monitoring/run_execution のそれぞれで使用）。
- Kill Switch:
  - KillSwitch はリスク条件を満たすと data/kill.flag を書き込み、別プロセス（run_execution）がその存在を検知して停止する運用想定です。
  - KillSwitch.clear() でフラグを削除できます（起動時のクリア挙動は設定可能）。

ディレクトリ構成
----------------
（抜粋）プロジェクトの主要ファイル/モジュール構成は以下のとおりです。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/設定管理
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite 永続化レイヤ
      - monitoring_engine.py   — 各 Monitor を束ねるループ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py (参照あり)
      - execution_engine.py (参照あり)
      - broker_factory.py (参照あり)
      - ...（その他発注関連モジュール）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/  (実行時に使用される、リポジトリルートの data/ 推奨)
      - monitoring.db (SQLite, 既定)
      - paper_trading.db (Paper Trading 用 DB)
      - kabusys.duckdb (DuckDB データ倉庫)
      - execution.pid, stop_requested.flag, kill.flag

注意事項 / 運用メモ
-----------------
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成を行い、既存 DB にないカラムがあれば ALTER で追加する簡易マイグレーションを含みます。
- Paper Trading:
  - KABUSYS_ENV=paper_trading を設定すると paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- OpenAI 呼び出し:
  - rate limit / network error / 5xx に対するリトライとフェイルオーバーを実装しています。OPENAI_API_KEY を必ず設定してください。
- プロセス優先度:
  - run_* スクリプトは起動時にプロセス優先度を上げようとします（psutil を利用）。権限が足りない場合は警告を出してスキップします。
- 自動環境変数読み込み:
  - プロジェクトルートの .env/.env.local を自動で読み込みます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献 / ライセンス
-----------------
- この README はコードベースの概要と運用方法をまとめたものです。実際のパッケージ化や CI / テストの手順、詳しい設定は別途ドキュメントや CONTRIBUTING.md を用意してください。
- ライセンス情報はリポジトリに含まれる LICENSE ファイルを参照してください（無い場合はプロジェクト所有者に確認してください）。

以上。必要であれば各モジュールの API ドキュメントや実行例（環境変数テンプレート、systemd/unit ファイル例、Docker 化手順など）を追記します。どの情報を優先して追加しますか？