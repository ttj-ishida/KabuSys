# KabuSys

日本株自動売買システムのモジュール群。ポートフォリオ構築、発注エンジン、監視・アラート、リサーチ（ファクター計算）や AI を用いたニュース解析などを含みます。

この README はコードベース（src/kabusys 以下）の主要機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール化されたシステムです。主な責務は次の通りです。

- 戦略 / ポートフォリオ構築（銘柄選定、重み付け、株数決定）
- 注文管理と ExecutionEngine による発注（本番 / Paper Trading 切替）
- 監視（システム稼働状況、注文滞留・約定異常、リスク監視）
- アラート（LINE Push）
- DuckDB/SQLite を使った市場データ処理、ファクター計算、研究用ユーティリティ
- OpenAI を使ったニュースの NLP スコアリング、および市場レジーム判定
- Paper Trading の検証レポート生成ツール、Streamlit ダッシュボード

設計方針としては「テストしやすい純粋関数」「DBは読み書き層分離」「ルックアヘッドバイアス回避」「フェイルセーフ（外部 API 失敗時は継続）」などが採用されています。

---

## 主な機能一覧

- ポートフォリオ構築
  - 銘柄候補選別（score / rank）
  - 等金額・スコア加重の重み計算
  - セクター制限適用、レジームに基づく投下率調整
  - 株数決定（リスクベース、等配分、スコアベース）、単元株丸め、aggregate cap

- Execution / 発注
  - OrderManager、OrderRepository、Reconciler による注文状態管理と起動時のリコンシリエーション
  - 本番 / Paper Trading 切替（Paper では専用 SQLite を使用）

- 監視
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度の監視
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボードの更新
  - MonitoringDB: SQLite を用いた監視ログの永続化（system_status / trade_logs / positions / risk_logs / dashboard）

- アラート
  - AlertManager: LINE Messaging API による一方向プッシュ（クールダウン管理）

- AI / NLP
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを計算し ai_scores に保存
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して market_regime を判定し保存

- リサーチ
  - factor_research: Momentum / Volatility / Value 等のファクター算出（DuckDB 上で SQL と Python の組合せ）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）や統計サマリ

- 運用ツール
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor 単体ポーリング起動スクリプト
  - tools.paper_verification_report: Paper Trading 検証レポート生成
  - streamlit_dashboard.py: Streamlit による監視ダッシュボード（read-only 接続）

---

## 前提 / 必要環境

- Python 3.9+
- 必要となる主要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite は標準で動作
- ネットワーク接続（LINE API / OpenAI を使用する場合）

実際のインストールはプロジェクトに requirements.txt があればそれを使ってください。例:

pip install -r requirements.txt

requirements.txt がない場合は最低限次をインストールしてください（環境に合わせてバージョン指定を行ってください）:

pip install duckdb psutil requests openai streamlit

---

## 環境変数（主なもの）

Settings クラスで参照される環境変数（.env をプロジェクトルートに置くと自動読み込みされます）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- KABUSYS_ENV - 実行環境: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN - J-Quants API（必須）
- KABU_API_PASSWORD - kabuステーション API（必須）
- KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY - OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN - LINE Push 用トークン（アラート送信）
- LINE_USER_ID - LINE Push の送信先ユーザ ID
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE - Paper Trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL - ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL - run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH - ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH - kill flag のパス（デフォルト: data/kill.flag）

.env / .env.local の読み込み順:
OS 環境 > .env.local（上書き） > .env（未設定のみ）

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークツリーを移動
2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は前節の主要パッケージを個別にインストール）
4. data ディレクトリ作成（DB を置く場所）
   mkdir -p data
5. 環境変数を .env として作成（.env.example を参考に必要な値を設定）
6. 初期 DB（必要なら）：
   - DuckDB は初回アクセス時にファイルが作られます
   - monitoring 用 SQLite は run_* 起動時に init_monitoring_db によりテーブルが作成されます

---

## 使い方（主なコマンド）

注意: すべてプロジェクトルートから実行することを想定しています。

- 監視ループ（SystemMonitor 単体、MONITOR_POLL_INTERVAL で間隔指定可能）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します（same path がコードで参照されます）。

