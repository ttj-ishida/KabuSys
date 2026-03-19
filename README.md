KabuSys — 日本株向け自動売買 / データプラットフォーム
=================================================

概要
----
KabuSys は日本株のデータ収集・ETL、ファクター計算、監査ログ・データ品質チェック、ニュース収集などを備えた自動売買プラットフォームのコアライブラリです。本リポジトリは主に以下を提供します。

- J-Quants API を用いた市場データ・財務データ・カレンダーの取得と DuckDB への冪等保存
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター（モメンタム / ボラティリティ / バリュー 等）計算および IC や統計要約
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- マーケットカレンダー管理（営業日判定 / 前後営業日の取得）
- 監査ログ（signal → order → execution のトレース）用スキーマと初期化ユーティリティ

特徴（主な機能）
----------------
- データ取得
  - J-Quants API クライアント（ページネーション・レートリミット・リトライ・トークン自動更新）
  - 株価日足 / 財務データ / JPX カレンダー取得
- ETL
  - 差分更新（最終取得日ベース）＋ backfill
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- リサーチ / 特徴量
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算 / IC（Spearman） / ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- ニュース収集
  - RSS 取得、URL 正規化、記事ID（SHA-256 先頭32桁）生成
  - SSRF 対策（スキーム検証・プライベートIP拒否・リダイレクト検査）
  - raw_news / news_symbols への冪等保存（チャンク挿入・トランザクション）
- 監査ログ
  - signal_events / order_requests / executions などの監査テーブル初期化ユーティリティ
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出、.env / .env.local の優先度）
  - 必須環境変数チェック

セットアップ手順
----------------

前提
- Python 3.9+（typing の記載に合わせてください）
- DuckDB を使用（Python パッケージ duckdb）
- ネットワークアクセス（J-Quants API / RSS など）

1. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクトをパッケージとして使う場合）pip install -e .

   ※requirements.txt は本リポジトリに含めていませんが、実運用ではロギング・HTTP クライアント等の依存を明記してください。

3. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を作成してください。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - SLACK_BOT_TOKEN: Slack 通知に使う bot トークン（必須 / 使用する場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須 / 使用する場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
   - オプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます（テスト時に便利）
     - DUCKDB_PATH / SQLITE_PATH: DBファイルパスの上書き

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで schema.init_schema() を呼ぶと DB とテーブルが作成されます。

   例:
   >>> from kabusys.data import schema
   >>> conn = schema.init_schema("data/kabusys.duckdb")
   >>> conn.close()

使い方（短いコード例）
--------------------

- 日次 ETL を実行する（J-Quants から差分取得して品質チェックまで実行）

  Python スクリプト例:
  ```
  from datetime import date
  import kabusys
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  # target_date を指定しない場合は今日が対象
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ニュース収集ジョブを実行する（既知銘柄セットを与えて銘柄紐付けまで）

  ```
  from kabusys.data import news_collector
  import kabusys
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄コードの集合（例: {'7203','6758',...}）
  res = news_collector.run_news_collection(conn, known_codes={'7203','6758'})
  print(res)
  conn.close()
  ```

- ファクター計算（リサーチ）例

  ```
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2024, 1, 4))
  volatility = calc_volatility(conn, date(2024, 1, 4))
  value = calc_value(conn, date(2024, 1, 4))
  ```

- J-Quants クライアント直接利用（取得 → 保存）

  ```
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

注意点 / 設計上の考慮
--------------------
- J-Quants API はレート制限（120 req/min）を遵守するため内部で固定間隔の RateLimiter を実装しています。
- API 呼び出しは冪等性（ON CONFLICT）とリトライ／バックオフ、401 時のトークン自動リフレッシュを備えています。
- DuckDB を用いることでローカルでの高速な分析と永続化が可能です。
- RSS の取得は SSRF や XML Bomb、巨大レスポンスに対する対策（スキーム検証、プライベートIP拒否、gzip 解凍上限など）が入っています。
- 設定は環境変数ベースで管理し、パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- 本コードは「研究・データ基盤」層を中心に実装されており、本番口座に対する発注（execution）部分はスキーマや監査の基盤のみが含まれています。発注用のブリッジ実装・リスク管理・実行ワークフローは別途実装が必要です。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（fetch/save）
  - news_collector.py       — RSS ニュース収集・保存
  - schema.py               — DuckDB スキーマ定義・init_schema
  - stats.py                — zscore_normalize 等の統計ユーティリティ
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - features.py             — 特徴量ユーティリティ公開（再エクスポート）
  - calendar_management.py  — マーケットカレンダー関連ユーティリティ
  - audit.py                — 監査ログ（signal/order/execution）初期化
  - etl.py                  — ETLResult の公開
  - quality.py              — データ品質チェック
- research/
  - __init__.py
  - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - factor_research.py      — モメンタム/ボラ/バリュー等のファクター計算
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

開発・拡張のヒント
-------------------
- DuckDB のスキーマは init_schema() で作成されます。既存 DB を更新する場合はマイグレーション戦略を検討してください。
- research モジュールは pandas 等へ依存していないため、データフローを把握しやすくユニットテストを書きやすい設計です。単体テストでは DuckDB の in-memory モード(":memory:") を使うと便利です。
- ニュースの銘柄抽出は単純な 4 桁数字マッチなので、誤抽出対策として known_codes を使ってフィルタリングしています。より高度な NLP を導入する余地があります。
- 監査スキーマは UTC タイムスタンプで記録する前提です。外部システムと連携する際は時差に注意してください。

ライセンス / コントリビューション
----------------------------------
本 README はコードベースの仕様説明を目的としたものです。実運用・商用利用時はライセンス条件・外部 API 利用規約（J-Quants 等）を確認してください。コントリビューションはプルリクエストを歓迎します。変更を行う際はユニットテストと簡単な動作検証を追加してください。

お問い合わせ
------------
コードや設計に関する質問があれば、用途や実行環境（Python バージョン、DuckDB バージョン、利用する外部 API の権限など）を添えてお問い合わせください。