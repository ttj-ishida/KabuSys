KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・シグナル生成・監査（トレーサビリティ）を想定したライブラリ群です。  
主に以下領域を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（DuckDB に格納）
- ニュース収集（RSS）と LLM を用いたニュースセンチメント（銘柄ごと / マクロ）評価
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- 市場カレンダー管理（営業日判定など）
- 監査ログ（signal → order_request → execution を追跡する監査テーブル）初期化ユーティリティ
- データ品質チェックおよび ETL 実行の結果集計

特徴
----
- DuckDB ベースのローカルデータストア（デフォルト: data/kabusys.duckdb）
- J-Quants API に対するページネーション・レート制限・リトライ・トークン自動リフレッシュ対応
- OpenAI（gpt-4o-mini）を利用したニュース NLP（JSON Mode）でのセンチメント集計
- Look-ahead bias を避ける設計（内部で date.today()/datetime.today() を不用意に参照しない等）
- 冪等（idempotent）な DB 保存ロジック（ON CONFLICT / DELETE→INSERT のパターン）
- RSS 収集時の SSRF 対策や XML の安全パース（defusedxml）

セットアップ手順
--------------
前提:
- Python 3.9+（typing の一部表記を使用）
- ネットワーク接続（J-Quants / OpenAI / RSS 取得用）

1) 必要パッケージをインストール（最低限）
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / poetry 等があればそちらを使用してください）

2) パッケージのインストール（開発環境）
   - ソースルートで:
     - pip install -e .

3) 環境変数（.env ファイル）を用意
   プロジェクトルートに .env を作成すると自動で読み込まれます（.env.local は .env を上書き可能）。
   必要な主要環境変数（例）:
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN       : Slack 通知の Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 等で使用）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite 監視 DB（デフォルト data/monitoring.db）
   - KABUSYS_ENV           : environment (development / paper_trading / live)（デフォルト development）
   - LOG_LEVEL             : ログレベル (DEBUG/INFO/...)（デフォルト INFO）

   自動ロードを無効化する場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを抑制できます（テスト用）。

使い方（主要ユースケース）
-----------------------

※ すべての操作は Python スクリプトまたは REPL から実行できます。DuckDB 接続には duckdb.connect(path) を使用します。

1) DuckDB 接続の準備
   例:
   from datetime import date
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")

2) 日次 ETL を実行（株価 / 財務 / カレンダー・品質チェック）
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn, target_date=date(2026,3,20))
   # result は ETLResult オブジェクト（fetched/saved/quality_issues/errors 等を含む）

3) ニュースのセンチメントを算出（銘柄ごと）
   from kabusys.ai.news_nlp import score_news
   written = score_news(conn, target_date=date(2026,3,20))
   # OpenAI API キーは api_key 引数で渡すか OPENAI_API_KEY 環境変数を設定

4) 市場レジーム（マクロ + ETF MA200）を評価して保存
   from kabusys.ai.regime_detector import score_regime
   score_regime(conn, target_date=date(2026,3,20))
   # API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用

5) 監査ログ（audit）スキーマ初期化
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/audit.duckdb")
   # init_audit_schema を transactional=True で行うため安全に初期化される

6) ファクター計算 / 研究ユーティリティ
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   m = calc_momentum(conn, date(2026,3,20))
   v = calc_value(conn, date(2026,3,20))

設定・実装上の注意点
--------------------
- OpenAI 呼び出しは gpt-4o-mini（コード内では _MODEL で指定）を JSON Mode で使用しています。API レスポンスのパースやリトライが組み込まれていますが、API キーが未設定だと ValueError が発生します。
- J-Quants API の認証は refresh token → id token のフローをサポート。get_id_token() が利用され、401 発生時に自動でトークンを更新します。
- ETL / 保存関数は可能な限り冪等に設計されています（ON CONFLICT 等）。
- ニュース収集は SSRF 対策・圧縮対応・XML の安全パースを実装しています（defusedxml を使用）。
- デフォルトの DB パス等は kabusys.config.Settings で管理され、.env または環境変数で上書きできます。

主要モジュール一覧（簡易説明）
----------------------------
- kabusys.config
  - 環境変数の読み込み・設定管理。プロジェクトルートの .env / .env.local を自動ロード（無効化可）。
  - Settings クラスで各種設定値を参照可能。

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB への保存ユーティリティ）
  - pipeline: 日次 ETL 実行ロジック（run_daily_etl 等）
  - etl: ETLResult の再エクスポート
  - news_collector: RSS 収集と raw_news への保存ロジック
  - calendar_management: market_calendar 管理と営業日ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
  - audit: 監査ログスキーマの初期化 / init_audit_db

- kabusys.ai
  - news_nlp: 銘柄ごとのニュースセンチメント算出（score_news）
  - regime_detector: ETF（1321）MA200 とマクロニュースを組み合わせた市場レジーム判定（score_regime）

- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ 等の計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリ、ランク機能
  - data.stats より zscore_normalize を利用可能

ディレクトリ構成（ソースの主要箇所）
-----------------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research / その他の補助モジュール...

よくある質問 / トラブルシューティング
-----------------------------------
- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認してください。
  - パッケージはプロジェクトルート（.git または pyproject.toml）から .env を探索しています。

- OpenAI / J-Quants の API エラー:
  - ネットワーク・認証・レート制限に対するリトライ実装がありますが、長時間失敗する場合はキーやネットワークの確認を行ってください。

- DuckDB への書き込みでエラー:
  - schema が未作成の場合やカラム名不一致が原因のことがあります。ETL 実行前にスキーマ初期化スクリプトを用意してください（プロジェクトの別モジュールでスキーマ定義がある前提）。

貢献 / 開発メモ
----------------
- テストや CI を用意することを推奨します（外部 API 呼び出しはモック化）。
- OpenAI / J-Quants 呼び出しは差し替え可能な内部関数（_call_openai_api 等）を使っているため、ユニットテスト時にパッチできます。
- DB 周りは DuckDB を使用しているため、意図的に軽量で高速なローカル処理が可能です。

連絡先
------
リポジトリ管理者（またはプロジェクト README に記載の担当）へお問い合わせください。README にない運用ルールやデプロイ手順はプロジェクト固有のドキュメントを参照してください。

以上。必要であれば README のサンプル .env.example や簡易スキーマ初期化手順、実行スクリプトのテンプレート（cron / systemd / supervisor 用）なども追加で作成します。どの情報を追加しますか？