KabuSys — 日本株自動売買基盤
===========================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買基盤のコアライブラリです。  
J-Quants API を用いたデータ ETL、ニュースの自然言語処理（LLM を使ったセンチメント評価）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

主な目的
- データ取得（株価・財務・市場カレンダー）と DuckDB への堅牢な保存
- ニュースを LLM でスコアリングして銘柄ごとの AI スコアを生成
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェックと監査ログによるトレーサビリティ

機能一覧
--------
- データ ETL（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足 / 財務データ / 上場情報 / JPX カレンダーの取得と DuckDB への冪等保存
  - レートリミット制御、トークン自動リフレッシュ、リトライ処理実装
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、前処理、SSRF・Gzip・XML 脆弱性対策
- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を用いた銘柄ごとのセンチメント評価（JSON mode）
  - チャンク処理、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントの合成による日次レジーム判定
  - OpenAI 呼び出しのフェイルセーフ（失敗時 macro_sentiment=0）
- 研究支援（kabusys.research）
  - モメンタム / ボラティリティ / バリュー 等のファクター算出
  - 将来リターン、IC 計算、ファクター統計・正規化ユーティリティ
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・next/prev_trading_day・calendar 更新バッチ
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue レポート）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化ユーティリティ
  - 監査テーブルの冪等初期化（init_audit_schema / init_audit_db）
- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）、環境変数ラッパー（settings）

セットアップ手順
----------------

前提
- Python 3.10+（型アノテーションで | を使用しているため）
- システムに DuckDB ライブラリ、openai SDK、defusedxml 等をインストールする必要があります。

推奨インストール例
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt がある場合はそれを使用してください:
   - pip install -r requirements.txt

3. パッケージを開発モードでインストール（リポジトリルートで）
   - pip install -e .

環境変数 / .env
- 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順で読み込みます。
  - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な必須環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client 用）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（実行/発注に使用）
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（必要に応じて）
- SLACK_CHANNEL_ID      : Slack チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector が参照）

任意 / デフォルト
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : SQLite／モニタリング用 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV           : 環境 ("development" / "paper_trading" / "live")（デフォルト development）
- LOG_LEVEL             : ログレベル（"DEBUG","INFO",...）

使い方（簡単な例）
-----------------

共通準備
- settings でパスを取得し DuckDB に接続する例:

  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

ETL を実行（日次 ETL）
- run_daily_etl を使って日次 ETL（株価・財務・カレンダー・品質チェック）を実行:

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

ニューススコアリング（LLM）
- ai.news_nlp.score_news により、raw_news → ai_scores へ書き込む:

  from kabusys.ai.news_nlp import score_news
  # api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print("書き込み銘柄数:", n_written)

市場レジーム判定
- ai.regime_detector.score_regime により market_regime テーブルへ日次判定を保存:

  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

監査ログデータベース初期化
- 監査用テーブルを DuckDB に作成する:

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

マーケットカレンダー関連
- is_trading_day / next_trading_day 等の利用例:

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

J-Quants クライアントの直接利用
- jquants_client の fetch/save 関数を直接使うことも可能です（ETL はこれらを利用しています）:

  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  saved = jq.save_daily_quotes(conn, quotes)

注意点 / ベストプラクティス
- Look-ahead bias の防止:
  - 各モジュールは target_date を明示して外部日付（today）参照を避ける設計です。バックテスト等では target_date を適切に渡してください。
- OpenAI 呼び出し:
  - API レートやエラーに備えたリトライ実装があります。OPENAI_API_KEY を設定するか api_key 引数を渡してください。
- 自動 .env 読み込み:
  - ローカルで .env.local を使うことで OS 環境変数を上書きできます（ただし OS 環境変数は protected されています）。
- DuckDB の executemany の取り扱い:
  - 一部コードは DuckDB のバージョン依存制約（空の executemany を避ける等）に対応しています。DuckDB を適切に更新しておいてください。

ディレクトリ構成
----------------

（主要ファイルを抜粋）

src/kabusys/
- __init__.py                      - パッケージ定義・バージョン
- config.py                        - 環境変数 / settings の管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py                     - ニュース NLP（score_news）
  - regime_detector.py              - 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py               - J-Quants API クライアント（fetch/save）
  - pipeline.py                     - ETL パイプライン（run_daily_etl 等）
  - etl.py                          - ETL 結果型の公開（ETLResult）
  - news_collector.py               - RSS ニュース収集ユーティリティ
  - calendar_management.py          - マーケットカレンダー管理
  - quality.py                      - データ品質チェック
  - stats.py                        - 統計ユーティリティ（zscore_normalize）
  - audit.py                        - 監査ログ（テーブル DDL / 初期化）
- research/
  - __init__.py
  - factor_research.py              - ファクター計算（momentum/value/volatility）
  - feature_exploration.py          - 将来リターン/IC/統計サマリー
- monitoring/ (存在する想定: モニタリング用コード)
- execution/, strategy/             (プレースホルダ: 発注 / 戦略関連モジュール)
- その他モジュール...

開発 / 貢献
-----------
- 新しい機能追加/バグ修正は PR を送ってください。
- コードはユニットテストで保護すること（OpenAI 呼び出し等はモックすること）。
- 外部 API キーやパスワードは .env.local で管理し、リポジトリにコミットしないでください。

ライセンス
----------
（この README はコードベースの一部として作成しています。実際のライセンスはリポジトリの LICENSE ファイルを参照してください。）

補足
----
README に記載していない細かいパラメータや関数の詳細は、各モジュール内の docstring を参照してください。必要であれば関数別の使用例や実運用向けの設定テンプレート（.env.example）も作成できます。ご希望あれば追記します。