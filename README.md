KabuSys — 日本株向けデータプラットフォーム & 自動売買補助ライブラリ
================================================================================

概要
----
KabuSys は日本株のデータ収集（J-Quants / RSS）、データ品質チェック、特徴量（ファクター）計算、AI を用いたニュースセンチメント評価、そして監査ログ（トレーサビリティ）を提供する Python パッケージです。DuckDB をデータ層に用い、ETL パイプラインや研究用途（リサーチ）、戦略開発のためのユーティリティ群を備えています。

主な設計方針：
- ルックアヘッドバイアスを防ぐため、日付参照は関数引数ベース（date 引数）で行う
- DuckDB と SQL を中心に効率的に処理
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・レート制御を含む安全実装
- ETL / 品質チェックは部分失敗を許容して問題を収集する（Fail-Fast ではない）

機能一覧
--------
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得（jquants_client）
  - レートリミット・リトライ・トークン自動更新を実装
- ETL パイプライン（data.pipeline）
  - 差分取得、保存（冪等）、品質チェック（data.quality）
  - 日次一括実行 run_daily_etl
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定 / 前後営業日の取得 / 夜間カレンダー更新ジョブ
- ニュース収集（data.news_collector）
  - RSS 収集、安全対策（SSRF/サイズ/XML攻撃対策）、正規化
- AI スコアリング（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini 等）を使った JSON Mode 呼び出し、リトライ・パース耐性あり
- 研究用ユーティリティ（kabusys.research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（calc_momentum 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- 統計ユーティリティ（data.stats）
  - Zスコア正規化（zscore_normalize）
- 監査ログ（data.audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

前提条件
--------
- Python 3.9 以上（typing の Union / pipe 型ヒントを利用）
- 必要な外部ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS 取得）

インストール
------------
（例: pip を利用する場合）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

3. パッケージをプロジェクトに組み込む場合は、ソースを PYTHONPATH に含めるかパッケージ化してインストールしてください。

環境変数 / .env の設定
-----------------------
パッケージは起動時にプロジェクトルート（.git または pyproject.toml がある階層）から .env を自動読み込みします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主に使用する環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector 等で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（もし利用するなら）
- KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

例 (.env)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

基本的なセットアップ手順
-----------------------
1. DuckDB データベースの準備
   - デフォルトパスは settings.duckdb_path（デフォルト data/kabusys.duckdb）。
   - Python から duckdb.connect(settings.duckdb_path) で接続します。

2. 監査ログ DB 初期化（監査専用 DB を分けたい場合）
   ```py
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   - init_audit_db はテーブル・インデックスを作成し、UTC タイムゾーンを設定します。

3. ETL の実行（例: 日次 ETL）
   ```py
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=None)  # target_date=None は今日
   print(result.to_dict())
   ```
   - run_daily_etl はカレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック を順に実行します。
   - settings.jquants_refresh_token により自動で J-Quants トークンを取得します（必要に応じて id_token を関数に渡せます）。

4. ニュース収集（RSS 取得）
   ```py
   from kabusys.data.news_collector import fetch_rss
   articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
   # 取得した articles を DB の raw_news に保存する処理は独自に実装してください
   ```
   - fetch_rss は安全対策（SSRF ブロック、gzip サイズチェック、XML 防御）を備えています。

AI（OpenAI）を使った利用例
--------------------------
- ニュースセンチメントスコア（ai_scores へ書き込み）
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が環境に必要
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- いずれも api_key を明示的に渡すことができます（api_key="sk-..."）。指定しない場合は環境変数 OPENAI_API_KEY を参照します。

リサーチ / ファクター計算の利用例
---------------------------------
- モメンタム / ボラティリティ / バリュー計算
  ```py
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  momo = calc_momentum(conn, target)
  vola = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

- Zスコア正規化
  ```py
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(momo, ["mom_1m", "mom_3m", "mom_6m"])
  ```

データ品質チェックの実行
-----------------------
- run_all_checks を呼んで問題一覧を取得できます（QualityIssue オブジェクトのリスト）。
  ```py
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意点 / トラブルシューティング
------------------------------
- OpenAI / J-Quants の API 呼び出しには課金やレート制限があります。環境や運用に応じたキー管理・制御を行ってください。
- .env 自動ロードはプロジェクトルート判定を行います。テスト環境で自動ロードを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に関する制約（バージョンによる）に配慮した実装となっていますが、運用環境の DuckDB バージョンに応じて挙動を確認してください。
- news_collector.fetch_rss は記事の DB への保存（raw_news への INSERT）は行いません。取得結果を正しいスキーマで保存する処理は呼び出し側で実装してください（セキュリティ注意）。

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（fetch / save）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - etl.py                 # ETLResult 再エクスポート
    - news_collector.py      # RSS 収集
    - calendar_management.py # マーケットカレンダー管理
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py     # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py # calc_forward_returns / calc_ic / factor_summary / rank

貢献・拡張
----------
- 新しいデータソースの追加（RSS ソース追加や J-Quants のフィールド対応）
- ETL の細かいスケジュール化やモニタリング（Slack 通知等）
- strategy / execution / monitoring 層の実装（パッケージはそれらのための基盤を提供）

ライセンス
---------
- （この README にはライセンス情報が含まれていません。実運用時はプロジェクトルートの LICENSE を参照してください。）

最後に
------
この README はコードベースから抽出した主要機能と利用手順の概要です。実際に運用環境で使う際は、環境変数・API キーの管理、ネットワーク制御、DuckDB のバックアップ・運用設計などを十分に行ってください。もし README に追加したい具体的な利用例（例えば CI/CD 用のスクリプト、Docker 化、監視設定など）があれば教えてください。必要に応じて追記します。