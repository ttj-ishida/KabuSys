KabuSys
=======

日本株のデータプラットフォームと自動売買支援ライブラリ。  
ETL（J-Quants）による株価・財務・市場カレンダーの取得、ニュース収集とLLMによるニュースセンチメント評価、ファクター計算・リサーチ用ユーティリティ、監査ログ用スキーマ等を提供します。

主な特徴
-------
- J-Quants API 経由での差分 ETL（株価 / 財務 / カレンダー）、DuckDB への冪等保存
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄別センチメント）とマクロセンチメントによる市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と統計ユーティリティ（Zスコア、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）のスキーマ定義・初期化ユーティリティ
- .env ファイル / 環境変数からの設定読み込み（自動ロードはプロジェクトルート検出に基づく）

セットアップ
-----------

前提
- Python 3.10+（Union 型記法 Path | None 等を使用）
- ネットワークアクセス（J-Quants, OpenAI 等）

手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - その他プロジェクト固有の依存がある場合は pyproject.toml / requirements.txt を利用してください。
   - 開発用に編集可能インストール:
     - pip install -e .

4. 環境変数 (.env) を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env または .env.local を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨する最小の環境変数（例）
- JQUANTS_REFRESH_TOKEN=（必須: J-Quants のリフレッシュトークン）
- OPENAI_API_KEY=（LLM 呼び出しに必要）
- KABU_API_PASSWORD=（kabuステーション API を利用する場合）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi（任意）
- DUCKDB_PATH=data/kabusys.duckdb（DuckDB ファイルパス）
- SQLITE_PATH=data/monitoring.db（監視用 SQLite）
- LOG_LEVEL=INFO（ログレベル）
- KABUSYS_ENV=development|paper_trading|live

使い方（主要 API）
-----------------

準備: DuckDB 接続作成の例
- Python REPL / スクリプトから:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

ETL（デイリー）
- 日次 ETL を実行して株価・財務・カレンダーを取得・保存・品質チェック:
  - from kabusys.data.pipeline import run_daily_etl
  - res = run_daily_etl(conn, target_date=__import__("datetime").date(2026,3,20))
  - print(res.to_dict())

個別 ETL ジョブ
- run_prices_etl / run_financials_etl / run_calendar_etl を直接呼べます（テストや部分更新に便利）。

ニュース NLP（銘柄別センチメント）
- from kabusys.ai.news_nlp import score_news
- score_count = score_news(conn, target_date=__import__("datetime").date(2026,3,20))
- OpenAI API キーを明示する場合は api_key 引数に指定可能。

市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=__import__("datetime").date(2026,3,20))
- 内部で ETF (1321) の 200 日 MA 乖離とマクロセンチメント（LLM）を合成して market_regime テーブルへ書き込みます。

監査ログスキーマ初期化
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")  # :memory: も可

その他ユーティリティ
- ファクター計算: from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- リサーチ補助: from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary, rank
- 統計: from kabusys.data.stats import zscore_normalize
- データ品質チェック: from kabusys.data.quality import run_all_checks

注意点 / 設計上のポリシー
------------------------
- ルックアヘッドバイアス排除:
  - 日付の解決に datetime.today() / date.today() を直接使わず、target_date を明示する設計が多く採用されています。バックテストや再現性に注意して使用してください。
- 自動 .env 読み込み:
  - プロジェクトのルート（.git または pyproject.toml）を走査して .env / .env.local を読み込みます。
  - .env.local は .env を上書きします（OS 環境変数は保護されます）。
- フェイルセーフ:
  - LLM 呼び出し失敗や API 一時エラー時はフォールバック（0.0 など）で継続する実装が多いです。重大な失敗はログに記録されますが、処理を止めない設計が基本です。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE 等で冪等に実行します。ETL は差分更新 + バックフィル戦略を採用しています。
- セキュリティ:
  - RSS フェッチは SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）等を実施しています。
- LOG_LEVEL / 環境:
  - KABUSYS_ENV は development / paper_trading / live のいずれかで、settings で検証されます。

ディレクトリ構成（主要ファイル）
------------------------------
（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py                : パッケージ定義（version 等）
  - config.py                  : 環境変数 / 設定管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py              : ニュースセンチメントの取得・書込み（score_news）
    - regime_detector.py       : マクロ + MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py              : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   : 市場カレンダー管理・営業日判定
    - news_collector.py        : RSS 収集・前処理・保存
    - quality.py               : データ品質チェック（欠損/スパイク/重複/日付整合）
    - stats.py                 : 共通統計ユーティリティ（zscore_normalize）
    - audit.py                 : 監査ログ（テーブル DDL / 初期化）
    - etl.py                   : ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py       : ファクター計算（momentum / value / volatility）
    - feature_exploration.py   : 将来リターン / IC / summary 等
  - execution/                  : （発注／実行関連を想定するモジュール）
  - monitoring/                : （監視・プロセス管理等を想定するモジュール）
  - ai/、research/、data/ 等は上記のように役割が分かれています。

付録: よく使うコマンド例
-----------------------
- ETL を対話的に実行:
  - python -c "import duckdb; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); print(run_daily_etl(conn, target_date=__import__('datetime').date(2026,3,20)).to_dict())"

- ニューススコア付け:
  - python -c "import duckdb; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, __import__('datetime').date(2026,3,20)))"

- レジーム判定:
  - python -c "import duckdb; from kabusys.ai.regime_detector import score_regime; conn=duckdb.connect('data/kabusys.duckdb'); score_regime(conn, __import__('datetime').date(2026,3,20))"

- 監査 DB 初期化:
  - python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

サポート / 開発メモ
------------------
- テスト時に自動 .env 読み込みを無効にしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の呼び出しは外部 API を使用します。API キーやトークンの権限・レート制限にご注意ください。
- DuckDB に対する executemany の空リストバインドやバージョン差異に配慮した実装になっています。ローカルで使う DuckDB のバージョンを合わせてください。

ライセンス / 貢献
-----------------
- （この README にライセンス表記は含まれていません。プロジェクトの LICENSE を参照してください）
- 貢献は Pull Request を歓迎します。コードスタイル・テスト・ドキュメント整備を優先してください。

以上。README に含める追加の実行スクリプトや具体的な .env.example を用意したい場合は、その内容を教えてください。