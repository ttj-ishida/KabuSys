KabuSys
======

概要
----
KabuSys は日本株のデータ基盤・リサーチ・自動売買パイプラインを想定した Python ライブラリ群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダーデータの差分取得（ETL）
- RSS ニュース収集と LLM によるニュースセンチメント評価（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算・特徴量探索・IC 計算などのリサーチユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）を保持する DuckDB スキーマ
- データ品質チェック（欠損、スパイク、重複、日付整合性）

本 README はローカル開発・実行・簡単な使い方を説明します。

主な機能一覧
--------------
- データ ETL
  - J-Quants API から raw_prices / raw_financials / market_calendar を差分取得する run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 保存時は DuckDB 側で冪等（ON CONFLICT DO UPDATE）
  - レート制御・リトライ・ID トークン自動リフレッシュ実装 (kabusys.data.jquants_client)
- ニュース収集・NLP
  - RSS 取得・前処理・raw_news への保存（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント score_news（バッチ・チャンク処理・リトライ）
  - マクロニュースを使った市場レジーム判定 score_regime（ETF 1321 の MA200 乖離 + マクロセンチメント）
- リサーチ
  - ファクター計算（momentum, value, volatility 等）
  - 将来リターン計算、IC（Spearman rank）算出、ファクターサマリ
  - zscore 正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合検出（run_all_checks）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト（kabusys.config.settings）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 演算子、list[str] 等を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS 取得）

1. リポジトリをクローン
   - git clone ... （.git または pyproject.toml がプロジェクトルート検出に使われます）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   例 requirements.txt（最小）
   - duckdb
   - openai
   - defusedxml

   実プロジェクトではテストフレームワーク等も追加してください。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD     : kabu ステーション API のパスワード（必要な場合）
   - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 sqlite（デフォルト data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH 等の監視関連
   - KABUSYS_ENV           : development / paper_trading / live
   - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL

   例 .env（最小）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=sk-...

5. 初期 DB 準備（監査ログ用の例）
   - Python REPL またはスクリプトから：
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（主要な API 例）
----------------------

共通: DuckDB 接続
- import duckdb
- conn = duckdb.connect("data/kabusys.duckdb")  # ":memory:" も可

1) 日次 ETL 実行（J-Quants から差分取得）
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- res = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(res.to_dict())

2) 個別 ETL（株価・財務）
- from kabusys.data.pipeline import run_prices_etl, run_financials_etl
- fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
- fetched, saved = run_financials_etl(conn, target_date=date(2026,3,20))

3) ニューススコアリング（銘柄別）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n = score_news(conn, target_date=date(2026,3,20))  # OpenAI キーは環境変数か api_key 引数で渡す
- print(f"{n} 銘柄のスコアを書き込みました")

4) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーが必要

5) 監査ログ初期化
- from kabusys.data.audit import init_audit_schema, init_audit_db
- conn = init_audit_db("data/audit.duckdb")  # ファイルを作成してスキーマ初期化

6) リサーチ系ユーティリティ
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- records = calc_momentum(conn, target_date=date(2026,3,20))
- from kabusys.data.stats import zscore_normalize
- normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

7) 品質チェック（ETL 後）
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=date(2026,3,20))
- for i in issues: print(i)

注意事項・設計上のポイント
-------------------------
- Look-ahead bias 対策:
  - 日付判定・ウィンドウ計算は内部で datetime.today() を直接参照せず、target_date を明示的に渡して使用する設計です。バックテストでは必ず過去時点の情報のみを与えてください。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定（JSON mode を利用）。API エラーや JSON パース失敗時はフェイルセーフとして 0.0（中立）にフォールバックする箇所があります。
- J-Quants クライアント:
  - レート制限（120 req/min）を守る RateLimiter とリトライ・401 自動リフレッシュ実装あり。
- DuckDB との互換性:
  - DuckDB の executemany 空リスト制約などに配慮した実装があります（コード内コメント参照）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                     : .env / 環境変数管理、Settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py                  : ニュースセンチメント集約・OpenAI 呼び出し
  - regime_detector.py           : ETF + マクロニュース合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            : J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py                  : ETL パイプライン（run_daily_etl 等）
  - etl.py                       : ETLResult の再エクスポート
  - news_collector.py            : RSS 取得・前処理・raw_news 保存（SSRF 対策等）
  - calendar_management.py       : 市場カレンダー管理・営業日ロジック
  - quality.py                   : データ品質チェック群
  - stats.py                     : zscore_normalize 等の統計ユーティリティ
  - audit.py                     : 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py           : momentum / value / volatility 等
  - feature_exploration.py       : 将来リターン・IC・統計サマリ
- research/... (その他の研究ユーティリティ)

環境変数・自動 .env 読み込み
-----------------------------
- config.py はプロジェクトルート（.git または pyproject.toml）を基に .env / .env.local を自動読み込みします。
- 優先順位: OS 環境 > .env.local > .env
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須変数に未設定がある場合、Settings のプロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

トラブルシューティング
---------------------
- OpenAI / J-Quants の認証エラー:
  - 環境変数が正しく設定されているか確認してください。J-Quants はリフレッシュトークンから id_token を取得します。
- DuckDB のパス:
  - デフォルトは data/kabusys.duckdb。親ディレクトリが存在しない場合は作成してください（audit.init_audit_db は親作成を行います）。
- RSS 取得時の SSRF 関連エラー:
  - fetch_rss はプライベートアドレスや非 http(s) スキームを拒否します。URL を確認してください。

ライセンス・貢献
----------------
この README はコードベースの説明用です。実際に運用・本番トレードを行う場合は十分なテストと運用上の安全策（リスク管理、フェイルセーフ、監査）を実装してください。

フィードバックや改善提案は Pull Request / Issue を通じて歓迎します。