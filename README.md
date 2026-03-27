KabuSys — 日本株自動売買プラットフォーム（README）
====================================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買基盤のライブラリです。本リポジトリは次を提供します。

- J-Quants API を使った株価・財務・カレンダーの差分取得（ETL）
- DuckDB を使ったデータ保存・品質チェック・監査ログスキーマ
- ニュースの収集・NLP（OpenAI）による銘柄別センチメント算出
- 市場レジーム判定（MA とマクロニュースの合成）
- 研究用のファクター計算・特徴量探索ユーティリティ

このコードベースは「データ取得（Data）」「研究（Research）」「AI によるニュース分析（AI）」「監査／実行ロジック（Audit/Execution）」といったレイヤーに分かれています。Look-ahead バイアス回避や冪等性、API のレート制御・リトライなどに配慮した設計です。

主な機能
--------
- ETL パイプライン（data.pipeline.run_daily_etl）
  - 市場カレンダー、日足価格、財務データの差分取得・保存・品質チェック
- J-Quants API クライアント（data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
- ニュース収集（data.news_collector）
  - RSS フィード取得・正規化・raw_news への冪等保存（SSRF／XML 攻撃対策あり）
- ニュース NLP（ai.news_nlp）
  - 銘柄ごとのニュースをまとめて OpenAI（gpt-4o-mini）でセンチメント化し ai_scores テーブルへ保存
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）200日 MA 乖離とマクロニュースセンチメントを合成して market_regime を算出・保存
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク（急変）、日付不整合チェックを実装
- 監査ログ（data.audit）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
- 研究ユーティリティ（research）
  - ファクター計算（モメンタム/バリュー/ボラティリティ）、将来リターン・IC・統計サマリー

セットアップ手順
----------------

1. 前提
   - Python 3.10+ を推奨
   - ネットワークアクセス（J-Quants / OpenAI / 各 RSS）を利用できること

2. リポジトリをクローンして開発インストール（例）
   - git clone <repo-url>
   - cd <repo>
   - pip install -e ".[default]"  （依存パッケージを pyproject / requirements によって管理している場合はそちらに従ってください）
   - 必要な主なライブラリ
     - duckdb
     - openai
     - defusedxml
     - （標準ライブラリ以外の依存はプロジェクトの管理ファイルに従ってください）

3. 環境変数 / .env
   - 設定は環境変数、またはプロジェクトルートの .env / .env.local ファイルから自動読み込みされます。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須の主な環境変数（settings を参照）：
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API のパスワード（必要に応じて）
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
     - OPENAI_API_KEY         — OpenAI API キー（ai モジュール利用時）
   - オプション：
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            — 監視用 SQLite 等のパス（デフォルト: data/monitoring.db）

   例 .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

使い方（よく使う例）
-------------------

以下は Python REPL やスクリプトでの利用例です。実行前に環境変数や DB パス等を設定してください。

- DuckDB 接続を作成して ETL を実行（日次 ETL）
  ```
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())  # ETL 実行結果を確認
  ```

- ニュースセンチメントを計算して ai_scores に書き込む
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数に設定済みか、api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数を返す
  print("written:", written)
  ```

- 市場レジーム（market_regime）を算出
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # テーブルを作成して接続を返す
  ```

- J-Quants から上場銘柄リストを取得
  ```
  from kabusys.data.jquants_client import fetch_listed_info
  items = fetch_listed_info()
  print(len(items))
  ```

注意点 / 運用メモ
-----------------
- OpenAI 呼び出しは API コストとレートに注意して運用してください。news_nlp/regime_detector はリトライと失敗時のフォールバックを実装していますが、キー設定は必須です。
- ETL は差分取得・バックフィルの仕組みを持ちます。初回は大量データの取得が発生します。
- DuckDB に対する executemany の空リストバインド制約（バージョン差）に配慮した実装になっています。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。

ディレクトリ構成
----------------
主要ファイル・モジュールの概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py                      — score_news を公開
    - news_nlp.py                      — ニュースのセンチメント算出（OpenAI）
    - regime_detector.py               — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得・保存）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — 型再エクスポート（ETLResult）
    - news_collector.py                — RSS → raw_news の収集・前処理
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py           — 市場カレンダー・営業日計算・更新ジョブ
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum/value/volatility）
    - feature_exploration.py           — 将来リターン計算・IC・統計サマリ
  - monitoring/ (存在する場合: 監視/メトリクス用モジュール)
  - strategy/  (存在する場合: 戦略定義・信号生成)
  - execution/ (存在する場合: 発注ロジック・ブローカー連携)

（実際のファイルは src/kabusys 以下の各モジュールを参照してください）

開発に関する補足
----------------
- テスト容易性のため、OpenAI/API 呼び出しやネットワーク IO はモック可能な設計になっています（内部の _call_openai_api / _urlopen 等をパッチする想定）。
- DuckDB 接続は外部から注入するスタイル（関数引数）なので、インメモリ DB でのユニットテストが容易です（db_path=":memory:" を利用）。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンスはプロジェクトルートの LICENSE を参照してください。
- バグ修正や機能追加はプルリクエストで受け付けます。大きな変更は issue で相談してください。

最後に
------
この README はコードベースの主要な機能と使い方の概要を示したものです。詳細は各モジュールの docstring（ソース内のコメント）を参照してください。質問や補足があれば教えてください。