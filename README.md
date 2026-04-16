README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群をまとめた Python パッケージです。本リポジトリは以下の主要機能を持ちます。

- 注文実行エンジン（ExecutionEngine）とその補助コンポーネント（OrderManager / RiskManager / Reconciler 等）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と監視 DB（SQLite）／ダッシュボード
- ポートフォリオ構築ロジック（候補選定・重み計算・ポジションサイジング・リスク調整）
- リサーチ用ファクター計算・特徴量解析（DuckDB を使った計算）
- AI を使ったニュースセンチメント評価・レジーム判定（OpenAI）
- Paper Trading 検証レポート生成ツール・Streamlit ベースの監視ダッシュボード

設計上の特徴：
- DuckDB と SQLite を併用（時系列ファクター計算は DuckDB、監視ログ等は SQLite）
- 実行環境（KABUSYS_ENV）により paper_trading / live / development を切替可能
- 実行プロセスの優先度設定、フラグファイルによる停止・kill シグナルなど運用を考慮した設計

主な機能一覧
-------------
- Execution
  - 注文生成・送信、状態同期、リコンシリエーション（reconciler）
  - RiskManager によるレート制限 / 最大ポジション比率等のリスク管理
  - Paper Trading モード用の完全分離 DB（data/paper_trading.db 等）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視（kill flag 書込み）
  - AlertManager: LINE Messaging API へのプッシュ通知（クールダウン付き）
  - MonitoringDB: monitoring 用 SQLite スキーマの初期化・CRUD（冪等）

- Portfolio
  - 候補選定（score / rank ベース）
  - 重み計算（等金額・スコア加重）
  - セクター上限適用、レジーム乗数
  - 株数決定（リスクベース・配分ベース）、単元株丸め、aggregate cap

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン、IC 計算、統計サマリー・ランク化ユーティリティ

- AI
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に書込
  - regime_detector: ma200 とマクロニュースセンチメントを合成して日次レジーム判定

- Tools
  - paper_verification_report: Paper Trading DB から稼働率・注文成功率・レイテンシ等を集計し判定レポートを出力
  - streamlit_dashboard: monitoring.db を読む Web ダッシュボード（Streamlit）

セットアップ手順
----------------

前提
- Python 3.10+（typing の Union シンタックス等を使用）
- DuckDB, psutil, requests, openai, streamlit 等のパッケージが必要

推奨手順（例）
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（requirements.txt がある想定）
   pip install -r requirements.txt

   手動インストール例:
   pip install duckdb psutil requests openai streamlit

4. 環境変数（.env）を設定
   プロジェクトルートの .env または .env.local に必要キーを配置します。自動読み込み機構により .env が読み込まれます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
   - PAPER_FILL_MODE=instant|partial|never|reject  (Paper Trading の約定挙動)
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - MONITOR_POLL_INTERVAL=60  （監視ループの秒間隔、デフォルト 60）

5. データディレクトリ作成（必要に応じて）
   mkdir -p data

使い方
-------

実行コマンド（代表例）

- 監視ループ（SystemMonitor 単体の起動）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 実行中にプロジェクトルート/data/stop_requested.flag が作成されるとループを終了します。

- ExecutionEngine（注文実行エンジン）起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag があれば起動せず終了します。
  - 実行中に data/stop_requested.flag が作成されると安全に停止します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --db PATH を指定すると PAPER_TRADING_SQLITE_PATH より優先して DB パスを使用します。

- Streamlit 監視ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で読み込み対象の monitoring SQLite DB を指定できます。
  - ダッシュボードは DB を読み取り専用で開きます（URI mode=ro を使用）。

- AI ツール
  - ニューススコア付与（プログラムから呼び出す）
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=None)  # api_key を渡すか OPENAI_API_KEY 環境変数を設定
  - レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)

運用・停止
- run_monitoring / run_execution は flag ファイル（data/stop_requested.flag）を監視しており、ファイルが存在すると安全に停止します。
- KillSwitch による強制停止は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを渡せます（KillSwitch は主に RiskMonitor により書かれます）。

開発・デバッグ
- Settings は config.py を通じて環境変数を取得します。自動的にプロジェクトルートの .env / .env.local を読み込みます（CWD に依存せず __file__ からプロジェクトルートを探索）。
- 各モジュールには単体で動作する関数が用意されているため、REPL / pytest でのユニットテストがしやすい設計です。
- MonitoringDB.init_monitoring_db は冪等的にテーブルを作成し、既存 DB に対する簡単なマイグレーション（カラム追加）も行います。

ディレクトリ構成
----------------
以下は主要ファイル／ディレクトリの一覧と簡単な説明（src/kabusys をルートとした相対パス）。

- src/kabusys/__init__.py
  - パッケージ定義・バージョン

- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス（_env変数の検証・デフォルト）

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- src/kabusys/run_execution.py
  - ExecutionEngine（注文実行）の起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py       — SQLite スキーマ / MonitoringDB（永続化層）
  - system_monitor.py      — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py       — 注文滞留・約定異常監視
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag 書込ユーティリティ
  - alert_manager.py       — LINE push 通知（クールダウン付き）
  - monitoring_engine.py   — 複数モニタを束ねる実行ループ
  - streamlit_dashboard.py — Streamlit ベースの監視 UI

- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory 等
  - 注文状態管理、ブローカー API 抽象化、リコンシリエーション処理

- src/kabusys/portfolio/
  - portfolio_builder.py    — 候補選定・スコアソート
  - position_sizing.py      — 株数計算・aggregate cap
  - risk_adjustment.py      — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py      — momentum / volatility / value の計算（DuckDB）
  - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - __init__.py             — 公開 API（zscore_normalize 等をエクスポート）

- src/kabusys/ai/
  - news_nlp.py             — raw_news を OpenAI で評価して ai_scores に書込
  - regime_detector.py      — ma200 + マクロニュースセンチメントでレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 用の検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/ (推奨)
  - monitoring.db           — SQLite 監視 DB（デフォルト）
  - kabusys.duckdb         — DuckDB ファイル（時系列データ）
  - paper_trading.db       — Paper Trading 用 SQLite（paper_trading 環境時）
  - execution.pid, stop_requested.flag, kill.flag 等の運用フラグファイル

注意事項 / 運用ヒント
--------------------
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して動作します。誤操作による本番データ破壊を防ぎます。
- OpenAI API 呼び出しを行うコードはリトライ・バックオフ・レスポンス検証を実装していますが、API キーと利用制限には注意してください。
- Monitoring 系は監視結果を SQLite に永続化します。運用時は定期的なバックアップを推奨します。
- process priority / cpu affinity の設定は psutil 経由で行います。権限不足時は警告ログを出してスキップします。

貢献 / 開発
------------
- 新機能追加や修正は各モジュールの責務に沿って行ってください。ユニットテストを追加してから PR を送ることを推奨します。
- DuckDB を使った SQL はパフォーマンス・可読性を重視して書かれています。大きな変更を行う場合はクエリの実行計画やインデックス影響を確認してください。

ライセンス
----------
（ここにプロジェクトのライセンス情報を記載してください）

以上。必要であれば README にサンプル .env.example、requirements.txt の候補、あるいは起動時のログ例やトラブルシュート項目を追記します。どの情報を追加しますか？