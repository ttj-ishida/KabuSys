KabuSys — 日本株自動売買プラットフォーム（簡易 README）
概要
- KabuSys は日本株向けの自動売買・リサーチ・監視機能を備えたライブラリ群です。
- DuckDB / SQLite を用いたローカルデータ処理、kabuステーション等のブローカー API 経由の発注、LLM を用いたニュース（マクロ／銘柄）センチメント評価、監視アラート（LINE）・ダッシュボードなどを提供します。
- 設計方針は「DB 参照の明確化」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時のフォールバック）」です。

主な機能一覧
- 設定管理
  - .env/.env.local または環境変数から設定を自動読み込み（プロジェクトルート検出）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須変数未設定時は ValueError を送出するユーティリティ（kabusys.config.Settings）。
- ポートフォリオ構築（純粋関数）
  - 候補選定（スコア降順、タイブレーク含む）
  - 等金額・スコア加重配分
  - セクター集中制限の適用
  - レジームに応じた投下資金乗数計算
  - 株数決定（リスクベース、等配分、スコア配分）、単元丸め、aggregate cap 調整
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受け取る）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI（LLM）連携
  - ニュース記事の銘柄別センチメントスコア算出（OpenAI API を利用、gpt-4o-mini 想定）
  - マクロニュースと ETF（1321）の MA を組み合わせた市場レジーム判定（bull/neutral/bear）
  - レート制限・リトライ・レスポンス検証を備えた堅牢な実装
- 実行系（Execution）
  - Signal Queue ベースの発注エンジン（ExecutionEngine）
  - OrderManager（状態遷移・DB 永続化・ブローカー呼出し）
  - Reconciler（再起動時の状態回復）
  - Broker API 抽象インターフェース（Protocol）とデータモデル
- 監視（Monitoring）
  - MonitoringDB（SQLite）による永続化スキーマ + 初期化ユーティリティ
  - System / Trade / Risk Monitor（ドローダウン監視、滞留注文・約定異常検出）
  - KillSwitch（flag ファイルで ExecutionEngine を停止）
  - AlertManager（LINE push）
  - Streamlit ベースの監視ダッシュボード（read-only 接続）

セットアップ手順（開発向け）
1. リポジトリをクローン / コピー
   - プロジェクトルートに .git または pyproject.toml があると自動で .env を読み込みます。

2. Python 環境（仮想環境）を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（代表例）
   - pip install duckdb openai psutil requests streamlit
   - （プロジェクトに requirements.txt/pyproject.toml がある場合はそちらを利用してください）

4. .env の準備
   - プロジェクトルートに .env（と必要なら .env.local）を置くと自動読み込みされます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH など
- KABUSYS_ENV, LOG_LEVEL 等のシステム設定

使い方（サンプル）
- 設定取得（例）
  from kabusys.config import settings
  token = settings.jquants_refresh_token

- MonitoringDB 初期化
  import sqlite3
  from kabusys.monitoring import init_monitoring_db
  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)

- Streamlit ダッシュボード起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ニュース NLP スコア付与（DuckDB 接続を渡す）
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, date(2026, 3, 20), api_key="sk-...")

- 市場レジーム算出
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")

- ExecutionEngine の実行（概念）
  - ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続と EngineConfig が必要。
  - 実際の run_session() 呼び出しは本番のブローカークライアント実装を組み合わせて行います（テストではモックを利用）。

設計上の注意点 / 動作ポリシー
- DuckDB / SQLite によるデータ参照は、本番口座 API には依存しない関数群（リサーチ・ファクター計算）は外部 API を呼ばない設計です。
- LLM 呼び出しでは JSON モード＋検証を行い、部分失敗でも他銘柄データを保持するよう設計されています。API エラーは適切にリトライまたはフォールバック値で継続します。
- 自動ロードされる .env の優先順位は OS 環境変数 > .env.local > .env です。プロジェクトルート検出は .git または pyproject.toml を用いて行われます。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — 環境変数 / 設定管理
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定・重み計算
    - risk_adjustment.py       — セクター上限・レジーム乗数
    - position_sizing.py       — 発注株数計算
  - research/
    - __init__.py
    - factor_research.py       — momentum/value/volatility 等
    - feature_exploration.py   — forward returns / IC / summary
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（OpenAI 経由）
    - regime_detector.py       — 市場レジーム判定（MA + マクロ LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite スキーマ & MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py            — Broker API のデータモデル / Protocol / 例外
    - order_manager.py
    - reconciler.py
    - execution_engine.py
    - （その他 OrderRepository 等は別ファイル群）
  - その他モジュール:
    - monitoring/alert_manager.py（LINE 通知）
    - research zscore 正規化など（data.stats 参照）

トラブルシューティング（よくある点）
- .env が読み込まれない
  - プロジェクトルートを .git または pyproject.toml で検出します。ルートにこれらが無い場合は自動ロードがスキップされます。自動ロードを明示的に無効にしている場合（KABUSYS_DISABLE_AUTO_ENV_LOAD）も確認してください。
- OpenAI API エラー
  - API キーが未設定だと ValueError が発生します。rate limit 等は内部でリトライが働きますが、最終的に該当チャンクはスキップされうる点に注意してください。
- kill.flag / PID
  - ExecutionEngine は PID ファイルを書き、kill.flag が存在する場合は挙動（停止 or 起動拒否）が設定に依存します（Settings.kill_flag_clear_on_start）。

貢献
- バグ報告・機能提案は Issue を立ててください。テストやモック実装を含む PR は歓迎します。

以上。必要であれば .env.example の例、実行スニペット（ExecutionEngine を使った具体的な起動例）や依存関係の pin リスト（requirements.txt）を追記します。どの情報を追加しますか？