KabuSys
=======

日本株向けのデータパイプライン・リサーチ・AI支援・監査を備えた自動売買／研究ユーティリティ群。
本リポジトリは主に以下を提供します。

- J-Quants API からの差分ETL（株価・財務・マーケットカレンダー）
- ニュース収集（RSS）と LLM によるニュースセンチメント集計（銘柄別 ai_score）
- 市場レジーム判定（ETF + マクロニュースの合成）
- 研究用ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ用スキーマ・初期化ユーティリティ（シグナル→発注→約定のトレース）

プロジェクト概要
----------------

KabuSys は日本株のデータ収集・品質管理・特徴量生成・AIスコアリング・監査ログを統合的に扱うためのライブラリ群です。
ETL は J-Quants API に準拠しており、DuckDB をローカル永続化に使用します。ニュースは RSS から収集し、OpenAI（gpt-4o-mini 等）を用いた JSON Mode によるセンチメント評価を行います。
設計上「ルックアヘッドバイアス」を避ける工夫（日時の扱い、DB クエリの排他条件など）が各所に施されています。

主な機能一覧
------------

- データ取得・保存
  - J-Quants からの株価日足 / 財務データ / 上場銘柄情報 / 市場カレンダー取得
  - id_token のキャッシュ・自動リフレッシュ、リトライ、レート制御実装
  - DuckDB へ冪等保存（ON CONFLICT ベース）

- ETL / パイプライン
  - run_daily_etl: カレンダー→株価→財務→品質チェックを一括実行
  - 個別の run_prices_etl / run_financials_etl / run_calendar_etl

- データ品質
  - 欠損、スパイク、重複、日付不整合のチェックと QualityIssue レポート

- ニュース収集・NLP
  - RSS 収集（SSRF 対策、gzip制限、URL 正規化）
  - news_nlp.score_news: 銘柄ごとのニュースをまとめて LLM に投げ、ai_scores に格納
  - LLM 呼び出しは堅牢なリトライ・パース検証を実装

- AI ベース判定
  - ai.regime_detector.score_regime: ETF(1321)の MA 乖離とマクロニュースセンチメントを合成して日次レジーム判定
  - 両モジュールとも OpenAI API を用い、JSON Mode で厳格にレスポンス検証

- 研究向けユーティリティ
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 将来リターン計算・IC（Spearman rank）・統計サマリー
  - zscore_normalize（クロスセクション正規化）

- 監査（Audit）
  - 監査テーブル DDL とインデックス定義
  - init_audit_schema / init_audit_db：監査用 DuckDB 初期化ユーティリティ

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 演算子等を使用）
- DuckDB, openai 等のパッケージを利用します

1) 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 依存パッケージのインストール（例）
   pip install duckdb openai defusedxml

   ※実際のプロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r requirements.txt または pip install . を行ってください。

3) 環境変数設定
   必須（ETL や AI 機能を使う場合）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知を使う場合
   - KABU_API_PASSWORD : kabu ステーション API を使う場合

   任意 / デフォルトあり:
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
   - OPENAI_API_KEY : OpenAI API（score_news / score_regime に引数で渡すことも可）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）

   .env 自動読み込み:
   - パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env および .env.local を自動読み込みします。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4) データベース初期化（オプション）
   - 監査 DB を独立させる場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（主要 API 例）
--------------------

以下は主要なユースケースの簡単な例です。関数の引数や戻り値は docstring を参照してください。

- DuckDB 接続作成（デフォルトパスを使用）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

- ニュースセンチメントのスコアリング（ai_scores へ書き込み）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("書き込み銘柄数:", n_written)

- 市場レジーム判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 研究用ファクター計算
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- 監査スキーマ初期化（既存の接続へDDLを追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

テスト・開発向け注意点
- OpenAI 呼び出しは内部で _call_openai_api を経由しており、ユニットテストでは unittest.mock.patch で差し替え可能（news_nlp._call_openai_api, regime_detector._call_openai_api）。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。
- settings オブジェクト経由で設定値にアクセスできます（例: settings.jquants_refresh_token）。

ディレクトリ構成
----------------

src/kabusys/
- __init__.py
- config.py                         : 環境変数 / .env 読み込み・設定オブジェクト
- ai/
  - __init__.py
  - news_nlp.py                      : ニュース NLP（score_news）と OpenAI 連携ロジック
  - regime_detector.py               : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                : J-Quants API クライアント + DuckDB 保存ロジック
  - pipeline.py                      : ETL パイプライン（run_daily_etl 等）
  - etl.py                           : ETLResult の公開
  - news_collector.py                : RSS 収集・保存ロジック
  - calendar_management.py           : 市場カレンダー管理（is_trading_day 等）
  - stats.py                         : zscore_normalize 等の統計ユーティリティ
  - quality.py                       : データ品質チェック（check_missing_data 等）
  - audit.py                         : 監査テーブル DDL / 初期化関数
- research/
  - __init__.py
  - factor_research.py               : calc_momentum / calc_value / calc_volatility
  - feature_exploration.py           : calc_forward_returns / calc_ic / factor_summary / rank
- research/... (ファイル群)
- その他モジュール（strategy, execution, monitoring 等はパッケージ公開対象一覧に含まれますが、ここで提供されるのは data/research/ai 中心のユーティリティです）

追加の設計・運用メモ
-------------------
- ルックアヘッドバイアス対策: 多くの関数が内部で date.today() を参照せず、引数で date を受け取る設計になっています。バックテスト等で過去日時を使う際に便利です。
- リトライ・レート制御: J-Quants と OpenAI の呼び出しは再試行と指数バックオフ、ステータスコードに基づく分岐を実装しています。
- セキュリティ: news_collector は SSRF 対策、XML の defusedxml、レスポンスサイズ上限などを備えています。

免責・今後の拡張
----------------
- 本リポジトリは実際の発注（ブローカー連携）を含まない調査・データ基盤部分が中心です。実際の売買を行う場合は別途ブローカー接続の実装と厳格なテスト・監査が必要です。
- 実運用では secrets の管理（安全な Vault 等）・モニタリング・リカバリ手順の整備を推奨します。

何か不明点や README に追加してほしい内容があれば教えてください。