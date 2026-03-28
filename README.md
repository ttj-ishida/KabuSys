# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データの ETL、ニュース NLP、研究用ファクター計算、監査ログ、マーケットカレンダー管理、J-Quants / kabu API クライアントなどを含みます。

## 概要

KabuSys は以下の目的を持つモジュール集合です。

- J-Quants API からのデータ取得（株価日足、財務、上場情報、JPXカレンダー）
- DuckDB を用いたデータ格納・ETLパイプライン（差分取得・保存・品質チェック）
- RSS ニュース収集と LLM を使った記事ベースの銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの混合スコア）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ定義・初期化
- kabu ステーション等への実際の発注処理（将来的な実装箇所）

バイアス防止（Look-ahead）、冪等性、フェイルセーフ設計、API リトライ/レート制御などを重視しています。

## 主な機能一覧

- データ取得・保存
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - save_* 系で DuckDB に冪等保存
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・NLP
  - RSS フィード取得（SSRF 防御、トラッキングパラメータ除去）
  - OpenAI を使った銘柄ごとのニュースセンチメント score_news
  - マクロニュース + ETF MA200 を合成して市場レジームを判定 score_regime
- 研究用ユーティリティ
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（J-Quants から差分取得）
- 監査ログ（audit）
  - init_audit_schema / init_audit_db（監査テーブルの初期化）
- 共通ユーティリティ
  - 設定管理（kabusys.config.Settings）: .env 自動ロード、必須環境変数チェック

## 必要環境・依存パッケージ（代表）

- Python 3.9+
- duckdb
- openai
- defusedxml

（プロジェクトの pyproject.toml / requirements.txt を参照して下さい。実行環境に合わせて追加パッケージが必要になる場合があります。）

## セットアップ手順

1. レポジトリをクローンし、編集用にインストール（開発モード推奨）

   git clone <リポジトリURL>
   cd <repo>
   pip install -e .

2. 環境変数 / .env ファイルを準備

   必須の環境変数（少なくとも以下は設定が必要）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu API のパスワード（発注等で必要）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時）
   
   オプション（デフォルト値あり）:

   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 などを設定）

   推奨: プロジェクトルートに `.env` と（必要なら）`.env.local` を置く。
   モジュール起動時に自動で .env を読み込みます（プロジェクトルートは .git または pyproject.toml を基準に検索）。

   .env の例（.env.example）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB データベースの準備

   デフォルトパスは data/kabusys.duckdb。必要に応じてディレクトリを作成してください:
   mkdir -p data

## 使い方（簡単なコード例）

基本的に DuckDB の接続を作り、公開 API 関数を呼びます。

- DuckDB 接続作成例

  from pathlib import Path
  import duckdb
  db_path = Path("data/kabusys.duckdb")
  conn = duckdb.connect(str(db_path))

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを算出（score_news）

  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written: {n_written}")

  ※ api_key を None にすると環境変数 OPENAI_API_KEY を参照します。

- 市場レジーム判定（score_regime）

  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使う

- 研究用ファクター計算

  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m"])

- 監査ログ DB 初期化

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # 既存接続にスキーマを追加したい場合は init_audit_schema(conn)

## 設定・挙動の注意点

- .env 自動ロード
  - モジュールインポート時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで有用）。

- OpenAI 呼び出しについて
  - gpt-4o-mini を利用する前提で JSON Mode を使った呼び出しを行います。
  - API エラー（レート制限・ネットワーク等）はリトライ実装がありますが、最終的に失敗した場合は安全側のデフォルト（例: macro_sentiment=0.0）で継続します。

- Look-ahead / バイアス防止
  - score_news / score_regime / ETL 等の関数は内部で datetime.today() を直接参照しない設計です。必ず target_date を指定するか、公開関数のデフォルト（today）利用時も設計方針に従っています。

- DuckDB の executemany の制約
  - 一部実装で空リストでの executemany を避けるチェックを行っています（DuckDB 互換問題回避）。

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      -- 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                  -- ニュース NLP（score_news）
  - regime_detector.py           -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py            -- J-Quants API クライアント（取得・保存）
  - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
  - etl.py                       -- ETLResult の再エクスポート
  - calendar_management.py       -- 市場カレンダー管理（is_trading_day 等）
  - news_collector.py            -- RSS ニュース収集
  - stats.py                     -- 統計ユーティリティ（zscore_normalize）
  - quality.py                   -- データ品質チェック
  - audit.py                     -- 監査ログスキーマ / 初期化
- research/
  - __init__.py
  - factor_research.py           -- モメンタム / ボラティリティ / バリュー算出
  - feature_exploration.py       -- 将来リターン / IC / 統計サマリー等
- ai/ (上記)
- research/ (上記)
- その他（strategy / execution / monitoring 等の名前空間は将来的に含める設計）

（実際のリポジトリルートには pyproject.toml / setup.cfg / README などが存在する想定です）

## 開発・テスト時のヒント

- 設定の自動ロードが邪魔な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして無効化してください。
- OpenAI 呼び出し部分は内部で _call_openai_api を定義しており、ユニットテストではこの関数をモックすることで外部 API を差し替えられます。
- J-Quants API へのリクエストは RateLimiter とリトライロジックが組み込まれているため、テストでは get_id_token / _request をモックするとよいです。
- news_collector の fetch_rss は SSRF 防止や応答サイズ制限などの厳格な検証を行っているため、テスト用に HTTP サーバを立てる際はその制約を満たしてください。

---

問題や改善案があれば issue を作成してください。README の追記やサンプルスクリプト、CLI ラッパー等を追加する予定です。