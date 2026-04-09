KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視ユーティリティ群を含む Python ライブラリです。本コードベースは以下の主要機能をモジュール単位で提供します。

- ポートフォリオ構築（銘柄選定・配分・ポジションサイズ計算）
- リスク調整（セクター上限・市場レジームに応じた乗数）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアリング）
- 市場レジーム判定（ETF、マクロニュースを組み合わせた判定）
- 発注エンジン周り（注文管理・ブローカー API インターフェース・リコンシリエーション）
- 監視（システム状態・注文状態・リスク監視）、および Streamlit ダッシュボード

主な機能
--------
- 環境変数 / .env の自動読み込み（プロジェクトルート検出）
- ポートフォリオ構築用の純粋関数群（候補選定・等重/スコア重み・リスクベースの株数決定）
- DuckDB を前提としたファクター / 将来リターン計算（外部 API へはアクセスしない設計）
- OpenAI（gpt-4o-mini）を使ったニュース・マクロセンチメント評価（フェイルセーフ、リトライ実装）
- 発注フローの堅牢化（2相コミット的な永続化、再同期／リコンシリエーション機能）
- 監視 DB（SQLite）層と MonitoringEngine、Streamlit ダッシュボード、LINE 通知によるアラート

セットアップ
-----------

※ 以下は一般的な手順例です。実際の環境に合わせて Python バージョンや依存パッケージを調整してください。

1. Python を用意
   - 推奨: Python 3.10+（コードは typing / match 等を使っており modern な機能を想定）

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的な必要パッケージ:
     - duckdb
     - openai
     - requests
     - psutil
     - streamlit
   - 例:
     pip install duckdb openai requests psutil streamlit

   （実プロジェクトでは requirements.txt / pyproject.toml を参照してください）

4. プロジェクトの .env 準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くと自動でロードされます。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env（代表的な環境変数）
-----------------------
以下は本リポジトリで参照される代表的な環境変数の一覧（必要に応じて .env に設定してください）。

- JQUANTS_REFRESH_TOKEN：J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD：kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL：kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY：OpenAI API キー（AI モジュールを使う場合）
- LINE_CHANNEL_ACCESS_TOKEN：LINE 通知用トークン（任意）
- LINE_USER_ID：LINE 通知先 user id（任意）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE：Paper Trading の挙動（instant/partial/never/reject）
- PID_FILE_PATH：実行 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH：Kill フラグファイル（デフォルト: data/kill.flag）
- KABUSYS_ENV：環境 (development/paper_trading/live)
- LOG_LEVEL：ログレベル（DEBUG/INFO/...）

簡易 .env.example（参考）
-------------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxxx
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_FILL_MODE=instant
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KABUSYS_ENV=development
LOG_LEVEL=INFO

初期 DB 作成（監視用）
---------------------
監視用 SQLite スキーマを作成するための例:

python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); conn.close()"

Streamlit ダッシュボード
-----------------------
データベースが作成されている前提で起動:

streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

使い方（主要 API / 実行例）
-------------------------

- 環境設定取得
  from kabusys.config import settings
  settings.jquants_refresh_token
  settings.duckdb_path
  （.env または環境変数から読み込まれます）

- ニュース NLP（スコア付与）
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  # target_date は datetime.date 型（例: date(2026,3,20)）
  score_news(conn, target_date, api_key="sk-...")

  ※ API キーを引数で与えない場合は OPENAI_API_KEY 環境変数を使用します。
  ※ 処理はフェイルセーフ設計：API エラー時はスキップ・ゼロフォールバックします。

- レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="sk-...")

- ポートフォリオ構築ユーティリティ（純粋関数）
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  shares = calc_position_sizes(weights, candidates, portfolio_value=..., available_cash=..., ...)

- 監視関連
  - MonitoringDB: 監視用 SQLite への読み書きラッパー
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine: 各種監視タスクの実行と統合
  - AlertManager: LINE push による通知（チャンネル設定が必要）

