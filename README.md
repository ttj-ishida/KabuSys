# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants API からの市場データ取得、RSS ベースのニュース収集、DuckDB によるデータ保存・スキーマ管理、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（トレーサビリティ）などの機能を提供します。

---

## 主な特徴（機能一覧）

- 環境変数/設定管理
  - .env/.env.local からの自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得と検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
  - 実行環境（development / paper_trading / live）やログレベル設定

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ、レートリミット制御
  - 取得時刻（fetched_at）の UTC 記録、DuckDB への冪等保存（ON CONFLICT）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化（トラッキングパラメータ除去）、記事ID を SHA-256 から生成
  - SSRF 対策（スキーム検証 / プライベートIP 判定 / リダイレクト検査）、レスポンスサイズ制限
  - DuckDB への冪等保存（INSERT ... RETURNING / トランザクション）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を含むテーブル定義と初期化
  - インデックス、外部キー、制約を含むスキーマを冪等に作成
  - init_schema / get_connection API

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）: カレンダー、株価、財務データの差分取得・保存
  - 差分更新・バックフィル（デフォルト 3 日）・品質チェックの実行
  - 結果を ETLResult として返却（品質問題やエラーを収集）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 前後の営業日検索 / 期間内営業日取得
  - 夜間バッチで J-Quants から差分更新（calendar_update_job）

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比急変）、日付不整合（未来日付・非営業日のデータ）を検出
  - QualityIssue オブジェクトで詳細を返す。ETL 側は重大度に応じて対応可能

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 までのトレーサビリティ用テーブル群の初期化
  - UUID ベースの冪等キー、UTC タイムスタンプ、インデックス定義

---

## 必要な依存パッケージ

最低限必要なパッケージ（コード中で利用）:

- Python 3.9+
- duckdb
- defusedxml

インストール例:

```bash
pip install duckdb defusedxml
```

プロジェクト配布時に pyproject.toml / setup.cfg 等があれば、パッケージを editable インストールできます:

```bash
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 依存パッケージをインストール

   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数設定 (.env)

   プロジェクトルートに `.env` または `.env.local` を用意します。必須項目（例）:

   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu API 用パスワード
   - SLACK_BOT_TOKEN       : Slack ボットトークン
   - SLACK_CHANNEL_ID      : 通知先チャンネル ID

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

   自動ロードを無効にしたい場合（テスト等）:

   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. DuckDB スキーマ初期化

   Python REPL またはスクリプトでスキーマを初期化します。デフォルト DB パスは `.env` の DUCKDB_PATH（未設定時は data/kabusys.duckdb）です。

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   監査ログ専用の初期化:

   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しなければ今日を対象
print(result.to_dict())
```

- 個別 ETL ジョブの実行例（株価差分ETL）

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.data.pipeline import run_prices_etl

conn = get_connection("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026,1,10))
print(f"fetched={fetched}, saved={saved}")
```

- RSS ニュース収集と保存

```python
from kabusys.data.news_collector import fetch_rss, save_raw_news, run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")

# 単一ソースから取得
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
new_ids = save_raw_news(conn, articles)

# 複数ソース＋銘柄紐付けで実行（known_codes を与えると銘柄抽出を行う）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- マーケットカレンダーの夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

- 品質チェックの実行（ETL 内で自動的に呼ばれますが、単独実行も可能）

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for issue in issues:
    print(issue)
```

---

## 運用（推奨）

- 日次スケジュール（cron / Airflow 等）で run_daily_etl を実行し、データを継続的に収集。
- カレンダーは calendar_update_job を夜間で定期実行して先読み（デフォルト 90 日）しておくと営業日判定が安定。
- ニュース収集は頻度を決めて（例: 10〜30 分毎） run_news_collection を実行。
- 監査ログ（order_requests / executions 等）は実運用で必ず初期化し、発注フローからの追跡を有効にする。
- ログレベルや KABUSYS_ENV を適切に設定して、paper_trading / live を切り替え。

---

## ディレクトリ構成

（リポジトリの src 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定の読み込み/検証
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py             -- RSS ニュース収集・保存
    - schema.py                     -- DuckDB スキーマ定義・初期化
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        -- マーケットカレンダー管理/ユーティリティ
    - audit.py                      -- 監査ログ用スキーマ初期化
    - quality.py                    -- データ品質チェック
  - strategy/
    - __init__.py                   -- 戦略層（将来的に戦略実装を配置）
  - execution/
    - __init__.py                   -- 発注 / 実行関連（将来的に実装）
  - monitoring/
    - __init__.py                   -- 監視/メトリクス（将来的に実装）

---

## 参考 / 注意事項

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化可能です。
- J-Quants API はレート制限（120 req/min）や認証トークンのリフレッシュを考慮して実装されていますが、実運用では API 利用規約に従ってください。
- DuckDB のファイルはデフォルトで data/ 配下に作成されます。バックアップやアクセス制御を運用ポリシーに合わせて設定してください。
- ニュース収集では外部 RSS を取得するため、ネットワーク・セキュリティ上の注意（プロキシ、接続先検査等）を行ってください。

---

必要に応じて、README に含めたい追加情報（例: .env.example のテンプレート、運用例の systemd ユニット / cron サンプル、CI 設定）を教えてください。README をそれらに合わせて拡張します。