KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的に設計された Python パッケージ群です。
主に以下を目的とします。

- ファクター計算・特徴量探索（DuckDB を用いたオフライン分析）
- ポートフォリオ構築（候補選定、重み決定、株数算出）
- 実行エンジン（シグナル→発注、WebSocket プッシュの処理、再構成）
- AI 支援（ニュースセンチメント、マクロセンチメントによるレジーム判定）
- 監視・アラート（ロギング、ダッシュボード、LINE プッシュ通知、Kill Switch）

主要な設計方針は「本番発注ロジックと研究ロジックの分離」「ルックアヘッドバイアスの排除」「DB を用いた可観測性の確保」「フェイルセーフ設計（API失敗時は安全側で継続）」です。

機能一覧
--------
- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート判定: .git / pyproject.toml）
  - 必須値の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能

- ポートフォリオ構築
  - シグナルのスコア順選定 (select_candidates)
  - 等金額配分 / スコア加重配分 (calc_equal_weights, calc_score_weights)
  - セクター集中制限適用 (apply_sector_cap)
  - レジームに応じた投下資金係数 (calc_regime_multiplier)
  - 株数決定（リスクベース、重みベース）・利用可能資金に応じたスケーリング (calc_position_sizes)

- リサーチ / ファクター
  - Momentum / Volatility / Value（PER, ROE）等のファクター算出（DuckDB 上で SQL＋Python）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計要約

- AI（OpenAI）統合
  - ニュース記事のセンチメントスコア化（ai.news_nlp.score_news）
  - マクロセンチメントと ETF (1321) MA200 を用いた市場レジーム判定（ai.regime_detector.score_regime）
  - バッチ・リトライ・レスポンス検証などの堅牢な実装

- 実行 / 発注
  - Broker API プロトコル定義（broker_api）
  - Order 管理、送信、同期、キャンセル（OrderManager）
  - 再起動時のリコンシリエーション（Reconciler）
  - ExecutionEngine：シグナル処理と WebSocket ドレイン（kill flag, PID 管理）

- 監視 / アラート
  - SQLite に監視ログを永続化する MonitoringDB（init_monitoring_db）
  - System / Trade / Risk の監視ロジック（システム負荷、滞留注文、ドローダウン等）
  - LINE 通知（AlertManager）・KillSwitch による安全停止
  - Streamlit ベースの監視ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

セットアップ手順
--------------
前提
- Python 3.10+（typing の記法や型補助を使用）
- 仮想環境の利用を推奨

1. クローン／配置
   - リポジトリをチェックアウトし、プロジェクトルート（pyproject.toml や .git がある場所）を確認します。

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存ライブラリをインストール
   - 必要なパッケージ（例）
     - duckdb
     - openai
     - requests
     - psutil
     - streamlit
   - 例:
     pip install duckdb openai requests psutil streamlit

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

4. 環境変数設定
   - プロジェクトルートの .env / .env.local を用意するか、OS 環境変数を設定します。
   - 自動ロード: .env → .env.local の順で読み込まれます（OS 環境変数が最優先）。.env.local は .env を上書きできます。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

  代表的な環境変数例（.env の一部例）
  - JQUANTS_REFRESH_TOKEN=<your jquants refresh token>      # 必須
  - KABU_API_PASSWORD=<kabu station password>               # 必須（実行用）
  - OPENAI_API_KEY=<openai api key>                         # AI 機能を使う場合
  - LINE_CHANNEL_ACCESS_TOKEN=<line token>                  # アラート用（任意）
  - LINE_USER_ID=<line user id>                             # アラート用（任意）
  - DUCKDB_PATH=data/kabusys.duckdb                          # デフォルト
  - SQLITE_PATH=data/monitoring.db                           # 監視 DB（デフォルト）
  - KABUSYS_ENV=development|paper_trading|live               # 動作モード
  - LOG_LEVEL=INFO|DEBUG|...                                 # ログレベル

5. 監視 DB 初期化（MonitoringDB）
   Python から:
   python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn)"

使い方
------
- 設定参照
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.is_paper)

- DuckDB を使ったファクター計算（例: Momentum）
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  results = calc_momentum(conn, date(2026, 3, 20))

