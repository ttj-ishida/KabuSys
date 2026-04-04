# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株を対象としたデータパイプライン、リサーチ（ファクター計算）、AI ニューススコアリング、監査トレーサビリティ、そして発注/実行監視を支援するモジュール群を含む Python パッケージです。本リポジトリは以下の目的を想定しています。

- J-Quants API からのデータ取得（株価、財務、JPX カレンダー）
- DuckDB を使ったローカルデータ保存と ETL パイプライン
- ニュース記事の収集・前処理と OpenAI を用いた銘柄センチメント算出
- ETF の移動平均などを用いた市場レジーム判定（LLM と価格情報の組合せ）
- ファクター計算、将来リターン・IC 計算などのリサーチユーティリティ
- 監査用テーブル（signal / order_request / executions）と初期化ユーティリティ
- 各種データ品質チェック

主要機能
--------
- data:
  - J-Quants API クライアント（レート制御、リトライ、自動トークンリフレッシュ）
  - ETL パイプライン（run_daily_etl 等）
  - market calendar 管理、ニュース収集、データ品質チェック、統計ユーティリティ
  - 監査テーブルの初期化（init_audit_schema / init_audit_db）
- ai:
  - news_nlp.score_news: 指定期間のニュースを銘柄別に集約して OpenAI でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA 乖離とマクロニュースセンチメントを合成して market_regime に書き込み
- research:
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC / 統計サマリ、Zスコア正規化
- config:
  - .env または環境変数を自動で読み込む Settings（自動ロードは無効化可能）

前提条件
--------
- Python 3.10+
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（ニュース RSS の安全なパースに使用）
- ネットワーク接続（J-Quants / OpenAI 等）

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - 開発環境であればプロジェクトルートに .git または pyproject.toml があることを推奨

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （パッケージは用途に応じて追加してください。プロジェクトをパッケージ化している場合は pip install -e . でインストールできます。）

4. 環境変数 / .env を用意
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須 / 任意）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行に必要）
  - KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード（実行モジュールで参照）
- OpenAI 関連
  - OPENAI_API_KEY: news_nlp / regime_detector で使用（引数で上書き可）
- 任意 / デフォルト有り
  - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG/INFO/...

例 (.env)
- .env.example としてプロジェクトに用意することを想定しています。最小例:
  JQUANTS_REFRESH_TOKEN=xxxx
  OPENAI_API_KEY=sk-xxxxx
  DUCKDB_PATH=data/kabusys.duckdb

使い方（基本例）
----------------

- 設定の読み出し
  from kabusys.config import settings
  print(settings.duckdb_path)

- DuckDB 接続を開いて日次 ETL を実行（J-Quants トークンが設定済みであること）
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI API キーが必要）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

  ※ score_news は内部で calc_news_window を使い、前日 15:00 JST ～ 当日 08:30 JST の記事を扱います。

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査データベース初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます

- リサーチ関数の利用例
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))

注意点 / 設計上の留意事項
-------------------------
- ルックアヘッドバイアス対策:
  - 多くの関数は date.today() を直接参照せず、明示的な target_date を要求します。バックテストでは必ず過去の date を渡してください。
- OpenAI API 呼び出し:
  - API エラー / レート制限時はリトライ・フェイルセーフ（多くのケースで 0.0 やスキップで継続）する実装です。必要に応じてテスト時はモックしてください。
- .env 自動読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を辿って .env/.env.local を自動で読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと便利です。
- DuckDB executemany の空パラメータに注意:
  - 一部関数（ai/news_nlp 等）は DuckDB の executemany に空リストを渡さないようにガードしています。API からの戻りが空のケースがあることを考慮してください。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py               - パッケージ定義（version）
- config.py                 - 環境変数・設定の管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py             - ニュースの集約・OpenAI による銘柄別スコアリング
  - regime_detector.py      - ETF (1321) MA とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py  - 市場カレンダー管理 / 営業日判定
  - etl.py                  - ETL 結果クラスの公開
  - pipeline.py             - ETL パイプライン（run_daily_etl 等）
  - stats.py                - zscore 等統計ユーティリティ
  - quality.py              - データ品質チェック
  - audit.py                - 監査ログ（DDL / 初期化）
  - jquants_client.py       - J-Quants API クライアント（取得 & 保存）
  - news_collector.py       - RSS フィード収集と前処理
- research/
  - __init__.py
  - factor_research.py      - モメンタム/バリュー/ボラティリティ等の計算
  - feature_exploration.py  - 将来リターン・IC・統計サマリ等
- monitoring / execution / strategy / (他)  
  - （本コードベースには monitoring/execution/strategy への参照がある想定。実装の追加により展開）

開発・テストのヒント
--------------------
- OpenAI 呼び出しや外部 API は単体テストでモックすることを推奨します。各 ai モジュールは _call_openai_api を内部に持っており、これを patch してテスト可能です。
- .env の自動ロードは便利ですが、CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して意図しない設定の混入を防いでください。
- DuckDB はインメモリ (":memory:") を指定して高速にユニットテストを行えます（例: init_audit_db(":memory:")）。

ライセンス / 貢献
-----------------
（この README ではライセンス表記は省略しています。プロジェクトに適切な LICENSE を追加してください。）

問い合わせ
----------
不明点や質問があればリポジトリの issue あるいはプロジェクト内の担当者にお問い合わせください。

--- 
この README はコードベースの現状（src/kabusys 以下）に基づいて作成しています。実行やデプロイの前に環境変数と必要パッケージを必ずご確認ください。