KabuSys — 日本株自動売買 / データプラットフォーム
=================================

これは日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。DuckDB をデータ格納に使い、J-Quants API / RSS / OpenAI を組み合わせてデータ取得・品質チェック・ニュースセンチメント・市場レジーム判定・ファクター計算・監査ログ等を提供します。

主なポイント
- DuckDB を中心としたローカルデータレイヤ（raw_prices, raw_financials, raw_news, market_calendar, ai_scores, market_regime, audit テーブル群など）
- J-Quants API からの差分 ETL（株価 / 財務 / カレンダー）
- RSS ニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュース NLP（銘柄別センチメント）およびマクロセンチメント合成による市場レジーム判定
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions のトレース可能なテーブル定義）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）

機能一覧
- data:
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save_*）
  - market_calendar 管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS fetch_rss, preprocess / 保存ロジック）
  - 品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - score_news(conn, target_date) — 銘柄別ニュースセンチメントを ai_scores に書き込む
  - score_regime(conn, target_date) — ETF 1321 の MA200 とニュースのマクロセンチメントを合成して market_regime に書き込む
- research:
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config:
  - 環境変数自動ロード（.env / .env.local をプロジェクトルートから読み込む）
  - Settings クラス経由で設定値を取得（settings）

前提条件
- Python 3.10 以上（typing の | 記法を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

インストール（開発環境）
1. リポジトリをクローンしてパッケージをインストール（例）
   - pip install -e .
   - または pip install duckdb openai defusedxml など必要パッケージをインストール

環境変数（必須/推奨）
以下の環境変数は Settings クラスから参照されます。プロジェクトルートに .env（または .env.local）を置くと自動ロードされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注等を行う場合）
- SLACK_BOT_TOKEN — Slack 通知を行う場合の Bot Token
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）

任意（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると自動 .env 読込を無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等の SQLite パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）

セットアップ手順（例）
1. 必要な環境変数を .env に記述（.env.example を参考に作成）
2. DuckDB 用ディレクトリを作成（data ディレクトリ等）
3. 監査ログ DB を初期化（任意）:
   - Python から init_audit_db を呼ぶとテーブルを作成します

使い方（コード例）
- DuckDB 接続を取得して日次 ETL を実行する簡単な例:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI API キーが環境変数に設定されている前提）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")

- 市場レジーム判定:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（監査専用 DB を作る）:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

主要 API（抜粋）
- data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
- data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl
- data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- data.news_collector.fetch_rss, preprocess_text（RSS 収集）
- data.quality.run_all_checks（品質チェック）
- data.audit.init_audit_schema / init_audit_db（監査ログ初期化）
- ai.news_nlp.score_news（銘柄別ニューススコア）
- ai.regime_detector.score_regime（市場レジーム判定）
- research.calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（銘柄別スコア）
    - regime_detector.py     — マクロ＋MA200 によるレジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存処理
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - calendar_management.py — 市場カレンダー管理（営業日判定）
    - news_collector.py      — RSS 収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査テーブル定義・初期化
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — forward returns / IC / summary utilities
  - research/...             — 研究向け補助関数群

開発・テスト
- 環境変数は .env / .env.local をプロジェクトルートに置くことで自動読み込みされます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で便利です）。
- OpenAI 呼び出しはモジュール内で _call_openai_api をラップしているため、ユニットテストでは該当関数をモックしてテストできます（例: unittest.mock.patch）。

注意事項 / ベストプラクティス
- score_news / score_regime は外部 API（OpenAI）を利用します。API キーと使用量に注意してください。
- 実運用での自動発注を行う場合は設定（KABUSYS_ENV）を必ず確認し、paper_trading と live を適切に使い分けてください。
- DuckDB の executemany に空リストを渡せないバージョンに配慮した実装が含まれます（空チェックが入っています）。
- ETL は差分更新およびバックフィルを行うよう設計されています。データの過去取り扱い（バックテスト）では Look-ahead バイアスに注意してください。

貢献・ライセンス
- 質問・バグ報告・改善提案は Issue を立ててください。
- （ライセンスが別に定められている場合はその指示に従ってください）

この README はリポジトリに含まれるソースコード（config / data / ai / research 等）を参照してまとめた概要です。実際の運用では .env の設定、DB 初期化、J-Quants/OpenAI の認証情報管理を慎重に行ってください。