KabuSys
======

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどの機能を提供します。

主な目的
- J-Quants API から日次データを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と LLM（OpenAI）を使った銘柄別センチメント評価
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 研究（ファクター計算・前方リターン・IC 等）用ユーティリティ
- 発注〜約定までを追跡する監査ログ（DuckDB スキーマ）

機能一覧
- 環境 / 設定管理: 自動 .env ロード、settings オブジェクト（kabusys.config）
- J-Quants クライアント: 認証（refresh → id_token）、ページネーション、レート制御、保存用ユーティリティ（kabusys.data.jquants_client）
- ETL パイプライン: 日次 ETL（カレンダー・株価・財務）と品質チェック（kabusys.data.pipeline, quality）
- 市場カレンダー管理: 営業日判定／前後営業日／カレンダー更新ジョブ（kabusys.data.calendar_management）
- ニュース収集: RSS 取得・前処理・SSRF 対策・raw_news 保存（kabusys.data.news_collector）
- ニュース NLP: OpenAI を用いた銘柄別センチメント付与（kabusys.ai.news_nlp）
- 市場レジーム判定: ETF（1321）の MA とマクロニュースの LLM スコアを合成（kabusys.ai.regime_detector）
- 研究ユーティリティ: モメンタム/バリュー/ボラティリティ計算、前方リターン、IC／統計要約（kabusys.research）
- 監査ログ（audit）: signal → order_request → execution を追跡するスキーマ生成と専用 DB 初期化（kabusys.data.audit）
- 汎用統計関数: Z-score 正規化等（kabusys.data.stats）
- 自動環境変数ロード: プロジェクトルートの .env / .env.local を自動読み込み（kabusys.config）

セットアップ手順（開発環境）
1. 前提
   - Python 3.10 以上
   - 必要パッケージ: duckdb, openai, defusedxml 等（下記参照）

2. リポジトリをクローン / 作業ディレクトリへ移動

3. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて）pip install -e . で編集可能インストール

   主要依存例:
   - duckdb
   - openai
   - defusedxml

5. 環境変数 / .env を用意
   プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は .env 上書き）。  
   必須例（.env / 環境変数）:
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - KABU_API_PASSWORD=...  (kabuステーション関連)
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...

   オプション例:
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

   注意: 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで使用）。

6. DuckDB データベース用ディレクトリ作成
   - デフォルトの DUCKDB_PATH は data/kabusys.duckdb（settings.duckdb_path 参照）。
   - 必要ならディレクトリを作成しておく（save 関数は親ディレクトリを作成しますが注意）。

基本的な使い方（コード例）
- DuckDB 接続を作って ETL 実行（日次 ETL）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのセンチメントスコアリング（OpenAI 必須）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を使う
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数参照

- 監査 DB を初期化（監査用の別 DB を作る）

  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可

- J-Quants の生データ取得（テスト等）

  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  # get_id_token() は settings.jquants_refresh_token を使用
  data = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))

運用上の注意 / 設計に関するポイント
- Look-ahead bias 対策: モジュール内の多くの関数は date/target_date を引数に取り、date.today() を直接参照しない設計です。バックテスト等ではこの点を尊重してください。
- API 呼び出しはリトライ・バックオフ・レート制御を備え、フェイルセーフで動作する（多くの箇所で失敗時はデフォルト値を用いる）。
- ニュース収集では SSRF 対策・受信サイズ制限・XML インジェクション対策（defusedxml）を実施しています。
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます。テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（銘柄別センチメント）
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + 保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 結果クラス再エクスポート
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — マーケットカレンダー管理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（モメンタム / ボラティリティ / バリュー）
    - feature_exploration.py — 前方リターン / IC / 統計サマリー
  - research/ (補助モジュール群)
  - その他: strategy, execution, monitoring などのパッケージ名が __all__ に登場します（実装がある場合）

よくある質問（FAQ）
- Q: OpenAI キーはどこに置けばよいですか？
  A: 環境変数 OPENAI_API_KEY をセットするか、score_news / score_regime の api_key 引数で渡してください。

- Q: テスト実行時に .env の自動ロードを無効にしたい
  A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします。

- Q: DuckDB のファイルパスを変更したい
  A: 環境変数 DUCKDB_PATH を設定するか、settings.duckdb_path を参照して接続してください。

最後に
- この README はコードベースに含まれる docstring と設計ノートを元にまとめています。各モジュールの詳細は該当するソースファイル（kabusys/data や kabusys/ai 等）の docstring を参照してください。質問や改善要望があれば issue を作成してください。