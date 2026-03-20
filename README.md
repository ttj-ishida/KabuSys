# KabuSys — 日本株自動売買基盤

概要
----
KabuSys は日本株のデータ取得・前処理・特徴量作成・戦略シグナル生成・発注監査までを想定した自動売買基盤のライブラリ群です。  
主に以下のレイヤで構成され、研究（research）と本番（execution）を分離した設計を採っています。

- データ収集・ETL（J-Quants からの OHLCV / 財務 / カレンダー・RSS ニュース）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution）
- ファクター計算（モメンタム・ボラティリティ・バリュー 等）
- 特徴量正規化・統合とシグナル生成（BUY / SELL の生成とエグジット判定）
- 発注監査ログ（トレーサビリティ用テーブル群）
- RSS ニュース収集と銘柄紐付け

主要機能
--------
- J-Quants API クライアント（ページネーション・レートリミット・リトライ・トークン自動更新）
- DuckDB スキーマ定義と初期化（冪等 DDL とインデックス）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算モジュール（prices_daily / raw_financials から算出）
- 特徴量構築（Z スコア正規化・ユニバースフィルタ・日付単位の UPSERT）
- シグナル生成（コンポーネントスコアの統合、Bear レジーム処理、エグジット判定）
- RSS ニュース収集（SSRF 対策・サイズ制限・記事ID 冪等化・銘柄抽出）
- カレンダー管理（営業日判定、next/prev_trading_day、夜間更新ジョブ）
- 発注監査（signal → order → execution のトレース用テーブル群）

動作環境・依存
--------------
主に標準ライブラリで実装されている部分が多いですが、実行には以下のパッケージが必要です（例）:

- Python 3.9+
- duckdb
- defusedxml

pip を使う場合の例:
```
pip install duckdb defusedxml
```

セットアップ手順
----------------
1. レポジトリをチェックアウトして editable install（オプション）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要なパッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

3. 環境変数 / .env ファイルを用意する  
   プロジェクトはルートの `.env` / `.env.local` を自動ロードします（ただしテストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します）。  
   必須の環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack 書き込み先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視系 SQLite DB パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development, paper_trading, live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   例 (.env.example)
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化  
   Python REPL またはスクリプトから実行:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

基本的な使い方
--------------

- 日次 ETL（市場カレンダー・株価・財務の差分取得）を実行する例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへ保存）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  cnt = build_features(conn, target_date=date(2024, 1, 31))
  print(f"upserted features: {cnt}")
  ```

- シグナル生成（signals テーブルへ保存）:
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals written: {total}")
  ```

- RSS ニュース収集ジョブの実行例:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄コードの集合（抽出のため）
  results = run_news_collection(conn, known_codes=set(["7203", "6758"]))
  print(results)
  ```

- カレンダー夜間更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

重要な設計・運用上の注意
-----------------------
- 環境( KABUSYS_ENV ) は "development" / "paper_trading" / "live" のいずれかに設定してください。settings.is_live 等で分岐できます。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は固定間隔スロットリングとリトライ・トークンリフレッシュを備えていますが、実運用では適切なスケジューリングを行ってください。
- ETL / feature / signal はルックアヘッドバイアスを避ける設計になっており、target_date 時点以前の情報のみを使用します。
- DuckDB のスキーマは冪等に作成されます。初回は init_schema() を呼び出してテーブルを用意してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定管理（.env 自動ロード / settings）
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（fetch/save 関数）
  - news_collector.py  — RSS 取得と raw_news / news_symbols 保存
  - schema.py         — DuckDB スキーマ定義・init_schema / get_connection
  - pipeline.py       — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — カレンダー管理・夜間更新ジョブ
  - audit.py          — 発注・約定の監査ログ用 DDL
  - stats.py          — zscore_normalize など統計ユーティリティ
  - features.py       — data.stats の再エクスポート
- research/
  - __init__.py
  - factor_research.py    — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py— 将来リターン / IC / サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル作成（build_features）
  - signal_generator.py    — generate_signals（BUY/SELL ロジック）
- execution/
  - __init__.py
  - (execution 層の実装ファイル)
- monitoring/ (パッケージとしては __all__ に含むが実体が増える想定)

開発・貢献
---------
- コードスタイルは可読性を重視しています。ユニットテストやモジュール単位の疎結合な設計を推奨します。
- 外部 API を呼ぶ箇所は id_token 注入やネットワークを抽象化しているため、テスト時はモック可能です（例: jquants_client._request, news_collector._urlopen 等をモック）。
- DB 操作はトランザクションと冪等保存（ON CONFLICT）で行っているため、再実行耐性があります。

補足
----
- このリポジトリは研究・プロダクション両用を想定したフレームワークであり、本番環境での運用には追加のリスク管理（資金管理、レート制限の厳密管理、監視・アラート等）が必要です。
- 外部サービス（J-Quants / kabu ステーション / Slack）に依存する機能は、それぞれの利用規約や API 制限を遵守してください。

以上。必要であれば README に含める具体的な .env.example や systemd / cron 用の起動例、CI テストコマンドなどを追加で作成します。どの情報を優先して追加しますか？