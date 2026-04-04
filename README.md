KabuSys — 日本株自動売買 / データプラットフォーム
================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・自動売買のための内部ライブラリ群です。  
主に以下を提供します。

- J-Quants API を用いた株価・財務・カレンダーの ETL（差分取得／冪等保存）
- ニュース収集・NLP（OpenAI）による銘柄ごとのニュースセンチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの合成による daily レジーム）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB を用いたローカルデータ永続化ユーティリティ

設計方針の要点
- ルックアヘッドバイアス防止（target_date の明示、today を直接参照しない設計箇所あり）
- 冪等設計（DB への保存は ON CONFLICT / UPDATE を利用）
- フェイルセーフ／リトライ（API 呼び出しはリトライやフォールバックを実装）
- 外部依存は最小限（OpenAI / J-Quants / duckdb / defusedxml 等）

主な機能一覧
----------------
- data:
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: API 呼び出し・保存ロジック（token リフレッシュ・レート制御・ページング）
  - news_collector: RSS 収集（SSRF 対策・URL 正規化・デデュープ）
  - quality: データ品質チェック（missing, spike, duplicates, date consistency）
  - audit: 監査テーブルの初期化・監査 DB 管理
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: zscore 正規化ユーティリティ
- ai:
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出と ai_scores への保存
  - regime_detector.score_regime: ETF（1321）MA とマクロニュース LLM スコアから市場レジームを判定
- research:
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
----------------

1. Python 環境（推奨: 3.10+）を用意
   - 仮想環境を作る例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - プロジェクトが pyproject.toml を持つ想定:
     - pip install -e .[dev]  (プロジェクトルートで)
   - 必須の外部ライブラリ（手動インストール例）:
     - pip install duckdb openai defusedxml

   ※ 実際の pyproject.toml に記載された依存関係に従ってください。

3. 環境変数 / .env ファイルの準備
   - ルートに .env（および任意で .env.local）を置くと自動で読み込まれます（プロジェクトルート検出: .git または pyproject.toml）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuAPI のパスワード（必須）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - OPENAI_API_KEY: OpenAI API キー（AI 関連を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...

   - .env の優先順位: OS 環境変数 > .env.local > .env

使い方（主な利用例）
------------------

- DuckDB 接続を作成して ETL を走らせる（Python REPL / スクリプト内）:

  - サンプル:
    - import duckdb
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
    - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    - print(result.to_dict())

  - run_daily_etl はカレンダー→株価→財務→品質チェック を順に実行し ETLResult を返します。

- ニュースセンチメントの算出（OpenAI API キー要）:

  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を渡すか環境変数 OPENAI_API_KEY を設定

  - 処理後、ai_scores テーブルにスコアが書き込まれます。

- 市場レジーム判定（OpenAI API キー要）:

  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

  - market_regime テーブルへ結果を冪等的に書き込みます。

- 監査 DB の初期化:

  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリを自動作成

- RSS 取得（ニュース収集）:

  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

  - 記事は raw_news に保存する前に preprocess して使います（モジュールの保存関数を利用）。

- J-Quants 直接呼び出し（トークン取得・データ取得）:

  - from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  - id_token = get_id_token()  # settings.jquants_refresh_token から自動取得
  - records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,20))

注意点
- OpenAI を用いる関数は API キー（OPENAI_API_KEY）を必要とします。API 呼び出しはリトライやフォールバックを実装していますが、コストとレート制限に注意してください。
- J-Quants の API 呼び出しはレート制御とトークンリフレッシュを備えています。refresh token は必ず安全に保管してください。
- 本ライブラリの設計はバックテストのルックアヘッドバイアス軽減を考慮していますが、外部での使用時も target_date の扱いに注意してください。
- 実際の取引・発注を行う実装（kabu ステーションとの連携やリスク管理ロジック）は別途十分な検証が必要です。本リポジトリは基盤・研究・監査ログを提供しますが、運用は自己責任です。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール（抜粋）と簡単な説明です。

- __init__.py
  - パッケージのバージョン等を公開

- config.py
  - 環境変数 / .env 自動読み込み、settings オブジェクトを提供
  - 主要プロパティ: jquants_refresh_token, kabu_api_password, openai, db paths, 環境判定 etc.

- ai/
  - news_nlp.py         — ニュースセンチメント算出と ai_scores への書き込み
  - regime_detector.py  — ETF MA とマクロニュースで市場レジーム判定

- research/
  - factor_research.py  — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

- data/
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py   — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py   — RSS 収集（SSRF 対策、URL 正規化）
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - stats.py            — zscore_normalize 等
  - quality.py          — データ品質チェック
  - audit.py            — 監査ログテーブル定義・初期化ユーティリティ
  - etl.py              — ETLResult 再エクスポート
  - pipeline.py（上記）/ 他ユーティリティ

テスト・開発
--------------
- 自動読み込みの無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config の .env 自動読み込みを無効化できます（テスト時に便利）。
- API 呼び出しは外部ネットワークや有料 API を利用するため、ユニットテストでは openai / urllib 等をモックすることを推奨します（モジュール内でモック対象の小さなラッパー関数を利用可能）。

ライセンス / 責任範囲
-------------------
- 本ドキュメントはコードベースの説明を目的としています。実際の運用・発注を行う際は適切なリスク管理・テスト・監査を行ってください。
- 外部 API の使用（OpenAI、J-Quants など）は各サービスの利用規約に従ってください。

補足（よくある操作）
-------------------
- .env の例（最低限必要な項目）:
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - OPENAI_API_KEY=sk-...
  - KABU_API_PASSWORD=your_kabu_password
  - DUCKDB_PATH=data/kabusys.duckdb
  - KABUSYS_ENV=development

- デバッグログを有効にする:
  - LOG_LEVEL=DEBUG を設定するとライブラリ内の logger の詳細が出力されます。

以上です。実際に使用したい箇所（ETL の実行方法、AI スコアリングの呼び出し、監査 DB 初期化など）について具体的なサンプルやスクリプトが必要であれば、用途に合わせた短い例を追加で作成します。どの操作の例を見たいか教えてください。