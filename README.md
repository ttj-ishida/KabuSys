# KabuSys

日本株向けデータプラットフォーム兼自動売買基盤（ライブラリ）

このリポジトリは、日本株のデータ取得（J-Quants）、ニュース収集・AIによるニュース解析、ファクター計算、ETL パイプライン、監査ログ（発注/約定トレース）、市場カレンダー管理などを含む汎用ライブラリ群を提供します。実運用の Execution/Strategy 層と連携して自動売買システムを構成するための基盤コンポーネント群です。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() を直接参照しない箇所が多い）
- DuckDB を主な永続化層として想定
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（JSON Mode）を組み込み
- J-Quants API のレート制御・リトライ・トークン自動更新対応
- 冪等性・監査ログを重視（ORDER_REQUEST の冪等キー等）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（例）
- ディレクトリ構成
- 知っておくべき実装メモ

---

プロジェクト概要
- 日本株データ ETL（J-Quants からの株価/財務/カレンダー取得）
- ニュース収集（RSS）および LLM によるニュースセンチメント解析（銘柄別 / マクロ）
- ファクター計算（Momentum / Volatility / Value 等）と研究ユーティリティ（IC / forward returns 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- 市場カレンダー管理（営業日の判定・次営業日/前営業日・カレンダー更新ジョブ）
- 設定管理（.env 自動読み込み、環境変数経由設定）

---

機能一覧（主要モジュール）
- kabusys.config
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - 環境変数のラッパー settings（J-Quants token、OpenAI、DBパス、監視閾値など）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、ページネーション、レート制御、トークン自動リフレッシュ
  - fetch/save系: fetch_daily_quotes / save_daily_quotes, fetch_financial_statements / save_financial_statements, fetch_market_calendar / save_market_calendar, fetch_listed_info
- kabusys.data.pipeline
  - ETL エントリーポイント run_daily_etl
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult（結果オブジェクト）
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- kabusys.data.news_collector
  - RSS フィード取得、前処理、SSRF/サイズ制限を考慮した安全な実装
- kabusys.ai.news_nlp
  - 銘柄別ニュースを LLM に送って ai_scores に書き込む score_news
  - バッチ／再試行／レスポンス検証ロジックを含む
- kabusys.ai.regime_detector
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime を算出する score_regime
- kabusys.research
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 研究用関数: calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.audit
  - 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

---

セットアップ手順

前提
- Python 3.10 以上（型注釈で | を使用しているため）
- システムに DuckDB をインストール可能であること

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -r requirements.txt
   ※ requirements.txt がない場合は主に以下をインストールしてください:
     pip install duckdb openai defusedxml

   （プロジェクトによっては追加ライブラリが必要になる可能性があります。運用用 Slack 通知等がある場合は slack-sdk 等も導入してください）

4. 環境変数を設定（.env をプロジェクトルートに配置）
   プロジェクトは自動的にプロジェクトルートを探索して .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=xxxxxxxx
   - OPENAI_API_KEY=sk-xxxxxxxx
   - KABU_API_PASSWORD=<kabu_station_password>
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C0123456789

   データベースパス等（任意・デフォルトあり）:
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO

   例 .env（最小）:
     JQUANTS_REFRESH_TOKEN=YOUR_JQUANTS_REFRESH_TOKEN
     OPENAI_API_KEY=YOUR_OPENAI_API_KEY
     KABU_API_PASSWORD=YOUR_KABU_PASSWORD
     SLACK_BOT_TOKEN=YOUR_SLACK_TOKEN
     SLACK_CHANNEL_ID=YOUR_SLACK_CHANNEL

5. データベース初期化（監査ログ用の例）
   Python REPL またはスクリプトから:
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

使い方（簡単な例）

以下は基本的な API の呼び出し例です。DuckDB 接続は通常ファイルベース（settings.duckdb_path）を使います。

- DuckDB 接続を作る
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを算出して ai_scores に保存
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を env に設定しておく
  print(f"scored {count} symbols")

- 市場レジーム判定を実行（ma200 + マクロニュース）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマを初期化
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- ファクター計算（例：モメンタム）
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  # 必要に応じて zscore_normalize を適用
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

注意点
- OpenAI の呼び出しはネットワークエラーやレート制限に対するリトライを備えていますが、APIキーの設定が必須です。テスト時は内部の _call_openai_api 関数をモックする設計になっています。
- J-Quants API はレート制限や 401 リフレッシュに対応しています。get_id_token() によりリフレッシュトークンから id_token を取得します。

---

ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                       -- 環境変数・設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                    -- 銘柄ニュースの LLM スコアリング（score_news）
  - regime_detector.py             -- マクロ + MA200 合成で市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py              -- J-Quants API クライアント（fetch/save）
  - pipeline.py                    -- ETL パイプラインと run_daily_etl
  - etl.py                         -- ETLResult の再エクスポート
  - quality.py                     -- データ品質チェック
  - stats.py                       -- 統計ユーティリティ（zscore_normalize）
  - news_collector.py              -- RSS 取得・前処理
  - calendar_management.py         -- 市場カレンダー管理
  - audit.py                       -- 監査ログスキーマ・初期化
- research/
  - __init__.py
  - factor_research.py             -- モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py         -- 将来リターン・IC・統計サマリー等
- ai/, data/, research/ の __init__ は公開 API を整理

（加えてテスト、CI、ドキュメント、CLI 等をプロジェクトで整備することを推奨します）

---

知っておくべき実装メモ / 運用メモ
- .env 自動ロード: プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を読み込みます。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは JSON Mode を想定し、厳密な JSON を期待します。実運用ではレスポンス検証・パース失敗時のフェイルセーフ（0.0 にフォールバックやスキップ）を行う実装になっています。
- DuckDB に対する executemany の仕様（バージョン差）を考慮して空パラメータでの executemany 呼び出しを避けるチェックが入っています。
- news_collector は SSRF 対策（リダイレクト検査、プライベートIP拒否）、レスポンスサイズ制限、XML パースの安全化（defusedxml）等を実装しています。
- 監査ログスキーマは冪等性・追跡性を重視しており、order_request_id を冪等キーとして二重発注を防止する設計です。

---

ライセンス / 貢献
- 本 README にライセンス情報は含まれていません。リポジトリルートに LICENSE ファイルがある場合はそれに従ってください。
- バグ修正や機能追加を行う場合は、ユニットテストとモック（外部 API 呼び出しの差し替え）を追加してください。

---

問い合わせ
- 実装の詳細や拡張（例: 発注ブローカー連携、バックテスト用 API、運用監視）についてはコード内の docstring とコメントを参照してください。必要であればサンプルスクリプトや CLI を追加して運用手順を標準化することを推奨します。

以上。