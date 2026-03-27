KabuSys — 日本株自動売買プラットフォーム（README）
================================

概要
----
KabuSys は日本株を対象としたデータパイプライン／リサーチ／AI 支援の市場解析／監査ログ基盤を含むライブラリ群です。本リポジトリは以下を目的とします。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL
- ニュース収集と LLM を用いたニュースセンチメント（銘柄単位・マクロ）スコアリング
- ファクター計算・特徴量探索（リサーチ用ユーティリティ）
- 監査ログ（signal → order → execution）用の DuckDB スキーマ初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の特徴
- Look-ahead bias を防ぐため、日付取得に datetime.today()/date.today() の直接参照を避ける設計（多くの関数は target_date を引数に取ります）。
- DuckDB を主要なローカルデータベースとして使用し、ETL は冪等（ON CONFLICT / DO UPDATE）を前提に設計。
- OpenAI（gpt-4o-mini）を使った JSON Mode による堅牢なレスポンスパース・リトライ処理を実装。
- 外部 API 呼び出し部分はリトライ・レート制御・トークン自動リフレッシュを備える（J-Quants / OpenAI）。
- .env 自動ロード機構（プロジェクトルートに .git または pyproject.toml がある場合）を持ち、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

主な機能一覧
----------------
- data.jquants_client: J-Quants API クライアント（取得＋DuckDB 保存: raw_prices / raw_financials / market_calendar）
- data.pipeline: 日次 ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- data.news_collector: RSS 収集（fetch_rss）・前処理機能（SSRF 対策・トラッキング除去）
- data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）と QualityIssue モデル
- data.audit: 監査ログ（signal_events, order_requests, executions）スキーマ初期化ユーティリティ
- data.calendar_management: マーケットカレンダー操作（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
- data.stats: zscore_normalize（クロスセクション正規化ユーティリティ）
- ai.news_nlp: ニュースを銘柄ごとにまとめて LLM に投げる score_news（OpenAI 必須）
- ai.regime_detector: マクロセンチメントと ETF(1321) の MA 乖離を合成して市場レジーム判定（score_regime）
- research.*: ファクター計算（momentum / volatility / value）や将来リターン計算、IC 計算、統計サマリー

要件
----
- Python: 3.10 以上（PEP 604 の型注釈や一部構文を使用）
- ランタイム依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, logging 等）

セットアップ手順
----------------
1. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. ソースをインストール（開発モード）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env / .env.local を置くと自動で読み込まれます（起動時）。
   - 自動ロードを無効化したい場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必要な主要環境変数（例）
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL : kabu API ベース URL（オプション、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- OPENAI_API_KEY : OpenAI 呼び出しに使用（ai.score系の実行に必須、関数引数で上書き可能）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV : environment（development / paper_trading / live のいずれか、デフォルト development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）

基本的な使い方（例）
------------------

共通メモ:
- 多くの関数は duckdb.DuckDBPyConnection（例: duckdb.connect(path)）を第一引数に取ります。
- AI 関連関数（score_news, score_regime）は OPENAI_API_KEY を環境変数で参照しますが、api_key 引数で上書き可能です。

1) DuckDB 接続を作成
- Python:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
- Python:
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を指定して実行することも可能
  print(result.to_dict())

3) ニューススコア（銘柄単位）を作成する
- 必要: OPENAI_API_KEY を環境変数に設定
- Python:
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  num_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {num_written} ai_scores")

4) 市場レジームを判定する（マクロセンチメント + ETF MA）
- 必要: OPENAI_API_KEY
- Python:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))

5) 監査ログ DB 初期化（専用 DB）
- Python:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  # これで signal_events / order_requests / executions テーブルが作成されます

6) J-Quants データ取得と保存（ETL の内部で使用）
- Python:
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って取得
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)

注意点・運用メモ
----------------
- .env の自動読み込みはプロジェクトルート (.git / pyproject.toml) を基準に行います。テスト環境で自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なパースとリトライを行います。API の失敗時はフェイルセーフとしてスコアを 0.0 にフォールバックする設計箇所があります（ログ出力あり）。
- DuckDB executemany は空リストを受け付けないバージョンの互換性を考慮したコードが一部にあります。
- ETL は冪等性を重視しており、save_* 系関数は ON CONFLICT DO UPDATE を使って既存データを更新します。
- data.news_collector は SSRF 対策や応答サイズ制限、XML の安全なパース（defusedxml）を実装しています。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                      -- 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                   -- 銘柄ニュースの LLM スコアリング
  - regime_detector.py            -- マクロセンチメント合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             -- J-Quants API クライアント + DuckDB 保存
  - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
  - etl.py                        -- ETLResult の再エクスポート等
  - news_collector.py             -- RSS 取得・前処理（SSRF/サイズ対策含む）
  - quality.py                    -- データ品質チェック
  - calendar_management.py        -- マーケットカレンダー管理
  - stats.py                      -- zscore_normalize 等
  - audit.py                      -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py            -- momentum/volatility/value 計算
  - feature_exploration.py        -- 将来リターン・IC・統計サマリー

開発・貢献
----------
- バグ修正・改善提案は PR / Issue を歓迎します。設計ポリシー（Look-ahead bias 防止、冪等性、明示的な日付引数）を崩さない実装をお願いします。
- テストを追加する際は、外部 API 呼び出し（OpenAI / J-Quants / HTTP）はモックして実行可能にしてください（既存コードはテスト差し替えを想定した設計になっています）。

ライセンス
----------
- 本リポジトリにライセンスファイルが無い場合は、使用環境・運用ポリシーに従って適切なライセンスを追記してください。

付記（実装上の重要ポイント）
--------------------------
- 自動ロードされる .env のパースはシェル風の export KEY=val、クォート内のエスケープ、インラインコメントなどに対応しています。
- jquants_client は固定間隔スロットリング（120 req/min）とリトライ・トークン自動更新を備えています。
- news_collector は URL 正規化・トラッキング除去・記事 ID のハッシュ化（SHA-256 の先頭 32 文字）による冪等性を意図しています。
- research モジュールは外部ライブラリに依存しない純 Python 実装で統計解析を行います。

必要であれば、個別のモジュール（ETL 実行例、監査ログ初期化手順、OpenAI のレスポンスモック例など）についてサンプルコードやより詳しい手順を追加で作成します。どのトピックを優先されますか？