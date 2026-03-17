# KabuSys

日本株向け自動売買 / データパイプライン基盤ライブラリ

短い概要:
KabuSys は日本株マーケットのデータ収集・ETL・品質管理・監査ログ・ニュース収集などを行うための内部ライブラリ群です。J-Quants API から株価・財務・カレンダーを取得し、DuckDB に冪等的に保存します。ニュース収集は RSS を安全に処理し、記事と銘柄の紐付けを行います。監査用スキーマ/テーブルも提供し、戦略から約定までのトレーサビリティを確保します。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env ファイルおよび OS 環境変数から設定を自動読み込み（自動無効化フラグあり）
  - 必須設定の取得とバリデーション（env, log level など）

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日次株価（OHLCV）、四半期財務データ、JPXマーケットカレンダーの取得
  - レート制限（120 req/min）順守の RateLimiter 実装
  - リトライ（指数バックオフ）と 401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を回避
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードの取得・解析・前処理（URL除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証
  - defusedxml による XML 攻撃対策、SSRF 対策（スキーム検証・プライベートIP拒否）
  - レスポンスサイズ上限（デフォルト 10MB）、gzip 解凍後のサイズ検査
  - DuckDB への一括トランザクション挿入（INSERT ... RETURNING を使用）
  - テキストからの銘柄コード抽出（4桁数字、known_codes によるフィルタ）

- データスキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution / Audit 層の DuckDB スキーマ定義と初期化
  - テーブル、制約、インデックスを含む冪等な初期化関数

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分取得（最終取得日からの差分 + バックフィル）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次統合 ETL エントリポイント（run_daily_etl）

- カレンダー管理 (`kabusys.data.calendar_management`)
  - 営業日判定、前後の営業日取得、期間内の営業日リスト取得
  - 夜間バッチでのカレンダー差分更新ジョブ

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - signal_events / order_requests / executions 等の監査テーブル定義
  - 監査用 DB の初期化関数（UTC タイムゾーン固定）

- 品質チェック (`kabusys.data.quality`)
  - 欠損、重複、スパイク（前日比閾値）、日付不整合を SQL で検出
  - QualityIssue オブジェクトの返却（severity による判定）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈に PEP 604 などが使われています）
- OS 標準のネットワークアクセスが可能であること
- J-Quants API の認証情報を取得済みであること

1. リポジトリをチェックアウト
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 最低限の依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - パッケージとして編集可能インストール（プロジェクトのルートに pyproject/setup がある場合）:
     - pip install -e .

4. 環境変数 / .env を用意
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（少なくとも次を設定してください）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_api_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
   - オプション:
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - Python REPL などで:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     ```
   - audit 用 DB を別ファイルで用意する場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な API / ワークフロー）

以下はライブラリを直接呼び出す最小例です。実運用ではログ設定やエラーハンドリングを追加してください。

- 日次 ETL を実行して株価・財務・カレンダーを収集・保存する
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data import schema, pipeline

  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行（RSS から記事を収集して DB に保存、銘柄紐付け）
  ```python
  from kabusys.data import news_collector, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  # known_codes は有効な4桁銘柄リストのセット（例: {'7203','6758',...}）
  known_codes = {"7203", "6758"}
  stats = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(stats)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  saved = calendar_management.calendar_update_job(conn)
  print("saved", saved)
  ```

- 監査スキーマの追加初期化（既存接続に対して）
  ```python
  from kabusys.data import audit, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  audit.init_audit_schema(conn, transactional=True)
  ```

- J-Quants の個別 API 呼び出し（テスト目的）
  ```python
  from kabusys.data import jquants_client as jq
  # トークン省略時は settings.jquants_refresh_token を使用して id_token を取得します
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意点:
- run_daily_etl は内部で品質チェック（kabusys.data.quality）を呼び出します。品質エラーは ETL を中断せずに収集され、ETLResult に格納されます。
- J-Quants API 呼び出しはレート制限やリトライロジックを持っています。大量並列呼び出しは避けてください。

---

## ディレクトリ構成

パッケージは src 配下の `kabusys` に配置されています。主要ファイル・サブパッケージは以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py               — J-Quants API クライアント、保存ユーティリティ
      - news_collector.py               — RSS ニュース収集・保存
      - schema.py                       — DuckDB スキーマ定義と init
      - pipeline.py                     — ETL パイプライン（差分取得・統合ETL）
      - calendar_management.py          — 市場カレンダー管理・判定ユーティリティ
      - audit.py                         — 監査ログ（トレーサビリティ）スキーマ
      - quality.py                       — データ品質チェック
    - strategy/                          — 戦略層（空のパッケージ / 実装場所）
      - __init__.py
    - execution/                         — 実行（ブローカー連携）関連（空のパッケージ）
      - __init__.py
    - monitoring/                        — 監視/メトリクス（空のパッケージ）
      - __init__.py

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|... , デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効にする)

---

## 開発・テスト・貢献

- 自動読み込みされる .env をテストで無効化したい場合は、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB はインメモリモード（":memory:"）をサポートしているため、ユニットテストでの高速検証が可能です。
- news_collector の HTTP open を差し替えてテストするために、内部の `_urlopen` をモックできます。

---

## 補足（設計上のポイント）

- API レート制限やリトライ、トークン自動更新、取得時刻の記録など、実運用を想定した堅牢性・トレーサビリティ設計が盛り込まれています。
- DuckDB を用いたローカル分析 DB を前提に、すべての保存処理は冪等性を意識して実装されています（ON CONFLICT 句や INSERT ... DO NOTHING / RETURNING を使用）。
- ニュース収集は SSRF・XML 攻撃・圧縮爆弾などに対する複数の防御を持ち、安全にフェッチ・解析を行います。

---

必要であれば、README に含めるサンプル .env.example や CI 用のテスト実行方法、詳細な API ドキュメント（関数ごとの引数/戻り値）も追加できます。どの情報を優先して拡張しますか？