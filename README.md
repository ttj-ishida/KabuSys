KabuSys — 日本株自動売買プラットフォーム（README）
===============================================================================

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ、AI（ニュースNLP / レジーム判定）、および監査・ETL ロジックを包含するライブラリ群です。  
主に以下の用途を想定しています：

- J-Quants API からの市場データ取得と DuckDB への保存（ETL）
- RSS ニュース収集と OpenAI を用いた銘柄センチメント付与
- マーケットレジーム判定（ETF とマクロニュースを組み合わせたスコア）
- ファクター計算・特徴量探索（リサーチ用途）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック、マーケットカレンダー管理

主な機能
--------
- data
  - ETL パイプライン（差分取得 / 保存 / 品質チェック）
  - J-Quants クライアント（認証・レート制御・リトライ・ページネーション）
  - ニュース収集（RSS、SSRF/サイズ対策、記事正規化）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
  - 監査ログ初期化（監査テーブル・インデックスの作成）
  - 統計ユーティリティ（Zスコア正規化 等）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF とマクロニュースを合成して market_regime に書き込み
  - 両モジュールは OpenAI JSON Mode（gpt-4o-mini）を用いる設計で、リトライやフォールバックを備える
- research
  - calc_momentum / calc_value / calc_volatility: ファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー、ランキング
- data.quality
  - 欠損・重複・スパイク・日付不整合チェック（QualityIssue を返す）

要件
----
- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）および必要に応じて kabuステーション API

（必要なパッケージはプロジェクト側で requirements.txt を用意してください。以下は例です）
pip install duckdb openai defusedxml

セットアップ手順
----------------

1. リポジトリを取得
   - git clone …（通常の手順）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係のインストール
   - pip install -e .   または
   - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local を上書き優先で読み込み）。  
     自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で便利）。

   - 必要な環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能を使う場合）
     - KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（必要に応じて）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 実行環境（development / paper_trading / live）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   - .env の例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. データベース初期化（監査ログ）
   - 監査テーブルを作る例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - その他のスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）はプロジェクト側でスキーマ定義／マイグレーションを用意してください（このコードベースには監査関連の DDL が含まれます）。

基本的な使い方
-------------

以下は Python REPL / スクリプトから呼び出す代表的な例です。

- DuckDB に接続して日次ETL を実行（J-Quants から差分取得・保存・品質チェック）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコアの取得（OpenAI API が必要）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {n_written}")

- マーケットレジームのスコア算出
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- ニュース RSS の取得（保存ロジックは別途必要）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

注意点 / 設計上の挙動
--------------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を起動時に自動で読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI 呼び出し:
  - news_nlp と regime_detector は JSON Mode（gpt-4o-mini）でレスポンスを厳密 JSON として期待します。
  - API 呼び出しはリトライやフォールバック（失敗時は 0.0 を返す等）を備えています。テストでは _call_openai_api をモックする設計です。

- Look-ahead bias 対策:
  - 多くの関数は date.today() や datetime.today() に直接依存しない実装で、target_date を明示的に渡してバックテスト向けに安全なデータ参照を意識しています。

- DuckDB 互換性:
  - 一部の実装は DuckDB の executemany の制約（空リスト不可 等）を考慮しています。

- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査、プライベートIP拒否）・XML 脆弱性対策（defusedxml）・レスポンスサイズ制限を実装しています。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                        -- 環境変数 / 設定読み込みロジック（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                     -- ニュースセンチメント付与（score_news）
  - regime_detector.py              -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py               -- J-Quants API クライアント（認証・取得・保存）
  - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
  - etl.py                          -- ETLResult の再エクスポート
  - news_collector.py               -- RSS 取得 / 前処理
  - calendar_management.py          -- 市場カレンダー操作（is_trading_day, next_trading_day 等）
  - quality.py                      -- データ品質チェック
  - stats.py                        -- 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                         -- 監査ログテーブル初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py              -- calc_momentum / calc_value / calc_volatility
  - feature_exploration.py          -- calc_forward_returns / calc_ic / factor_summary / rank

開発・テストメモ
----------------
- テスト時に OpenAI への呼び出しを避けたい場合は、kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch 等で差し替えてください（ライブラリはモジュール内のこの関数を呼んでいます）。
- 自動環境変数ロードはテストの再現性に影響するため、KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御できます。
- DuckDB のスキーマ定義や初期データロードはプロジェクト固有のセットアップスクリプトで行ってください（このリポジトリには監査用 DDL は含まれますが、raw_prices/raw_news 等の完全スキーマは環境に合わせて管理します）。

最後に
------
この README はコードベースから抽出できる主要な機能と利用方法をまとめたものです。実運用では環境変数や DB スキーマ、監査要件、発注インターフェース（kabuステーション）などに応じて追加の運用手順・監視・リスク制御を実装してください。質問や補足の希望があれば、どの機能について深掘りしたいか教えてください。