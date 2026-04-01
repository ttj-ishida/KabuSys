# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
DuckDB をデータ層に用い、J-Quants / JPX / RSS / OpenAI 等と連携して以下のような機能を提供します。

- データ ETL（株価日足、財務、マーケットカレンダー）
- ニュース収集・前処理（RSS → raw_news）
- ニュース NLP（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（ETF + マクロニュースの LLM 評価）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログテーブル（シグナル→発注→約定のトレーサビリティ）
- J-Quants API クライアント（取得・保存・レート制御・リトライ）

この README はソースツリーの主要モジュールに基づいて作成されています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch/save 各種データ、トークン自動更新、レート制御）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS の安全取得、正規化、raw_news への保存準備）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に書き込む）
  - 市場レジーム判定（score_regime: ETF 200 日 MA とマクロニュースの LLM スコア合成）
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索 / 統計（calc_forward_returns, calc_ic, factor_summary, rank）
- 設定管理
  - 環境変数読み込み（.env / .env.local を自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で各種設定・パスを取得

---

## セットアップ手順

前提:
- Python 3.10+（typing の union shorthand を使用）
- DuckDB が使用可能な環境
- OpenAI API キー（news_nlp / regime_detector で使用）
- J-Quants リフレッシュトークン（API 呼び出しで使用）

1. リポジトリをクローン / コピーする

   git clone <repo-url>
   cd <repo>

2. 依存パッケージをインストール（例: pip）

   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればその手順に従ってください。上記は最低限の依存です。）

3. 環境変数を設定する（.env をプロジェクトルートに配置するか OS 環境に設定）

   推奨キー（.env.example 相当）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=your_openai_api_key
   - DUCKDB_PATH=data/kabusys.duckdb      # 任意: デフォルト値
   - SQLITE_PATH=data/monitoring.db       # 任意
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO

   注意:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的に .env/.env.local を読み込む挙動を無効化できます（テスト用途など）。
   - settings により既定値や必須チェックが行われます（未設定だと ValueError が発生します）。

4. DuckDB 用ディレクトリを作成（必要に応じて）

   mkdir -p data

---

## 使い方（主要な例）

以下は Python スクリプトや REPL から呼び出す想定の使用例です。実運用時はログ設定・例外ハンドリングを追加してください。

1. 設定の参照

   from kabusys.config import settings
   print(settings.duckdb_path)
   print(settings.is_live)

2. DuckDB に接続して日次 ETL を実行

   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   # target_date を省略すると今日が使われます（内部は営業日調整あり）
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())

3. ニュースセンチメントの算出（OpenAI API 必須）

   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect(str(settings.duckdb_path))
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書き込み銘柄数: {written}")

   - API キーは環境変数 OPENAI_API_KEY を用いるか、score_news(..., api_key="...") の引数で指定できます。
   - news_nlp は J-Quants から取得した raw_news と news_symbols を参照して ai_scores を書き換えます。

4. 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM を合成）

   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20))

   - 同じく OPENAI_API_KEY を環境変数か api_key 引数で指定します。
   - 処理は market_regime テーブルへ冪等書き込みします。

5. 監査ログ DB の初期化

   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # これで監査用テーブル（signal_events, order_requests, executions 等）が作成されます

6. 研究用途のファクター計算

   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   conn = duckdb.connect(str(settings.duckdb_path))
   momentum = calc_momentum(conn, target_date=date(2026,3,20))
   volatility = calc_volatility(conn, target_date=date(2026,3,20))
   value = calc_value(conn, target_date=date(2026,3,20))

---

## 環境変数と設定（まとめ）

必須 env（Settings により要求されるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（必要なモジュール使用時）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知のチャンネル ID

推奨 / 任意
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

注意: .env の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）を基準に実行されます。

---

## ディレクトリ構成（主要ファイル・モジュール）

src/kabusys/
- __init__.py — パッケージ定義と __version__
- config.py — 環境変数 / 設定管理（Settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント解析 / score_news
  - regime_detector.py — 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - etl.py — ETL 結果型の再エクスポート
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック
  - audit.py — 監査ログテーブルの DDL と初期化
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - news_collector.py — RSS 収集 / 前処理
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

---

## 実運用上の注意点

- Look-ahead bias 対策
  - 多くのモジュールは内部で datetime.today()/date.today() を直接参照しない設計（引数で日付を渡す）になっています。バックテストや再現性のため、target_date を明示的に指定することを推奨します。

- OpenAI / J-Quants API 呼び出しのリトライとフォールバック
  - API エラー時は指数バックオフでリトライし、それでも失敗した場合はフェイルセーフ（ゼロスコアやスキップ）で継続する処理が多く取り入れられています。

- データベース操作の冪等性
  - save_* 関数や監査ログ作成は冪等性（ON CONFLICT / PRIMARY KEY）を考慮して実装されています。部分失敗時に既存データを保護するための実装がされています。

- セキュリティ
  - news_collector は SSRF 対策（リダイレクトチェック、プライベート IP 拒否）や XML パースの安全化（defusedxml）を行っています。
  - 環境変数・シークレットは .env に置く場合はファイルのアクセス制御に留意してください。

---

## 開発・テストのヒント

- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテストを行います。
- OpenAI 呼び出しなどをモックするために、各モジュール内の private な呼び出し関数（例: kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）を unittest.mock.patch で差し替えることが容易です。
- DuckDB のインメモリ接続は init_audit_db(":memory:") のように使えます。

---

必要であれば、この README をプロジェクトの実際のパッケージ構成（pyproject.toml / requirements.txt / CI ワークフロー）に合わせて調整します。追加で README に入れたい具体的なコマンド例（cron ジョブ、systemd ユニット、Dockerfile など）があれば教えてください。