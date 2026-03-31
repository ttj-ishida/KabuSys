KabuSys — 日本株自動売買プラットフォーム（README）
=============================================

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ、AI ベースのニュース解析、監査ログ、ETL、及び市場レジーム判定などを含むライブラリ群です。  
主に DuckDB をデータストアとして利用し、J-Quants API から市場データを取得、OpenAI（gpt-4o-mini 等）でニュースセンチメントを解析し、ファクタ計算や品質チェック、監査ログ管理までを行うことを目的としています。

主な機能
--------
- データ取り込み（J-Quants API 経由）
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
- ETL パイプライン
  - 差分取得、冪等保存、品質チェック（欠損・スパイク・重複・日付整合性）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- ニュース収集・NLP（OpenAI）による銘柄別センチメント算出
  - ニュース収集（RSS）→ raw_news への冪等保存
  - gpt-4o-mini を用いた銘柄別センチメント（score_news）
- 市場レジーム判定
  - ETF（1321）の MA 差分とマクロニュースセンチメントを合成して市場レジームを算出（score_regime）
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン / IC / 統計サマリー等の補助関数
- データ品質チェックモジュール（quality）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを含む監査スキーマの初期化・管理
- 環境・設定管理（自動 .env ロード、settings）

前提・必要環境
---------------
- Python 3.10 以上（typing の | 記法などを使用）
- DuckDB
- OpenAI Python SDK
- defusedxml
- （ネットワーク接続）J-Quants API, OpenAI API へのアクセス

インストール（開発環境）
-----------------------
1. 仮想環境作成・有効化（推奨）
   - 例（Unix/macOS）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
2. パッケージをインストール
   - setup.py/pyproject.toml がある前提で editable install:
     ```
     pip install -e .
     ```
   - 必要な外部ライブラリ（例）
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

環境変数・設定
--------------
KabuSys は .env / .env.local を自動でプロジェクトルート（.git または pyproject.toml を基準）から読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで使用）
- KABU_API_PASSWORD: kabu API のパスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack 設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite path（監視等で使用）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

セットアップ手順（簡易）
-----------------------
1. 必要なパッケージをインストール（上記参照）
2. プロジェクトルートに .env を作成し必要なキーを設定
3. DuckDB データベースを作る（ライブラリが自動でファイルを作成する機能あり）
4. 必要に応じて監査DBの初期化:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
5. 日次 ETL を実行してデータを収集:
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

使い方（主要 API 例）
--------------------

- DuckDB 接続の作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL の実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  ```

- ニュースセンチメントの算出（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # conn は DuckDB 接続、OPENAI_API_KEY は環境変数または api_key 引数で指定
  n = score_news(conn, target_date=date(2026,3,20))
  print("scored stocks:", n)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査 DB 初期化（別 DB に分けたい場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/monitoring_audit.duckdb")
  ```

- 研究用関数（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意・トラブルシュート
---------------------
- 環境変数が未設定の場合、多くの関数が ValueError を発生させます（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY）。エラーメッセージに従い .env を用意してください。
- OpenAI 呼び出しは失敗時にフェイルセーフ（スコア 0.0 など）を取る実装の箇所が多くありますが、APIキーと割当クォータを必ず確認してください。
- DuckDB の executemany はバージョン依存で空リストを渡せない箇所があるため、関数は空チェックを実装しています。ライブラリの実行時にエラーが出たら DuckDB バージョンを確認して下さい。
- .env 読み込みはプロジェクトルートの判定（.git または pyproject.toml）に依存します。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主なモジュールと概要です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py (パッケージ初期化、__version__)
  - config.py (環境変数・設定管理、.env 自動ロード、Settings)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP / score_news)
    - regime_detector.py (市場レジーム判定 / score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント + DuckDB 保存関数)
    - pipeline.py (ETL の中核、run_daily_etl 等、ETLResult)
    - etl.py (ETLResult 再エクスポート)
    - calendar_management.py (市場カレンダー管理・判定)
    - news_collector.py (RSS 収集、前処理、SSRF 対策等)
    - quality.py (データ品質チェック)
    - stats.py (統計ユーティリティ、zscore_normalize)
    - audit.py (監査ログスキーマ作成、init_audit_db)
  - research/
    - __init__.py
    - factor_research.py (Momentum/Value/Volatility 等)
    - feature_exploration.py (将来リターン・IC・統計サマリ)
  - ai/* と data/*, research/* の各モジュールはそれぞれ独立して利用可能です。

開発に関する方針・設計上の注意
-----------------------------
- Look-ahead bias 対策: 内部実装は date.today()/datetime.today() を直接参照せず、target_date を明示して処理します（バックテストでの公平性保守）。
- 冪等性: ETL 保存処理は基本的に ON CONFLICT DO UPDATE / DO NOTHING を用いて冪等化されています。
- フェイルセーフ設計: 外部 API 呼び出し失敗時には無効値でフォールバックして処理継続する箇所が多くあります（ログに注意）。
- セキュリティ: news_collector は SSRF 対策や XML の安全パーサを使用しています（defusedxml 利用）。

ライセンス・貢献
----------------
- この README ではライセンス情報は含めていません。リポジトリに LICENSE ファイルがあればそちらを参照してください。  
- 貢献時はコードスタイルや既存の設計方針（Look-ahead bias 回避、冪等性、テスト可能性）に従ってください。

補足
----
README に書ききれない細かな挙動（例: 各関数の引数仕様、戻り値の詳細、ログ・エラーハンドリングの挙動）はソース内ドキュメンテーション（docstring）に記載されています。必要な箇所の docstring を参照してください。

必要であれば、この README をプロジェクトの pyproject.toml / setup 情報に合わせて具体化（インストール手順や依存関係の正確な一覧、サンプル .env.example のテンプレート追加など）します。どの部分を詳しく書き起こすか教えてください。