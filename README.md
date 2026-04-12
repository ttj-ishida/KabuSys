KabuSys — 日本株自動売買システム
========

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python コードベースです。本リポジトリは以下の主要機能を含みます。

- 発注・約定管理（ExecutionEngine / OrderManager / Reconciler）
- Portfolio 構築（シグナル選定・ウェイト算出・ポジションサイジング）
- リサーチ（ファクター計算・特徴量探索）
- AI 支援（ニュースの NLP センチメント、レジーム判定 via OpenAI）
- 監視（System/Trade/Risk のポーリング、監視 DB、Streamlit ダッシュボード）
- Paper Trading 用機能（本番 DB と分離された専用 DB に記録）
- 各種ユーティリティ（プロセス優先度設定、.env ローダー 等）

主な特徴
-------
- モジュール化された設計により、個別コンポーネント（execution / monitoring / research / ai / portfolio）を単体で利用可能
- DuckDB を使った分析・ファクター計算（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとマクロセンチメントの統合（フェイルセーフ・リトライ実装）
- SQLite（monitoring.db / paper_trading.db）を用いた監視ログ永続化、スキーマの冪等初期化・簡易マイグレーション対応
- Streamlit による監視ダッシュボード（読み取り専用で起動可能）
- Paper Trading と Live の DB 分離（KABUSYS_ENV による挙動切替）

動作要件（概略）
----------------
- Python 3.9+（typing / dataclass 等を利用）
- 必要なライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite は標準ライブラリで利用
- ネットワーク接続（OpenAI API / LINE API を使用する場合）

インストール（例）
-----------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール（最低限の例）
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトが requirements.txt を提供している場合は pip install -r requirements.txt を推奨）

設定（環境変数 / .env）
---------------------
本パッケージは .env ファイルまたは環境変数を参照します。自動ロードはプロジェクトルート（.git または pyproject.toml のある場所）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（抜粋）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")。デフォルト: development
  - paper_trading の場合、Execution は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使用する場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の fill モード ("instant" | "partial" | "never" | "reject")（デフォルト: "instant"）
- PID_FILE_PATH / KILL_FLAG_PATH: ExecutionEngine 用の PID / kill flag ファイルパス
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト: 60）

セットアップ手順（簡易）
---------------------
1. 必要パッケージをインストール
2. data/ ディレクトリを作成（必要に応じて）
3. .env をプロジェクトルートに作成し、必要な環境変数を記載（.env.example を参考に）
4. DuckDB / SQLite に必要なテーブルを準備（多くのモジュールは初期化関数でテーブル作成を行います）

利用方法（スクリプト・モジュール）
-------------------------------

- 監視ポーリングを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 を設定するとポーリング間隔を変更できます（秒）。
  - このスクリプトはプロセス優先度を "high" に設定し、MonitoringDB（SQLITE_PATH）を初期化して SystemMonitor のポーリングを継続します。

- 実取引（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録します。
  - 起動時にプロセス優先度を "high" に設定します。

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（デフォルト: data/paper_trading.db）。

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開き、Overview / Positions / Orders / System タブを表示します。

- AI モジュール（プログラムから）
  - 例: ニュースセンチメントを生成する
    - from kabusys.ai import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=datetime.date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

開発者向けメモ
--------------
- 設定管理:
  - src/kabusys/config.py が .env のパースおよび環境変数の取得ロジックを提供します。自動ロード順は OS 環境変数 > .env.local > .env（保護された OS 環境変数は上書きされません）。
- 監視 DB:
  - init_monitoring_db(conn) はテーブルの作成および簡易マイグレーション（カラム追加）を実行します。MonitoringDB は書込/読込 API を提供します。
- プロセス優先度:
  - src/kabusys/utils/process_priority.py で Windows / POSIX を吸収して優先度や CPU affinity を設定します（アクセス拒否等は警告でスキップ）。
- AI 呼び出し:
  - news_nlp / regime_detector は OpenAI を使用。API 呼び出しはリトライやサニタイズ、レスポンス検証を内包しているため安全性に配慮されています。
- Paper vs Live:
  - Execution 起動時は KABUSYS_ENV によって paper_trading 用 DB を使うかどうかを切り替えますが、監視側（run_monitoring）は常に本番 sqlite_path を参照します（設計上の明示的挙動）。

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env ローダー / Settings クラス
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - run_monitoring.py — SystemMonitor ポーリングスクリプト
    - monitoring_db.py — SQLite スキーマ初期化 + MonitoringDB ラッパー
    - system_monitor.py — CPU / メモリ / データ鮮度 / PID チェック
    - trade_monitor.py — 注文滞留・約定異常の検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書込みによる Execution 停止トリガ
    - alert_manager.py — LINE Push 通知（クールダウン付き）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - run_execution.py — ExecutionEngine 起動スクリプト
    - order_manager.py — 発注ワークフロー（create/send/sync）
    - reconciler.py — 再起動時の自動リコンシリエーション
    - (その他: broker_factory, order_repository, order_record, risk_manager 等)
  - portfolio/
    - portfolio_builder.py — 候補選定・等/スコア配分
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - position_sizing.py — 株数決定、集計キャップ
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — forward returns / IC / factor summary 等
  - ai/
    - news_nlp.py — raw_news を LLM で集約評価 → ai_scores へ書込
    - regime_detector.py — ma200 + マクロ NLP を合成して market_regime を更新
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

注意事項 / 運用上のポイント
---------------------------
- 機密情報（API キー等）は .env または OS 環境変数で管理してください。リポジトリに直接書き込まないよう注意してください。
- Paper Trading は本番 DB と分離されますが、運用時はファイルパスの指定ミスに注意してください（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）。
- OpenAI を使う処理は API コストが発生します。バッチサイズやトークン制限に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒）。不正値はデフォルト 60 秒にフォールバックします。
- Streamlit ダッシュボードは読み取り専用で起動することを想定しています（データベースを ?mode=ro で開く）。

付録: よく使うコマンド例
-----------------------
- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動（Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

追加で README に盛り込みたい情報（例）
- requirements.txt（具体的パッケージとバージョン）
- .env.example（推奨設定のテンプレート）
- 開発用テスト手順 / CI 設定
- ライセンス表記

必要であれば上記の補助ファイルやより詳細なセットアップ手順（Docker / systemd ユニット 例）を作成します。どの部分を拡張しますか？