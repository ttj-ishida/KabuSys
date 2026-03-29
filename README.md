# KabuSys — 日本株自動売買プラットフォーム（README）

短い説明
- KabuSys は日本株のデータプラットフォーム、リサーチ、ニュースNLP、レジーム判定、ETL および監査ログ機能を備えた自動売買システムのコアライブラリ群です。
- 本リポジトリはモジュール単位でデータ取得/保存（J-Quants）、データ品質チェック、特徴量計算、AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定、監査ログ（オーダー追跡）などを提供します。

主な機能
- データ取得 & ETL
  - J-Quants API からの株価（日次 OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と DuckDB への冪等保存
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質管理
  - 欠損、重複、スパイク、日付不整合のチェック（quality モジュール）
- ニュース収集・NLP
  - RSS 取得と前処理、raw_news / news_symbols への保存ロジック（news_collector）
  - OpenAI を用いた銘柄ごとのニュースセンチメントスコア（news_nlp.score_news）
- レジーム判定（AI + 指標合成）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジームを日次判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム/バリュー/ボラティリティ等のファクター計算、将来リターン・IC・統計サマリ（research パッケージ）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマと初期化ユーティリティ（data.audit）

前提 / 必要な依存
- Python 3.10+（typing の一部記法に対応）
- 主要な Python パッケージ（例）:
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI、RSS ソースへの HTTP(S)
- 環境変数による設定管理（.env からの自動読み込みに対応）

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone ...（リポジトリ URL）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージをインストール（パッケージ化されている場合）
   - python -m pip install -e .
   - または必要な依存を手動でインストール:
     - pip install duckdb openai defusedxml
4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置けば自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須環境変数の一覧（config.Settings 参照）
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - 任意 / デフォルト値あり
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : SQLite (monitoring 用) のファイルパス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
5. 必要に応じて DuckDB ファイルの親ディレクトリを作成（init_audit_db が自動作成も行います）

.env の例（テンプレート）
- .env.example を参照してください（リポジトリにある想定）。ここは最低限の例：
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - KABU_API_PASSWORD=your_kabu_password
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C01234567
  - DUCKDB_PATH=data/kabusys.duckdb
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO

基本的な使い方（コード例）
- 共通: 設定と DuckDB 接続
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（データ取得 → 保存 → 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメント（AI）計算（target_date のウィンドウでニュースを集約し ai_scores に書き込む）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  - print(f"scored {n_written} symbols")

- 市場レジーム判定（MA200 とマクロニュースの LLM スコア合成）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - res = score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  - print("done", res)

- 監査ログ DB の初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # これで監査テーブルが作成されます

- RSS 取得（news_collector の単体ユーティリティ）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  - for a in articles: print(a["id"], a["title"], a["datetime"])

主な公開 API の一例
- kabusys.config.settings — 環境設定取得
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL パイプライン実行
- kabusys.data.jquants_client.* — J-Quants API クライアント（get_id_token, fetch_daily_quotes 等）
- kabusys.data.news_collector.fetch_rss(...) — RSS 取得・前処理
- kabusys.ai.news_nlp.score_news(...) — 銘柄ごとのニュース AI スコア化（ai_scores 書込み）
- kabusys.ai.regime_detector.score_regime(...) — 市場レジーム判定（market_regime 書込み）
- kabusys.data.audit.init_audit_db(...) / init_audit_schema(...) — 監査スキーマ初期化

注意事項 / 設計方針（抜粋）
- ルックアヘッドバイアス防止: スクリプト内で datetime.today() / date.today() を直接参照しない設計（関数は target_date を引数に取る）。
- 冪等性: ETL 保存処理は ON CONFLICT DO UPDATE / INSERT … ON CONFLICT を活用して冪等に動作。
- フェイルセーフ: API 呼び出しに失敗しても例外を上位に投げずフォールバックする（例: LLM の失敗時に macro_sentiment=0.0 等）。
- セキュリティ: news_collector では SSRF 対策・XML の defusedxml 使用・レスポンスサイズ上限などを実装。

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — MA200 と LLM を組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - etl.py — ETLResult の公開エイリアス
    - news_collector.py — RSS 収集・正規化・保存ロジック
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（複数チェックを実行）
    - audit.py — 監査ログテーブルの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - その他: strategy / execution / monitoring パッケージ名は __all__ に含まれるが、リポジトリの全体実装に依存します

開発・テストについて
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部やネットワーク呼び出しはユニットテストでモック差し替えがしやすい設計（各モジュールの _call_openai_api / _urlopen をパッチ可能）。

トラブルシューティング
- 環境変数が足りない場合、config.Settings のプロパティが ValueError を投げます。エラーメッセージに従い .env を準備してください。
- DuckDB 操作でエラーが起きた場合は SQL スキーマが未作成の可能性があります（必要なテーブルを schema 初期化するか、ETL 実行で自動作成される処理を確認してください）。

ライセンス / コントリビュート
- 本 README にはライセンス情報を含めていません。実際のリポジトリに LICENSE ファイルがあればそちらを参照してください。
- 貢献方法はプロジェクトの CONTRIBUTING.md（存在する場合）に従ってください。

以上が本コードベースの概要と基本的な使い方です。具体的な詳細や運用レシピ（スケジューリング、モニタリング、リトライ/アラート設定、kabu ステーション連携や証券会社 API のラッパー実装等）は運用に合わせて追加実装してください。必要であれば README に追記・改善します。