- ExecutionEngine（発注セッション）
  ExecutionEngine は broker（BrokerAPIProtocol 実装）・OrderRepository 等を注入してセッションを実行します。起動時にリコンシリエーションを行い、kill.flag / PID 管理・WebSocket プッシュのドレインなどを実行します。実行例（実際の broker 実装が必要）:

  engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=...))
  engine.run_session()

主なモジュールとファイル構成
--------------------------
src/kabusys/
- __init__.py               — パッケージメタ情報（version 等）
- config.py                 — 環境変数 / .env 自動読み込み・Settings（アプリ設定）
- portfolio/
  - portfolio_builder.py    — 候補選定・等重/スコア重み計算
  - risk_adjustment.py      — セクター上限・レジーム乗数
  - position_sizing.py      — 株数決定・キャッシュ制約・lot 整数化
  - __init__.py
- research/
  - factor_research.py      — モメンタム/ボラ/バリュー等の DuckDB ベース計算
  - feature_exploration.py  — 将来リターン・IC・統計サマリー等の解析ユーティリティ
  - __init__.py
- ai/
  - news_nlp.py             — ニュース記事を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py      — ETF + マクロ記事を組み合わせたレジーム判定（DB 書込）
  - __init__.py
- monitoring/
  - monitoring_db.py        — SQLite スキーマ定義 + MonitoringDB クラス
  - system_monitor.py       — システム状態・データ鮮度チェック
  - trade_monitor.py        — 注文滞留・約定異常チェック
  - risk_monitor.py         — ドローダウン・ポジション上限チェック
  - kill_switch.py          — フラグファイルによる停止制御
  - alert_manager.py        — LINE による通知
  - monitoring_engine.py    — 各 Monitor を束ねてポーリング
  - streamlit_dashboard.py  — Streamlit ダッシュボード（dev 用）
  - __init__.py
- execution/
  - broker_api.py           — Broker API のデータモデル・Protocol・例外
  - order_manager.py        — Order State Machine 外向け API（create/send/sync/cancel）
  - reconciler.py           — 起動時リコンシリエーション（注文・ポジション突合）
  - execution_engine.py     — Signal Queue Pull 型のセッション実行ロジック
  - (他の発注 DB / repository / record 等は別ファイルにある想定)
- monitoring/  (上記)
- その他（data パッケージや execution.order_repository 等は別ファイルで実装される想定）

設計/運用上の注意
----------------
- DuckDB / SQLite を使った設計は本番でも同一コードを流用できるよう配慮していますが、実際のブローカー・API 実装や運用手順については十分な検証・フェイルオーバー設計を行ってください。
- OpenAI 呼び出し部分は外部 API に依存するため、API キーの管理やレート制御、課金面に注意してください。AI 関連処理は失敗時に安全側（スコア 0 やスキップ）で継続する設計です。
- kill.flag / PID ファイルは安全停止・再起動時の重要な制御手段です。運用時はクリアの挙動（KILL_FLAG_CLEAR_ON_START）を理解した上で運用してください。
- 設定は .env / .env.local / OS 環境変数の優先順位で読み込まれます（OS > .env.local > .env）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

開発 / テストのヒント
---------------------
- 自動 .env ロードはパッケージ化後でも __file__ を起点にプロジェクトルートを探すため、CWD 依存が少ない設計です。ユニットテスト時に環境操作を行う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと安定します。
- OpenAI 呼び出し部分（_call_openai_api 等）は内部で関数が分離されており、unittest.mock.patch で差し替えが可能です。レスポンスバリデーションも厳密に行われ、例外を上位に伝播しない箇所が多くフェイルセーフです。
- DuckDB のテーブルスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets など）を用意したローカル DB を使って開発・検証してください。

ライセンス / 貢献
-----------------
本 README ではライセンス情報は含めていません。実際のリポジトリでは LICENSE を参照してください。バグ報告・プルリクエスト歓迎です。コードの各モジュールは比較的小さな責務に分割されているため、テスト追加や機能拡張が行いやすい構成です。

お問い合わせ
------------
不明点・質問があれば README の更新点や該当モジュールの docstring を参照してください。必要であれば具体的なユースケース（例: DuckDB のテーブル例、ブローカー実装のサンプル）を付けた補足ドキュメントを作成できます。