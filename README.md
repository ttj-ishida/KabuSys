KabuSys — 日本株自動売買プラットフォーム（README）
=====================================

概要
----
KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュース NLP・市場レジーム判定・監査ログを含む
オフライン/バッチ型のデータパイプラインおよびリサーチ基盤です。
主に以下を提供します。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（ページネーション・レート制御・自動リフレッシュ対応）
- raw データの品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と LLM を用いた銘柄センチメント解析（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの混合スコア）
- 研究用ファクター計算（モメンタム/ボラティリティ/バリュー 等）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- DuckDB を中心としたローカル DB の読み書きユーティリティ

特徴一覧
---------
主な機能（抜粋）:

- 環境/設定管理
  - .env ファイル（.env.local）と OS 環境変数から設定を自動ロード
  - settings オブジェクト経由で型付きプロパティ参照（例: settings.jquants_refresh_token）

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一連処理
  - 差分取得（最終取得日ベース）・バックフィル処理・品質チェック統合

- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミット制御、リトライ、401 時のトークン自動リフレッシュ対応
  - fetch / save 関数群（daily_quotes, financial_statements, market_calendar, listed_info）

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC）・スパイク（前日比）・重複・日付不整合チェック
  - QualityIssue を返却し呼び出し側で判定可能

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策、リダイレクト検査、受信サイズ制限、URL 正規化）
  - raw_news / news_symbols への冪等保存を想定した設計

- ニュース NLP・市場レジーム（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - score_regime: ETF 1321 の MA 偏差とマクロニュース LLM センチメントを合成し market_regime に書き込み
  - OpenAI 呼出しは JSON mode を期待、API キーは引数で上書き可（api_key）

- 研究用ツール（kabusys.research）
  - calc_momentum, calc_volatility, calc_value 等のファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

- 監査ログ（kabusys.data.audit）
  - 監査用スキーマ作成・初期化（init_audit_schema / init_audit_db）
  - signal / order_request / executions のテーブルとインデックスを定義

セットアップ手順
----------------

1. Python 環境を用意
   - 推奨: Python 3.10+（ソースの型注釈に基づく）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 代表的な依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r で管理してください）

3. 環境変数・.env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くと自動で読み込みます。
   - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（最低限必要なものの例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

   - .env のパースはシェル風の export KEY=val 形式やクォートに対応しています。

4. データディレクトリを作成
   - settings.duckdb_path（デフォルト data/kabusys.duckdb）などの親ディレクトリを作成しておくと便利です：
     - mkdir -p data

5. 監査 DB の初期化（任意）
   - 監査用 DuckDB を初期化する例:
     - from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

使い方（基本的な利用例）
-----------------------

※ 以下は最小限のコード例です。実環境ではログ設定やエラーハンドリングを追加してください。

- settings の参照
  - from kabusys.config import settings
  - print(settings.duckdb_path)

- DuckDB 接続の準備
  - import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（データ取得 → 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=None)  # target_date=None で今日（内部は営業日に調整）
    print(result.to_dict())

- ニューススコアリング（AI）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None で OPENAI_API_KEY を使用

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

  - 本関数は prices_daily / raw_news / market_regime を参照・更新します。

- ファクター計算（研究用途）
  - from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
    from datetime import date
    momentum = calc_momentum(conn, date(2026,3,20))
    volatility = calc_volatility(conn, date(2026,3,20))
    value = calc_value(conn, date(2026,3,20))

- 監査スキーマ初期化（既存接続にスキーマを作る）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

- ニュース収集（RSS）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

設計上の注意・運用上のポイント
-----------------------------
- Look-ahead バイアス対策
  - 多くの処理は date.today()/datetime.today() に依存しない設計になっており、
    明示的な target_date を渡すことでバックテスト時のルックアヘッドを防止できます。

- OpenAI 絡みの処理
  - AI 呼び出し（score_news, score_regime）は OpenAI API を用います。api_key を引数で与えるか
    環境変数 OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フォールバックの安全策を備えていますが、
    レートやコストに注意してください。

- 自動 .env ロード
  - パッケージは起動時にプロジェクトルートの .env/.env.local を自動で読み込みます。
  - テストや CI で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB 互換性
  - 一部の executemany や型バインドは DuckDB のバージョンに依存するため、
    プロダクション環境では DuckDB の適切なバージョンを固定してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py            — ニュース NLP（score_news）
  - regime_detector.py     — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理・営業日計算
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py      — J-Quants API クライアント（fetch/save）
  - news_collector.py      — RSS ニュース収集
  - quality.py             — データ品質チェック
  - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py               — 監査ログスキーマ初期化
  - etl.py                 — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン/IC/統計サマリー
- research/*（その他ユーティリティ等）
- その他: strategy/, execution/, monitoring/ （パッケージ公開用 __all__ に含む想定）

よくある質問
--------------
Q: OpenAI キーを複数プロセスで使いたいがセキュアな管理方法は？
A: 環境変数 OPENAI_API_KEY を CI / デプロイ環境のシークレット管理に格納してください。コードは api_key 引数で上書き可能です。

Q: テストで .env の自動読込を無効化したい
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: J-Quants の呼び出しで 401 が返ってきた場合は？
A: jquants_client はリフレッシュトークンから id_token を自動取得し 1 回リトライします。get_id_token を使って手動更新も可能です。

貢献・拡張
-----------
- 新しい ETL ジョブや品質チェックを追加する場合は kabusys.data.pipeline と kabusys.data.quality に実装を追加してください。
- LLM モデルを変えたい場合、kabusys.ai.news_nlp と kabusys.ai.regime_detector の _MODEL 定数や _call_openai_api 実装を調整してください（テスト用に _call_openai_api をモック可能です）。

ライセンス
----------
プロジェクトのライセンス情報はリポジトリの LICENSE を参照してください（この README 内では明示していません）。

以上です。必要であれば README に含めるコマンド例（docker / systemd / cron での定期実行例）や .env.example のテンプレートを追加で作成します。どの情報を補足しますか？