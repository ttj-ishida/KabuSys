# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ向け README。  
このドキュメントはプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買やデータ基盤（ETL / 品質チェック / 監査ログ）を支援する Python パッケージです。  
主に以下を目的とします：

- J-Quants API 等から市場データ（株価、財務、カレンダー）を取得して DuckDB に格納する ETL パイプライン
- RSS からのニュース収集と銘柄紐付け（raw_news, news_symbols）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・監査ログ用のスキーマ（監査トレーサビリティ）
- 将来的に戦略・実行・監視モジュールと連携可能な設計

設計上のポイント：
- J-Quants の API 制限（120 req/min）を守るレートリミッタ、再試行（リトライ）・トークン自動リフレッシュを内蔵
- DuckDB をデータストアに利用し、INSERT は冪等に実行（ON CONFLICT）
- RSS 収集は SSRF / XML-Bomb / メモリ DoS 等に対する防御を実装

---

## 主な機能一覧

- data.jquants_client
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、市場カレンダーの取得（ページネーション対応）
  - レート制御、リトライ、トークン自動リフレッシュ
  - DuckDB への保存（冪等）
- data.schema
  - DuckDB 用の包括的なスキーマ定義（Raw / Processed / Feature / Execution 層）
  - テーブル作成・インデックス作成を行う初期化関数
- data.pipeline
  - 差分更新ベースの ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - バックフィル（後出し修正吸収）や営業日調整を実装
- data.news_collector
  - RSS フィードの取得、前処理（URL 除去・空白正規化）、記事ID生成（SHA-256）
  - SSRF／gzip爆弾対策、DB への冪等保存、銘柄コード抽出・紐付け
- data.quality
  - 欠損・スパイク・重複・日付不整合のチェックを SQL ベースで実行
  - 問題は QualityIssue オブジェクトとして返却
- data.audit
  - シグナル → 発注 → 約定 に至る監査ログ用テーブルの定義と初期化
- 設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）、必須環境変数の抜け検出
  - 環境切替（development / paper_trading / live） とログレベル管理

---

## セットアップ手順

前提：
- Python 3.10 以上（型ヒントで `|` 演算子を使用）
- DuckDB を利用するためネイティブライブラリが必要（pip install duckdb で導入）

1. リポジトリをクローンして仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)

2. 依存パッケージをインストール
   - （プロジェクトに requirements.txt または pyproject.toml がある想定）
   - 例:
     - pip install -U pip
     - pip install duckdb defusedxml
     - pip install -e .   （パッケージ化されている場合）

   ※ 必要なパッケージ例：duckdb, defusedxml 等

3. 環境変数（.env）を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（CWD ではなくパッケージの __file__ を起点にプロジェクトルートを検出）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   必須（コードから判明する主な環境変数）:
   - JQUANTS_REFRESH_TOKEN  ← J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD      ← kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN        ← Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID       ← Slack チャンネル ID（必須）

   任意 / デフォルトあり:
   - KABUSYS_ENV            ← development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL              ← DEBUG/INFO/...（デフォルト: INFO）
   - KABU_API_BASE_URL      ← kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH            ← duckdb ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            ← monitoring 用 sqlite（デフォルト: data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマの初期化
   - Python REPL やスクリプト内で:
     ```
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログ（audit）テーブルを追加したい場合:
     ```
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（代表的なAPI・例）

以下は基本的な操作例です。実運用ではログ管理やエラーハンドリングを適切に行ってください。

1. DuckDB スキーマを作成して ETL を実行する（日次 ETL）
   ```
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn)  # target_date を指定しなければ今日
   print(result.to_dict())
   ```

   run_daily_etl は (1) カレンダー取得 (2) 株価差分取得 (3) 財務差分取得 (4) 品質チェック を順に実行します。各ステップは独立して例外処理されるため一部失敗しても他は継続します。

2. ニュース収集ジョブを実行する
   ```
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.news_collector import run_news_collection

   conn = init_schema("data/kabusys.duckdb")  # または settings.duckdb_path
   known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（抽出に使用）
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

   - RSS の既定ソースは `DEFAULT_RSS_SOURCES`（yahoo_finance 等）。sources を渡して任意の RSS 集合で実行できます。
   - fetch_rss は SSRF 防止・gzip サイズチェックを実装しています。

3. J-Quants API クライアントを直接使う
   ```
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))
   saved = save_daily_quotes(conn, records)
   ```

   - クライアントは内部でレート制御とリトライ、401 時の自動トークンリフレッシュを行います。

4. 品質チェックを個別に実行する
   ```
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=date(2025,1,1))
   for i in issues:
       print(i)
   ```

---

## 実装上の注意・設計メモ

- API レート制限：J-Quants の上限（120 req/min）を _RateLimiter で守ります。大量取得は時間を要します。
- リトライロジック：408/429/5xx に対する指数バックオフ。401 発生時は refresh token から id token を再取得して 1 回だけリトライします。
- ETL の差分更新：raw テーブルの最終日付を参照し、backfill_days（デフォルト 3 日）分遡って再取得することで API の後出し修正を吸収します。
- ニュース収集：記事ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。track param 除去・URL 正規化・SSRF 対策・gzip サイズチェックを実装。
- DB 保存は基本的に冪等（ON CONFLICT）／トランザクションを用いた安全な挿入を行います。
- 環境変数は .env/.env.local 経由で自動ロードされますが、テスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## ディレクトリ構成

以下は本コードベースの主要ファイル一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                         -- 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                       -- DuckDB スキーマ定義・初期化
      - jquants_client.py               -- J-Quants API クライアント
      - pipeline.py                     -- ETL パイプライン（差分更新・品質チェック）
      - news_collector.py               -- RSS ニュース収集・DB保存
      - audit.py                         -- 監査ログ（signal/order/execution）のDDL と初期化
      - quality.py                       -- データ品質チェック
      - audit.py
    - strategy/
      - __init__.py                      -- 戦略モジュール（将来的な実装場所）
    - execution/
      - __init__.py                      -- 発注・ブローカー接続用（将来的な実装場所）
    - monitoring/
      - __init__.py                      -- 監視 / メトリクス用（将来的な実装場所）

（上記は現状のファイル構成を要約したものです）

---

## 参考・トラブルシューティング

- 環境変数が足りない場合、kabusys.config.Settings のプロパティ呼び出しで ValueError が発生します。`.env.example` を参照して `.env` を準備してください。
- 自動 .env ロードはプロジェクトルート (.git または pyproject.toml があるディレクトリ) を探索して行います。パッケージ化後も .__file__ を基準に検出するため、CWD に依存しません。
- DuckDB への書き込みでスキーマが未作成だとエラーになるので、必ず init_schema を先に呼んでください。
- RSS 等の外部ネットワーク取得で接続エラーが出る場合、ネットワーク設定やファイアウォール、DNS の名前解決を確認してください。news_collector はプライベート IP へのアクセスを拒否するため、企業内環境でプロキシ等を設定していると挙動に影響します。

---

必要であれば README にサンプルスクリプト（cron / Airflow / systemd などでの運用例）や、CI / テストのセットアップ、さらに詳細な API リファレンス（各関数の引数・返り値の表）を追加できます。どの情報を優先して追加しますか？