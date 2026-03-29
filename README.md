KabuSys — 日本株自動売買 / データ基盤ライブラリ
=================================

概要
----
KabuSys は日本株のデータパイプライン、ファクター研究、ニュース NLP（LLM）によるセンチメント評価、そして監査付きの発注監視を目的とした Python モジュール群です。本リポジトリは以下の主要機能を提供します。

- J-Quants からの株価・財務・カレンダー等の差分 ETL と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理（raw_news 保存・銘柄紐付け）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）および市場レジーム判定
- 研究用途のファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal_events / order_requests / executions）用のスキーマ初期化ユーティリティ
- 環境変数による設定管理（.env 自動読み込み機能）

主な機能一覧
-------------
- data.jquants_client: J-Quants API 呼び出し、ページネーション、認証（リフレッシュ）、保存関数（raw_prices / raw_financials / market_calendar）
- data.pipeline: 日次 ETL（run_daily_etl）・個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）と ETL 結果データクラス（ETLResult）
- data.news_collector: RSS フィード取得、URL 正規化、SSRF 対策、raw_news 保存準備
- data.calendar_management: JPX カレンダー管理と営業日演算（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
- data.quality: データ品質チェック（欠損、スパイク、重複、日付不整合）と QualityIssue 定義
- data.audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
- data.stats: 汎用統計ユーティリティ（zscore_normalize）
- research.factor_research: モメンタム / ボラティリティ / バリュー計算関数
- research.feature_exploration: 将来リターン計算、IC（Spearman）、統計サマリ、ランク化
- ai.news_nlp: ニュースを銘柄ごとに集約して OpenAI に渡し ai_scores を生成（score_news）
- ai.regime_detector: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定（score_regime）
- config: .env 自動読み込み、必須環境変数チェック、settings オブジェクト

前提・依存
-----------
推奨環境：
- Python 3.10+（型注釈と一部の構文を使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
（実際の setup/pyproject は本コードに含まれていません。環境に合わせてインストールしてください。）

セットアップ手順
----------------
1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （他にログなどで使うパッケージがあれば追加でインストール）

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を配置すると自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
   - KABU_API_PASSWORD     : kabuステーション API パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID

   重要な任意設定（デフォルトあり）
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - OPENAI_API_KEY — OpenAI を使う機能を実行する場合に設定

4. データベース初期化（監査ログ等）
   - 監査ログスキーマを初期化する場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（簡単な例）
-----------------

- DuckDB 接続を作成して ETL を実行する（日次 ETL）
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコアを作成（OpenAI API キーが必要）
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key は環境変数 OPENAI_API_KEY でも可
  print(f"ai_scores に書き込んだ銘柄数: {written}")

- 市場レジーム判定（1321 MA200 + マクロニュース）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 研究用ユーティリティ
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  fwd = calc_forward_returns(conn, date(2026,3,20))
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")

注意点 / 設計上の要点
-------------------
- Look-ahead バイアス対策:
  - 多くのモジュール（news_nlp, regime_detector, ETL 等）は内部で datetime.today() を参照せず、外部から target_date を明示的に受け取る設計です。バックテストや再現性のために明示的な日付指定を推奨します。
- OpenAI 呼び出し:
  - gpt-4o-mini を JSON mode で利用し、レスポンスの検証やリトライ（429/ネットワーク/5xx）を実装しています。API エラー時はフェイルセーフ（0.0 など）で継続する設計です。
- .env の自動読み込み:
  - プロジェクトルート（.git or pyproject.toml）を探索して .env / .env.local を優先順で読み込みます。テスト時等に自動読み込みを無効化可能です。
- DuckDB への書き込みは冪等（ON CONFLICT）を基本としています。部分書き込みや部分失敗でも既存データの保護を考慮しています。
- テスト用の差し替えポイント:
  - OpenAI 呼出しや URL オープン関数などはユニットテストでモック可能な抽象化がされています（例: kabusys.ai.news_nlp._call_openai_api を patch）。

ディレクトリ構成
----------------
src/kabusys/
- __init__.py
- config.py                                — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                             — ニュース NLP（score_news）
  - regime_detector.py                      — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                       — J-Quants API クライアント（fetch / save）
  - pipeline.py                             — ETL パイプライン（run_daily_etl 等）
  - etl.py                                  — ETL インターフェース（ETLResult 再エクスポート）
  - news_collector.py                        — RSS 収集・前処理
  - calendar_management.py                   — JPX カレンダー管理
  - quality.py                               — データ品質チェック
  - stats.py                                 — 統計ユーティリティ
  - audit.py                                 — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py                       — ファクター計算（momentum/value/volatility）
  - feature_exploration.py                   — 将来リターン・IC・統計サマリ
- monitoring/ (※コードベースの一部が present であればここに監視関連を配置する想定)
- execution/ (発注関連モジュールがある場合に配置)

（上記は本コードベースで提供されている主要ファイル構成の抜粋です）

よくある質問（FAQ）
------------------
Q: OpenAI の API キーはどう渡すべきですか？
A: score_news / score_regime は api_key 引数を受け取ります。引数を省略すると環境変数 OPENAI_API_KEY を参照します。テストでは明示的に引数で渡すことをお勧めします。

Q: .env の自動読み込みを無効にしたい
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: DuckDB のスキーマはどこで定義されますか？
A: ETL や save_* 関数は既定のテーブルを前提としています。初回は ETL を走らせる前に別途スキーマ初期化関数（プロジェクト固有）を呼ぶか、提供されている DDL を実行してテーブルを作成してください。監査スキーマは data.audit.init_audit_schema / init_audit_db で初期化できます。

貢献・開発
-----------
- 新しい機能追加やバグ修正は PR を歓迎します。
- テスト: OpenAI や外部 API 呼び出しはモックしてユニットテストを作成してください。各モジュールは差し替え可能な内部関数を用意しています。

ライセンス
---------
（ここにライセンス情報を追加してください。未指定の場合はプロジェクトポリシーに従ってください。）

付録: 参考スニペット（DB 接続例）
---------------------------------
- DuckDB 接続（設定経由）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

以上。必要なら README に追記したい項目（例: 具体的な pyproject.toml / requirements.txt、DB スキーマ定義全文、運用手順）を教えてください。