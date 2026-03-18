# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けユーティリティ群です。  
J‑Quants API や RSS ニュースを用いたデータ収集、DuckDB スキーマ定義・初期化、日次 ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な設計思想：
- 冪等性（DB への INSERT は ON CONFLICT で上書き/スキップ）
- トレーサビリティ（UTC タイムスタンプ、監査テーブル）
- 外部 API のレート制御とリトライ（J‑Quants クライアント）
- セキュリティ対策（RSS 收集時の SSRF 対策、defusedxml による XML パース防御）
- テスト可能性（トークン注入やネットワークオープナーの差し替えを想定）

バージョン: 0.1.0

---

## 機能一覧

- J‑Quants API クライアント
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）は UTC で記録し Look‑ahead Bias を防止

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス定義と順序考慮した DDL 実行

- ETL パイプライン
  - 差分更新（最終取得日から未取得分のみを取得）
  - backfill による後出し修正吸収
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース収集（RSS）
  - RSS から記事を収集して raw_news に保存
  - URL 正規化（utm 等除去）→ SHA‑256 ハッシュで記事 ID を生成（冪等化）
  - SSRF 対策、gzip サイズ上限、defusedxml による安全な XML パース
  - 銘柄コード抽出（4桁数字）と news_symbols への紐付け

- マーケットカレンダー管理
  - JPX カレンダーの差分更新ジョブ（先読み/バックフィル）
  - 営業日判定 / 前後営業日取得 / 期間内営業日リスト取得

- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル
  - 発注要求の冪等キー（order_request_id）や broker_execution_id（約定の冪等）を想定
  - 全 TIMESTAMP を UTC に固定可能

- データ品質チェック
  - 欠損データ、スパイク（前日比）、重複、日付整合性チェック
  - 問題は QualityIssue リストとして返され、重大度別に扱える設計

---

## セットアップ手順

前提
- Python 3.9+（コードは型ヒントに union 型などを使用）
- OS により DuckDB の動作要件に注意

1. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

2. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml

   プロジェクト配布が pyproject.toml / requirements.txt を提供していればそちらを使用してください。開発インストール例:
   - pip install -e .

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可）。
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: 通知先チャネル ID
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: monitoring 用 SQLite（デフォルト data/monitoring.db）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DB スキーマの初期化（DuckDB）
   - Python から直接初期化できます。

   例:
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

   監査ログ用 DB を別に作る場合:
   - python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/kabusys_audit.duckdb')"

---

## 使い方（主な API と実行例）

以下はライブラリ API を直接呼ぶ簡単な例です。実運用ではログ設定や例外ハンドリングを適切に追加してください。

1. DuckDB スキーマ初期化（再掲）
   - from kabusys.data.schema import init_schema
   - conn = init_schema("data/kabusys.duckdb")

2. 日次 ETL 実行
   - 日次 ETL は市場カレンダー→株価→財務→品質チェックを順に実行します。

   例:
   ```
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を指定しなければ今日
   print(result.to_dict())
   ```

   run_daily_etl は ETLResult を返します（フェッチ数・保存数・品質問題・エラー一覧を含む）。

3. RSS ニュース収集（raw_news 保存）
   - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   - results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)

   既定ソースは kabusys.data.news_collector.DEFAULT_RSS_SOURCES（例: Yahoo Finance のビジネスカテゴリ RSS）。

4. J‑Quants データ取得を直接使う
   - from kabusys.data import jquants_client as jq
   - conn = init_schema("data/kabusys.duckdb")
   - records = jq.fetch_daily_quotes(date_from=..., date_to=...)
   - jq.save_daily_quotes(conn, records)

   get_id_token() は内部で設定済みリフレッシュトークンを使って ID トークンを取得し、キャッシュします。fetch 系関数はページネーション対応。

5. カレンダー更新ジョブ（夜間バッチ）
   - from kabusys.data.calendar_management import calendar_update_job
   - saved = calendar_update_job(conn)

6. 品質チェックを単独で実行
   - from kabusys.data.quality import run_all_checks
   - issues = run_all_checks(conn, target_date=..., reference_date=..., spike_threshold=0.5)

---

## 重要な挙動メモ

- .env 自動読み込み
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を起点）を探索し .env → .env.local を順に読み込みます。
  - OS 環境変数は上書きされません（.env.local は override=True で既存環境変数を保護した上で上書き可能）。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で有用）。

- J‑Quants クライアント
  - レート制限: 120 req/min（内部でスロットリング）
  - リトライ: 最大 3 回（408/429/5xx に対して指数バックオフ）。429 の場合は Retry‑After ヘッダを優先。
  - 401 エラー時は refresh token を使って id_token を自動更新し 1 回だけリトライ

- ニュース収集の安全対策
  - URL のスキームは http/https のみ許可
  - リダイレクト先のホストがプライベートアドレスでないか事前に検査（SSRF 防止）
  - レスポンスサイズ上限（デフォルト 10 MB）、gzip 解凍後も上限検査
  - defusedxml を用いた XML パースで XML Bomb 等を防止

- DuckDB スキーマ
  - init_schema() は冪等でテーブル・インデックスを作成します
  - audit 用の init_audit_db / init_audit_schema は UTC タイムゾーン固定等の監査要件を適用します

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理（.env 自動読込等）
    - data/
      - __init__.py
      - jquants_client.py      # J‑Quants API クライアント（取得と保存）
      - news_collector.py      # RSS ニュース収集・前処理・保存・銘柄抽出
      - pipeline.py            # ETL パイプライン（run_daily_etl 等）
      - schema.py              # DuckDB スキーマ定義・初期化
      - calendar_management.py # マーケットカレンダー管理（営業日ユーティリティ）
      - audit.py               # 監査ログの DDL と初期化
      - quality.py             # データ品質チェック
    - strategy/
      - __init__.py            # 戦略関連コード（将来的に実装）
    - execution/
      - __init__.py            # 発注/約定関連コード（将来的に実装）
    - monitoring/
      - __init__.py            # 監視・メトリクス（将来的に実装）

---

## 開発メモ / テスト時の差し替えポイント

- jquants_client の network 呼び出し／ID トークン処理は引数注入やキャッシュ制御が可能なのでユニットテストでモックしやすい設計です（例: id_token を外部から渡す）。
- news_collector._urlopen はテスト時に差し替えて外部アクセスをモックできます。
- DuckDB は ":memory:" を指定してインメモリ DB を使用できます（テストで便利）。

---

必要に応じて README を拡張して、CI/CD、デプロイ手順、Slack 通知の設定方法、運用上の注意（レート制限の観測やバックフィルの方針）などを追記してください。質問や特定の使い方（例: ETL の cron 化、kabu ステーションとの連携フローなど）があれば具体的に教えてください。