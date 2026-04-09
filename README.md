KabuSys — 日本株自動売買フレームワーク
====================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視を目的とした Python ライブラリ群です。  
主要機能は「ファクター計算（研究）」「ポートフォリオ構築」「ポジションサイズ計算」「監視・アラート」「LLM を用いたニュースセンチメント／レジーム判定」「発注エンジン（ExecutionEngine）」「起動時リコンシリエーション」等です。  
モジュールはできるだけ副作用を持たない純粋関数群と、DB／ブローカー接続を受け取る実行層に分かれています。

主な特徴
--------
- 環境変数 / .env 自動読み込み（.env, .env.local、OS環境変数優先）
- DuckDB ベースの時系列データ処理（prices_daily / raw_financials などを前提）
- ファクター計算（Momentum / Volatility / Value 等）
- ポートフォリオ構築（候補選定、等重／スコア重み、リスク制約、単元丸め）
- ポジションサイズ計算（risk-based / equal / score）
- OpenAI を使ったニュースセンチメント（ai.score_news）・レジーム判定（ai.score_regime）
- 監視用 SQLite（MonitoringDB）＋ Streamlit ダッシュボード
- ExecutionEngine（信号処理、ブローカー同期、WebSocket push ドレイン、Kill Switch）
- 再起動時の注文・ポジションリコンシリエーション（Reconciler）

動作環境／前提
--------------
- Python 3.10+
  - 型注釈に PEP 604 の X | Y を使用しているため 3.10 以上を推奨します
- 必須パッケージ（最低限）
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit（ダッシュボード使用時）
- DB ファイル（デフォルト）
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db

セットアップ
-----------
1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb openai requests psutil streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数の設定（.env）
   リポジトリルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   代表的な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  # development | paper_trading | live
     - LOG_LEVEL=INFO

   .env の読み込み挙動:
     - 既定: OS 環境変数 > .env.local > .env
     - 自動読み込みを抑止したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

使い方（主要ユースケース）
------------------------

1) 設定値の取得
   Python 内で環境設定へアクセスできます。
   例:
     from kabusys.config import settings
     token = settings.jquants_refresh_token
     duckdb_path = settings.duckdb_path

2) DuckDB に接続してファクター計算（例：モメンタム）
   例:
     import duckdb
     from datetime import date
     from kabusys.research import calc_momentum

     conn = duckdb.connect("data/kabusys.duckdb")
     records = calc_momentum(conn, date(2026, 3, 20))
     # records: [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]

3) ニュースのセンチメントスコア生成（OpenAI が必要）
   例:
     from kabusys.ai import score_news
     import duckdb
     from datetime import date

     conn = duckdb.connect("data/kabusys.duckdb")
     n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")  # api_key を省略すると env の OPENAI_API_KEY を使う

   出力: ai_scores テーブルへ書き込み（部分成功でも他コードを保護する設計）

4) 市場レジーム判定（ETF 1321 + マクロニュース → market_regime テーブル書き込み）
   例:
     from kabusys.ai.regime_detector import score_regime
     score_regime(conn, date(2026,3,20), api_key="sk-...")

5) 監視 DB の初期化と Streamlit ダッシュボード起動
   - 初期化:
       import sqlite3
       from kabusys.monitoring import init_monitoring_db

       conn = sqlite3.connect("data/monitoring.db")
       init_monitoring_db(conn)

   - Streamlit ダッシュボード起動:
       streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

6) MonitoringEngine（ポーリング監視）の利用（単回実行テスト）
   - MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor 等を組み合わせて使用します。
   - 単回実行テスト用に run_once() を呼び出して挙動確認可能。

7) ExecutionEngine（発注セッション）
   - 実行には BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続など多数の依存が必要です。  
     実稼働環境ではそれらを組み上げて ExecutionEngine(config).run_session() を呼びます（詳細はエンジンの docstring を参照）。

