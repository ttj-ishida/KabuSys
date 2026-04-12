README
======

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を行うためのモジュール群です。このリポジトリには以下の主要コンポーネントを含みます。

- 実行エンジン（ExecutionEngine）: ブローカーに発注し、リスク管理・注文管理を行う
- 監視（Monitoring）: システム状態・注文滞留・ドローダウン等を定期的にチェックしてログ・アラート・停止フラグを管理
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ算出などの純粋関数群
- リサーチ（Research）: ファクター計算、将来リターン・IC 計算など
- AI ユーティリティ（AI）: ニュースのセンチメントスコアリング、レジーム判定（OpenAI を利用）
- ツール: Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボード 等
- 共通設定・ユーティリティ（config, utils）

主な設計方針:
- DuckDB / SQLite を用いたデータ永続化
- 環境変数 / .env による設定管理（自動ロード）
- 本番/ペーパーを明確に分離（KABUSYS_ENV）
- LLM 呼び出しはリトライ/フォールバック等のフェイルセーフを実装

機能一覧
--------
主な機能（抜粋）:

- Execution
  - ブローカー抽象（BrokerClientFactory）により本番/モックを切替可能
  - OrderManager / OrderRepository による状態遷移・永続化
  - Reconciler による再起動時の状態同期（注文・ポジション照合）
  - RiskManager による発注前チェック

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在 / データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格チェック
  - RiskMonitor: ドローダウン・ポジション上限チェック
  - KillSwitch: 条件に応じて data/kill.flag を書いて ExecutionEngine を停止
  - AlertManager: LINE Messaging API 経由の通知（クールダウン管理）
  - Streamlit ダッシュボードで監視データを可視化

- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC・統計サマリー計算
  - 候補選定、等重・スコア加重、セクター上限、リスクベースのポジションサイズ算出

- AI（OpenAI）
  - news_nlp: ニュース記事を銘柄別に集約して LLM に投げ、銘柄スコアを ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースを組み合わせて日次レジーム判定

セットアップ手順
----------------
前提
- Python 3.9 以上を推奨（typing/標準ライブラリ機能利用）
- システムに DuckDB, SQLite がインストール済みである必要はなく、Python のパッケージで動作します

1. リポジトリをクローン
   git clone <このリポジトリ>
   cd <repo>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   以下は主に必要となるパッケージの例です。requirements.txt がある場合はそれを使用してください。
   pip install duckdb psutil requests openai streamlit

   ※ OpenAI の最新 SDK 名・バージョンに注意してください（このコードは OpenAI Python クライアントを想定）。

4. 環境変数（.env）の準備
   プロジェクトルートに .env または .env.local を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   主な環境変数:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須の箇所で参照）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
   - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定

   例 (.env):
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

5. データディレクトリの作成
   mkdir -p data

使い方
------
起動スクリプト

- 監視ループを起動
  python -m kabusys.run_monitoring

  挙動:
  - Settings から設定を読み込み、Monitoring 用 SQLite（settings.sqlite_path）を使用して DB 初期化を行う（init_monitoring_db）。
  - DuckDB を接続（settings.duckdb_path）。
  - SystemMonitor のポーリングループを開始。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）。
  - 起動時にプロセス優先度を "high" に設定しようとする（psutil 必須、失敗時は警告）。

  注意:
  - Monitoring は KABUSYS_ENV にかかわらず監視用 sqlite_path（本番パス）を使います。

- 実行エンジンを起動（売買実行）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、settings.paper_sqlite_path（data/paper_trading.db）を DB に使用して本番 DB と分離。
  - BrokerClientFactory に従いブローカークライアントを生成し、ExecutionEngine を起動。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  --from, --to: 期間（YYYY-MM-DD）
  --db: SQLite DB パス（環境変数 PAPER_TRADING_SQLITE_PATH で代替可）
  出力: 標準出力にレポート（稼働率、注文成功率、P95 レイテンシ等）

- Streamlit ダッシュボード（監視）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  （--db で監視 DB パスを指定。デフォルトは data/monitoring.db）
  ダッシュボードは監視 DB を read-only で開き、Positions / Orders / System / Overview を表示します。

主要設定（要点）
- KABUSYS_ENV: development / paper_trading / live。is_paper/is_live/prod 判定に使用。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。1 未満の値は無視されデフォルトにフォールバック。
- PAPER_FILL_MODE: ペーパー約定モード（instant, partial, never, reject）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（kill/プロセス存在の判定に利用）
- KILL_FLAG_PATH: KillSwitch が書き込む停止フラグ（ExecutionEngine はこのファイルを検知して停止する）

依存関係（主なもの）
- duckdb
- psutil
- requests
- openai (OpenAI Python SDK)
- streamlit (ダッシュボード利用時)

ディレクトリ構成
----------------
（抜粋） src/kabusys 配下:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 自動ロード・Settings
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 監視 DB 初期化 / CRUD ラッパ
    - system_monitor.py            — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常監視
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag 制御
    - alert_manager.py             — LINE Push 通知
    - monitoring_engine.py         — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - (OrderManager, Reconciler, ExecutionEngine, broker 等)  — 発注周りの実装
  - portfolio/
    - portfolio_builder.py         — 候補選定・等重/スコア重み
    - position_sizing.py           — 株数決定・スケーリング
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py       — forward returns / IC / summary
  - ai/
    - news_nlp.py                  — ニュースを LLM でスコアリング（ai_scores へ書込）
    - regime_detector.py           — MA + マクロニュースでレジーム判定
  - data/                           — 既定では data/kabusys.duckdb / data/monitoring.db などを使用
  - utils/
    - process_priority.py          — プロセス優先度・CPU affinity 設定ユーティリティ

開発者向けメモ
--------------
- Settings は起動時にプロジェクトルート（.git / pyproject.toml）を自動検索し .env を読み込みます。テスト時に自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring_db.init_monitoring_db は冪等に複数テーブル・インデックスを作成し、既存スキーマ不足カラム（peak_value, latency_ms）へのマイグレーションも行います。
- AI 周り（news_nlp, regime_detector）は OpenAI API を利用します。API キー未設定時は ValueError になります。API 呼び出しはリトライ・部分失敗耐性が実装されています。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使い、本番 DB と完全分離します。

トラブルシューティング
---------------------
- psutil によるプロセス優先度設定でアクセス拒否が発生することがあります。権限不足でも挙動は継続します（警告ログ）。
- Streamlit から DB を開く際は read-only URI を使用しており、DB が存在しないと起動に失敗します（MonitoringEngine を先に起動してください）。
- OpenAI 呼び出しで頻繁に 429 が出る場合、API レート・バッチサイズや再試行待機を調整してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

お問い合わせ
------------
- 実装や拡張に関する質問があればリポジトリの issue を作成してください。

以上。必要であれば README にサンプル .env.example や起動例の簡易スクリプトを追加できます。どの情報を追記しますか？