- ExecutionEngine 起動（発注エンジン）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を用い、data/paper_trading.db に記録されます（本番 DB と分離）。
  - 起動中に停止させたい場合は data/stop_requested.flag を作成するとエンジン停止処理を開始します。
  - ExecutionEngine は起動時に kill.flag のクリーンアップなどの設定を参照します（Settings.kill_flag_clear_on_start）。

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション `--db PATH` で DB パスを指定可能（デフォルト: data/paper_trading.db）。

- Streamlit ダッシュボード（監視データの可視化）:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の monitoring.db に対して read-only モードで接続します。MonitoringEngine を先に動かしてデータを作成してください。

- AI/Regime / News スコアリング（コード API）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  どちらも DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、OpenAI API キーを引数か環境変数 OPENAI_API_KEY で解決します。

---

## 運用上の注意

- run_monitoring / run_execution は process priority を High に設定しようとします（psutil を使用）。権限によっては警告が出て無視されます。
- Monitoring は実行環境にかかわらず（KABUSYS_ENV に依らず）デフォルト監視用 sqlite_path を使う設計です（run_monitoring の docstring 参照）。
- kill.flag / stop_requested.flag / execution.pid 等のフラグファイルによりプロセス制御を行います。これらは data/ 以下に置かれます。
- OpenAI 呼び出しはネットワークエラー・429・5xx 等に対してエクスポネンシャルバックオフでリトライする設計ですが、外部 API のレートやコストに留意してください。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

---

## 主要なディレクトリ構成（src/kabusys）

以下は本リポジトリ内の主要モジュールと役割（抜粋）です。

- kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートジェネレータ
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・aggregate cap ロジック
    - risk_adjustment.py       — セクター制限・レジーム乗数
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（テーブル定義・CRUD）
    - system_monitor.py        — システム監視（CPU / プロセス / データ鮮度）
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン / ポジション数監視
    - kill_switch.py           — kill.flag 書き込みユーティリティ
    - alert_manager.py         — LINE Push 通知
    - monitoring_engine.py     — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py        — OrderStateMachine の外向き API
    - reconciler.py           — 起動時の自動復旧（注文 / ポジション照合作業）
    - ...（broker_factory, execution_engine 等はコードベースに存在）
  - research/
    - factor_research.py      — モメンタム / ボラ / バリュー等のファクター計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py             — raw_news を LLM でスコアリングして ai_scores に書込
    - regime_detector.py      — マクロ + MA200 で市場レジーム判定
  - utils/
    - process_priority.py     — プラットフォーム依存を吸収した優先度 / CPU affinity 設定ユーティリティ
  - data/                      — デフォルトで使用される DB/フラグファイル格納先（リポジトリ外で作成）

---

## 監視 DB（monitoring.db）テーブル（概要）

init_monitoring_db() により作成される主なテーブル:

- system_status: CPU / memory / disk / process_ok のタイムスタンプ付きログ
- trade_logs: 注文イベントログ（Created / Sent / Filled 等）、latency_ms 列あり
- positions: 現在の保有（code を主キー）
- risk_logs: リスク関連の発生イベント（DRAWDOWN_ALERT 等）
- dashboard: 集計（単一行 id=1） — portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

各テーブルはマイグレーション処理（列追加）が初回起動時に行われます（冪等）。

---

## 開発 / テストに関するヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。CI やテストで自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- OpenAI 呼び出し部分は内部で小さなラッパー関数を使っているため、ユニットテストではモック差し替えがしやすくなっています（例: unittest.mock.patch で _call_openai_api を差替え）。
- DuckDB の分析系関数は SQL を主体に設計されており、duckdb.DuckDBPyConnection を渡すだけで呼べます。研究・検証環境ではローカルの DuckDB ファイルを用いて高速に検証できます。

---

## 参考コマンドまとめ（例）

- 監視開始（60秒間隔）:
  python -m kabusys.run_monitoring

- 発注エンジン起動（Paper/Live は KABUSYS_ENV に依存）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースから読み取れる挙動・設定をまとめたものです。より詳しい実装仕様や運用手順（デプロイ、監視設定、障害対応など）は別途運用ドキュメントにまとめることを推奨します。必要があれば各モジュールの API ドキュメントやユースケース別の手順書も作成します。