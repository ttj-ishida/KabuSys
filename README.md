README
======

概要
----
KabuSys は日本株向けの自動売買／研究／監視を目的とした小規模な Python プロジェクトです。本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: ブローカーとの発注・注文状態管理・リスク制御・リコンシリエーション
- 監視（Monitoring）: システム状態・注文滞留・リスク（ドローダウン等）監視、アラート送信
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制限・レジーム調整
- リサーチ: ファクター計算（モメンタム／ボラティリティ／バリュー等）、将来リターン計算、IC / 統計サマリ
- AI 支援: ニュースのセンチメントスコアリング（OpenAI）／市場レジーム判定
- ユーティリティ: プロセス優先度・CPU affinity 設定、.env 読み込み等
- 各種ツール: Paper Trading の検証レポート生成、Streamlit ダッシュボードなど

主な特徴
--------
- 実運用・Paper Trading を明確に分離（環境変数 KABUSYS_ENV により切替）
- DuckDB / SQLite を利用したデータ格納（prices_daily などは DuckDB、監視ログは SQLite）
- OpenAI API を用いたニュース NLP（スコアは ai_scores テーブルへ保存）
- 監視ループは flag ファイルによる外部停止（data/stop_requested.flag / data/kill.flag）
- フェイルセーフ設計（API失敗やデータ不足時に例外を全体に波及させない）

セットアップ
------------
前提
- Python 3.10 以上（PEP 604 の型記法（X | Y）等を使用）
- OS によって psutil の一部機能は権限を要する場合があります

依存パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）
- 他、標準ライブラリ

インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- 自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主要な環境変数
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
  - PAPER_FILL_MODE: paper_trading 時の fill 動作（instant | partial | never | reject）（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL など（Settings クラス参照）

ファイル/フラグ
- data/stop_requested.flag: run_monitoring / run_execution がポーリング中に検知して安全に終了するための停止フラグ
- data/kill.flag: KillSwitch により ExecutionEngine 停止を指示するフラグ
- data/execution.pid: ExecutionEngine の PID ファイル（存在チェックでプロセス生存確認を行う）

使い方
------

基本的な起動方法
- 監視ループを起動（Production 用監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - run_monitoring は Settings.env に関係なく本番用 sqlite_path を使用して監視テーブルを初期化します。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（実運用 DB と分離）。
  - 実行中は data/execution.pid に PID を書きます。data/stop_requested.flag による停止要求に対応します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視データが無ければエラーメッセージが表示されます（MonitoringEngine を先に起動してください）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で変更可能。

AI 機能（ニュース NLP / レジーム判定）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して指定日用のニュースセンチメントを ai_scores テーブルへ書き込みます。
  - api_key を渡すか環境変数 OPENAI_API_KEY を設定してください。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 差分とマクロニュースの LLM センチメントを合成して market_regime テーブルへ保存します。

監視／アラート
- AlertManager（LINE Push）により一方向アラートを送信可能。LINE の channel access token / user id を設定してください。
- KillSwitch によりリスクトリガー（ドローダウンやポジション上限超過）で data/kill.flag を書き込み、ExecutionEngine を停止できます。

起動時のプロセス優先度
- run_monitoring/run_execution は起動直後に set_process_priority("high") を試行します（psutil を使用）。権限不足等は警告ログを出してスキップします。

ディレクトリ構成
----------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                    — 環境変数/.env 読み込み・Settings
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py                 — raw_news → OpenAI → ai_scores
    - regime_detector.py         — マクロ + MA200 によるレジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite テーブル定義 & 永続層 API
    - system_monitor.py          — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py           — 注文滞留・約定価格異常の検出
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 書き込みユーティリティ
    - alert_manager.py           — LINE Push 通知
    - monitoring_engine.py       — 複数 Monitor を束ねるループ処理
    - streamlit_dashboard.py     — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository 等)
  - portfolio/
    - portfolio_builder.py        — 候補選定・等重/スコア重み
    - position_sizing.py          — 発注株数計算・ラウンド・aggregate cap
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py         — momentum/value/volatility 等の計算（DuckDB）
    - feature_exploration.py     — 将来リターン・IC・統計サマリ
  - utils/
    - __init__.py
    - process_priority.py        — set_process_priority / set_cpu_affinity

注意事項 / 運用ヒント
--------------------
- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等でテーブル作成と簡単なカラム追加を行います。既存 DB に対する互換性保持を配慮した処理が含まれます。
- Paper Trading: paper_trading 環境は本番 DB と分離されます。Settings.is_paper を利用してパスを切り替えます。
- OpenAI 呼び出し: rate limit / ネットワーク障害に対するリトライ（指数バックオフ）を実装していますが、API キーや料金設定には注意してください。
- ログ: logging.basicConfig(level=logging.INFO) がデフォルトで使用されます。LOG_LEVEL 環境変数で調整可能です。
- 停止フラグ: data/stop_requested.flag を作成すると run_monitoring/run_execution のループを安全に抜けます。kill.flag は KillSwitch が書き込み、ExecutionEngine に停止シグナルを送ります。

貢献 / テスト
--------------
- 各モジュールはできるだけ副作用を抑えた純粋関数や明確な I/O（DB 接続や API クライアント）を受け取る設計になっています。ユニットテストは外部 I/O をモックして実行できます。
- AI 周りや外部 API 呼び出しには patch / monkeypatch を使ってテスト可能です（コード内にテスト差し替えフックあり）。

ライセンス
---------
リポジトリに明示されたライセンスが無い場合は運用ルールに従ってください。

---

必要であれば、README にインストール用の requirements.txt 例、.env.example のサンプル、よくあるトラブルシューティング（権限エラー、psutil の動作、OpenAI API のエラー対処）を追加します。どのトピックを優先して追記しますか？