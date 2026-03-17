# KabuSys

日本株向け自動売買基盤（プロトタイプ） — データ取り込み、品質チェック、監査ログ、ニュース収集、ETL パイプライン等を提供する Python パッケージ。

主な狙いは J-Quants / kabuステーション 等の外部 API からデータを安全に取得して DuckDB に格納し、特徴量やシグナル・発注フローをトレース可能な形で管理することです。

## 機能一覧
- 環境変数 / .env 自動ロード（`kabusys.config`）
  - プロジェクトルートの `.env` / `.env.local` を自動で読み込み（無効化可能）
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限・リトライ・トークン自動リフレッシュ・ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- RSS ニュース収集（`kabusys.data.news_collector`）
  - RSS フィード取得（SSRF 防御、gzip 上限チェック、XML 安全パース）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等性を保証
  - raw_news / news_symbols へのバルク保存（トランザクション、INSERT ... RETURNING）
  - テキスト前処理、銘柄コード抽出（4桁）
- DuckDB スキーマ定義・初期化（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義、冪等な初期化 API（`init_schema` / `get_connection`）
- ETL パイプライン（`kabusys.data.pipeline`）
  - 日次 ETL のエントリポイント（`run_daily_etl`）
  - 差分更新、バックフィル、品質チェック（`kabusys.data.quality`）
  - カレンダー取得・調整機能（営業日補正）
- カレンダー管理（`kabusys.data.calendar_management`）
  - 営業日判定、前後営業日取得、バッチ更新ジョブ
- 監査ログ（`kabusys.data.audit`）
  - signal → order_request → executions のトレーサビリティ用テーブルと初期化 API
- 品質チェック（`kabusys.data.quality`）
  - 欠損・スパイク・重複・日付不整合検出
  - 問題は QualityIssue オブジェクトで収集し呼び出し元で判定可能

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | Y` シンタックスを使用）
- Git / 任意の仮想環境（推奨: venv）

1. リポジトリをクローン／チェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 必要最小パッケージ（例）:
     ```
     pip install duckdb defusedxml
     ```
   - その他プロジェクトで要求されるパッケージがあれば `requirements.txt` または `pyproject.toml` を確認してインストールしてください。

4. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成します。下記「環境変数」を参照してください。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化（例）
   - Python セッションやスクリプトから:
     ```py
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```

---

## 環境変数（例）
kabusys は .env または OS 環境変数から設定を読み込みます。主なキー:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。`kabusys.data.jquants_client.get_id_token` がこれを使って ID トークンを取得します。
- KABU_API_PASSWORD (必須)
  - kabuステーションAPIのパスワード（将来の実装で使用）
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, 値: development | paper_trading | live)
- LOG_LEVEL (任意, DEBUG/INFO/WARNING/ERROR/CRITICAL)

例 `.env`（最低限の必須キーを含む）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `from kabusys.config import settings` でアクセス可能です。
例:
```py
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## 使い方（主要ワークフロー）

以下は代表的な利用例です。プロジェクトに CLI は含まれていないため、スクリプトやジョブとして呼び出します。

1) スキーマ初期化
```py
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```py
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema していること
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())  # ETLResult の内容を確認
```

- 引数で `id_token` を注入することも可能（テスト容易性向上）。
- `run_daily_etl` は失敗したステップを記録して処理継続する設計です。戻り値の `errors` / `quality_issues` を監視してください。

3) ニュース収集ジョブ（RSS → raw_news, news_symbols）
```py
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規挿入数}
```

4) カレンダー夜間バッチ更新
```py
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

5) 監査テーブルの初期化（監査ログ用）
```py
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # 監査用テーブルを追加
```

---

## ディレクトリ構成

リポジトリ主要ファイル（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - calendar_management.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

README に示した主要 API は上記モジュールに実装されています。

（簡易ツリー）
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ pipeline.py
   │  ├─ calendar_management.py
   │  ├─ schema.py
   │  ├─ audit.py
   │  └─ quality.py
   ├─ strategy/
   ├─ execution/
   └─ monitoring/
```

---

## 運用上の注意 / トラブルシューティング
- J-Quants API はレート制限（120 req/min）があります。`jquants_client` は内部でスロットリングを行いますが、大量並列呼び出しは避けてください。
- トークン更新: 401 を受けた場合は一度だけ自動でリフレッシュしてリトライします。何度も 401 が発生する場合、リフレッシュトークンを確認してください。
- DuckDB ファイルのバックアップを定期的に行ってください。
- RSS 取得では SSRF / XML Bomb 等に対する対策を講じていますが、信頼できない URL の動的追加には注意してください。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動で `.env` を読み込まなくなります（ユニットテストや特殊環境で便利です）。
- ログは設定した `LOG_LEVEL` に従います。開発時は `DEBUG`、運用は `INFO` 推奨。

---

## 拡張 / 次のステップ（案）
- strategy / execution 層の具体的な戦略実装と kabuステーション実行ドライバの実装
- Slack 通知連携（設定は `config` にあるが通知ロジックは別実装）
- CI での DuckDB スキーマ検証テスト、ETL の回帰テスト
- Docker イメージ化、定期ジョブ (cron / Airflow / Prefect など) への組み込み

---

ご質問や README の追記・改善したい点があれば教えてください。使用したい具体的なワークフロー（例: 毎朝 6:00 に ETL を回す、Slack 通知を追加したい 等）があれば、それに合わせたサンプルスクリプトも提示します。