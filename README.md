KabuSys — 日本株自動売買／データプラットフォーム（README）
====================================

概要
----
KabuSys は日本株を対象としたデータパイプライン・リサーチ・AI評価・監査ログ・発注トレーサビリティを含む自動売買／データ基盤のライブラリ群です。本リポジトリは以下の機能群をモジュール化して提供します。

- データ収集（J-Quants API 経由の株価・財務・カレンダー）
- ETL（差分取得、保存、品質チェック）
- ニュース収集・NLP（OpenAI を用いたセンチメント評価）
- 市場レジーム判定（MA200 とマクロ記事センチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- ユーティリティ（カレンダー管理、統計、品質チェック 等）

主な特徴
--------
- Look-ahead バイアス対策（target_date を明示、datetime.today() を直接参照しない設計）
- DuckDB ベースのローカル DB 保存（冪等保存 / ON CONFLICT 処理を採用）
- J-Quants API 用のリトライ・レートリミット・自動トークン更新
- OpenAI（gpt-4o-mini）を JSON Mode で利用する NLU パイプライン（チャンク・バッチ化・リトライ）
- ニュース収集における SSRF/サイズ/XML インジェクション対策（URL 正規化、defusedxml、SSRF 検査 等）
- 監査テーブルとインデックスを備えた監査DB初期化ユーティリティ

必要条件（概略）
----------------
- Python 3.10 以上
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみでも動くモジュールもありますが、OpenAI／DuckDB 関連は必須で使用時にインストールしてください）

セットアップ手順
----------------

1. リポジトリをクローンしてプロジェクトルートへ移動
   - （本コードは pyproject.toml / .git を前提に自動 .env ロードを行います）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - （プロジェクトに requirements.txt/pyproject.toml がある想定）
   - pip install -r requirements.txt
   - または最低限:
     - pip install duckdb openai defusedxml

4. パッケージのインストール（開発モード）
   - pip install -e .

5. 環境変数設定（.env）
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO

   .env の記法は bash 風（export も可）、クォートやコメントにも対応しています。プロジェクトルートの .env と .env.local（後者が優先）を読み込みます。

使い方（主要な API と実行例）
----------------------------

（前提）Python REPL やスクリプト中で使用する例。DuckDB 接続は settings.duckdb_path で指定されたファイルを使うことを想定しています。

1) 設定読み出し
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.is_live 等を参照可能

2) ETL（データパイプライン）を日次で実行
- from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュースセンチメントスコア生成（AI）
- from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # ENV OPENAI_API_KEY を使用
  print(f"scored {count} symbols")

4) 市場レジーム判定
- from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

5) 監査DB 初期化（監査テーブルを新規 DB に作る）
- from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を用いて以降の監査ログ挿入を行う

6) カレンダー関連ユーティリティ（営業日判定等）
- from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  d = date(2026,3,20)
  is_open = is_trading_day(conn, d)

注意点 / 運用メモ
-----------------
- OpenAI 呼び出し: API 失敗時のフォールバック処理が実装されていますが、API キーの管理とコストに注意してください。api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants: rate-limit, retry, token refresh の機構があります。JQUANTS_REFRESH_TOKEN を .env に設定してください。
- 自動 .env 読み込み: パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）を走査して .env/.env.local を読み込みます。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して下さい。
- DuckDB の executemany に空リストを渡すと例外となるバージョンがあるため、モジュール側でチェック済みです。アプリ側で直接操作する場合は注意してください。

ディレクトリ構成（主要ファイルと説明）
------------------------------------

- src/kabusys/
  - __init__.py         — パッケージ初期化、バージョン定義
  - config.py           — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py       — ニュースを集約し OpenAI でセンチメント評価 → ai_scores へ書込む
    - regime_detector.py— MA200 とニュースセンチメントを合成して market_regime を更新
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存・認証・リトライ）
    - pipeline.py        — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - etl.py             — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - stats.py           — z-score 正規化など統計ユーティリティ
    - quality.py         — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py           — 監査ログテーブル定義／初期化、監査DBユーティリティ
    - news_collector.py  — RSS 収集・正規化・DB 保存ロジック（SSRF・サイズ制限対策あり）
  - research/
    - __init__.py
    - factor_research.py — モメンタム・ボラティリティ・バリュー等ファクター計算
    - feature_exploration.py — forward returns / IC / summary / rank 等の研究支援

よくある質問（FAQ）
------------------
Q: .env の読み込みが働かない
A: import 時にプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込みします。CWD が異なる場合でも動作するはずですが、特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で os.environ を用いて下さい。

Q: DuckDB の初期スキーマはどこで作る？
A: 本 README に記載の init_audit_db / init_audit_schema は監査用スキーマ初期化用です。その他のスキーマ（raw_prices, raw_financials, ai_scores 等）はプロジェクト別に schema 初期化コードが存在する想定です。ETL を初めて動かす前にスキーマ作成スクリプトを実行して下さい。

Q: OpenAI のレート制限・コストが心配
A: news_nlp と regime_detector はバッチ・チャンク・JSON Mode を採用し、冗長なトークン使用を減らす工夫をしています。テスト時は _call_openai_api をモックしてください。

貢献／開発
----------
- コーディング規約: type hints を活用、ルックアヘッドバイアスに注意した設計
- テスト: 各外部 API 呼び出しはモック可能な設計になっています（例: _call_openai_api の差し替え等）
- Issue / PR を歓迎します。セキュリティ（SSRF、XML）やデータ品質に関する修正は特に重要です。

以上。必要であれば README にサンプル .env.example、具体的な schema 作成 SQL、または Docker / systemd ベースの運用手順（cron ジョブやワーカ実行方法）を追記します。どの情報を追加しましょうか？