注意点・運用に関するポイント
---------------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CWD に依存せずパッケージ配布後も正しく動作するよう設計されています。
- .env のパースはシェルの export/クォート/コメントに準拠する実装です。特殊ケースがある場合は .env を直接編集してください。
- OpenAI API 呼び出しはレートリミット／5xx に対し指数バックオフでリトライしますが、運用では API キー・レート制限に注意してください。
- Kill Switch（data/kill.flag）で ExecutionEngine の安全停止を実現しています。起動時の残留フラグは設定でクリアするオプションがあります（KILL_FLAG_CLEAR_ON_START）。
- DB 書き込みはなるべく冪等に設計されています（DELETE→INSERT 等の扱いに注意）。

プロジェクト構成
----------------
以下は主要ファイル／ディレクトリの抜粋（src/kabusys 配下）。実際の実装はソース内の docstring を参照してください。

- src/kabusys/
  - __init__.py                         - パッケージ定義、バージョン
  - config.py                           - 環境変数 / .env 読み込みと Settings
  - portfolio/
    - portfolio_builder.py              - 候補選定・等重／スコア重み計算
    - risk_adjustment.py                - セクター上限・レジーム乗数
    - position_sizing.py                - 発注株数計算（リスクベース等）
  - research/
    - factor_research.py                - Momentum / Volatility / Value 等の計算
    - feature_exploration.py            - 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py                       - ニュースを LLM でスコアリング → ai_scores へ書込
    - regime_detector.py                - マクロ + ETF MA200 から市場レジーム判定
  - monitoring/
    - monitoring_db.py                  - SQLite 操作用ラッパー（init, MonitoringDB）
    - risk_monitor.py                   - ドローダウン・ポジション上限チェック
    - system_monitor.py                 - システムステータス／データ鮮度監視
    - trade_monitor.py                  - 注文滞留／約定異常監視
    - alert_manager.py                  - LINE push 通知
    - streamlit_dashboard.py            - Streamlit ダッシュボード（起動コマンドあり）
    - kill_switch.py                    - フラグファイル制御
    - monitoring_engine.py              - 各 Monitor を束ねるポーリングエンジン
  - execution/
    - broker_api.py                     - Broker API データモデル / Protocol / 例外
    - order_manager.py                  - Order State Machine 外向き API
    - order_repository.py               - （orders DB 操作 — 実装省略／別ファイル）
    - reconciler.py                     - 起動時のリコンシリエーション
    - execution_engine.py               - Signal Queue Pull 型発注エンジン
    - ...（他の execution 関連ファイル）
  - monitoring, research, portfolio の __init__.py で主要 API を再エクスポート

サンプル .env（最小）
--------------------
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=secret
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

トラブルシューティング
----------------------
- .env が読み込まれない
  - プロジェクトルートの判定はソースファイルの親ディレクトリ列を探索して .git または pyproject.toml を探します。ルート検出に失敗すると自動ロードをスキップします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自力で env を管理してください。
- OpenAI 例外
  - ネットワーク断や 5xx は再試行しますが、API キー未設定時は ValueError が発生します。
- DuckDB / SQLite に関するクエリ失敗
  - データテーブル（prices_daily / raw_financials / raw_news など）が想定通り存在しているか確認してください。

貢献・拡張
-----------
- 研究モジュールは純粋関数として設計されているため、追加ファクターや異なる正規化手法の追加が容易です。
- Position sizing は将来的に銘柄別 lot_size を受け取るよう拡張する設計余地があります（コードにも TODO コメントあり）。
- ブローカークライアントは BrokerAPIProtocol（protocol）に実装を合わせれば差し替え可能です。

ライセンス
----------
（このリポジトリのライセンス情報をここに記載してください。README には含めていません。）

最後に
------
各モジュールの詳細な使用法やパラメータはソースコード内の docstring に豊富に記載されています。まずは DuckDB / Monitoring DB を準備して、research モジュールや monitoring の機能から動かしてみることをおすすめします。必要な補助サンプルがあれば、用途別の短い起動例や設定テンプレートを追加で作成します。