- AI ニューススコアリング
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")  # ai_scores, raw_news, news_symbols テーブルが必要
  n = score_news(conn, date(2026, 3, 20), api_key="sk-...")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,3,20), api_key="sk-...")

- Streamlit ダッシュボード起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- MonitoringEngine（ポーリング監視）をテストで1回だけ実行
  from kabusys.monitoring import MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager
  # それぞれに必要な依存（DB コネクション等）を渡してインスタンス化し、engine.run_once() を呼ぶ

- ExecutionEngine（本番用）
  実行には Broker 実装（BrokerAPIProtocol を実装したクライアント）、OrderRepository（SQLite ベース）、RiskManager、OrderManager、DuckDB 接続など多くの依存が必要です。
  テスト目的でモックを用意して ExecutionEngine.run_session() や .run_once() を呼ぶことが可能です。

- kill.flag / PID ファイル
  - ExecutionEngine 起動時に PID を data/execution.pid（デフォルト）へ書きます。
  - KillSwitch は settings.kill_flag_path（デフォルト data/kill.flag）へ文字列を書き込み実行停止指示を出します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると既存 kill.flag をクリアして起動します。

自動 .env 読み込みの挙動（補足）
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env/.env.local を探索して自動読み込みします。
- export KEY=val、シングル／ダブルクォート、行頭コメント（#）など一般的な .env 構文をサポートします。
- OS 環境変数は保護され、.env の上書きを防ぎます。.env.local は override=True で上書き可能（ただし OS 環境変数は保護）。

ディレクトリ構成（主要ファイル）
-------------------------
src/
  kabusys/
    __init__.py                     # パッケージ定義、__version__
    config.py                       # 環境変数・設定管理
    portfolio/
      __init__.py
      portfolio_builder.py          # 候補選定・重み計算
      risk_adjustment.py            # セクターキャップ・レジーム倍率
      position_sizing.py            # 株数算出・スケーリング
    research/
      __init__.py
      factor_research.py            # Momentum/Volatility/Value ファクター
      feature_exploration.py        # 将来リターン、IC、統計サマリー
    ai/
      __init__.py
      news_nlp.py                   # ニュース NLP（OpenAI）→ ai_scores 書き込み
      regime_detector.py            # マクロ + MA200 によるレジーム判定
    monitoring/
      __init__.py
      monitoring_db.py              # SQLite 用永続化層（テーブル作成等）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    execution/
      broker_api.py                 # Broker API のデータモデル / Protocol / 例外
      order_manager.py              # OrderManager（送信・同期・キャンセル）
      reconciler.py                 # 再起動時リコンシリエーション
      execution_engine.py           # 発注エンジン（シグナル処理 + push drain）
      ...                           # （order_repository/record 等は別ファイルに存在する想定）
    data/
      ...                           # DuckDB 関連ユーティリティ（get_last_price_date など）
    monitoring/                       # 監視関連は上記 monitoring フォルダ内に配置

注意点 / 運用ヒント
------------------
- AI 機能は OPENAI_API_KEY が必須です。API 呼び出し失敗時は安全側のデフォルト（例: macro_sentiment=0.0）で継続するよう実装されていますが、正確な結果には API キーが必要です。
- 実際の発注を行う部分（Broker 実装・パスワード管理）は慎重に扱ってください。テスト環境／paper_trading モードを用意しているので、本番口座での投入前に十分な検証を行ってください。
- DuckDB / SQLite のスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets 等）が前提になります。必要なテーブルは事前に作成・投入してください。
- ローカルテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを抑止すると再現性の高いテストが可能です。

コントリビューション／拡張
--------------------------
- BrokerAPIProtocol を実装することで任意の証券会社クライアントを接続できます。
- position_sizing の lot_size 固定設計は将来的に銘柄別単元対応へ拡張可能です（注記あり）。
- 新たなファクター／フィーチャーは research 以下に純粋関数として追加してください（DuckDB 接続を引数として受ける設計）。

---

README に書ききれない詳細（関数や引数の振る舞い、エラーハンドリング、SQL の前提等）は各モジュールの docstring / 関数コメントに記載しています。実装を読むことで動作要件や安全上の注意点を確認できます。必要があれば利用例や運用手順（デプロイ手順、runbook、テスト例）を別ドキュメントで追加します。