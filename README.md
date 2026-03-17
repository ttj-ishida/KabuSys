# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、DuckDB スキーマ、監査ログなどを含むインフラ周りのコンポーネントを提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤ライブラリです。主な目的は次の通りです。

- J-Quants API からの市場データ（株価日足、四半期財務など）取得と DuckDB への冪等保存
- RSS フィードからのニュース収集と銘柄リンク付け
- ETL パイプライン（差分取得、バックフィル、カレンダー先読み）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（戦略→シグナル→発注→約定 のトレーサビリティ）用スキーマ

設計上の特徴：
- API レート制限・リトライ・トークン自動リフレッシュ対応（J-Quants）
- DuckDB に対する冪等性のある INSERT（ON CONFLICT を使用）
- RSS 収集での SSRF / XML攻撃対策・受信サイズ制限
- ETL は差分更新、バックフィル、品質チェックをサポート

---

## 機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存用関数: save_daily_quotes, save_financial_statements, save_market_calendar
  - レートリミッタ、リトライ、トークンキャッシュ、look-ahead bias 対策（fetched_at）

- data/news_collector.py
  - RSS フィード取得 (gzip 対応)、記事正規化、ID 作成（URL の正規化 + SHA-256）
  - SSRF 対策（リダイレクト検査、プライベートIP拒否）
  - raw_news への冪等保存（INSERT ... RETURNING）と news_symbols の紐付け

- data/schema.py / data/audit.py
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / init_audit_schema / init_audit_db 等で初期化

- data/pipeline.py
  - 日次 ETL（run_daily_etl）・個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 差分取得、バックフィル、品質チェック呼び出し

- data/quality.py
  - 欠損、スパイク、重複、日付不整合のチェックと QualityIssue 出力

- config.py
  - 環境変数読み込み（.env, .env.local の自動ロード）、Settings クラスで設定を提供
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に実行
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈や union 型表記に対応）
- Git（任意、プロジェクトルート検出に利用）

1. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージとして配布する場合は pyproject / requirements に記載してください）
   - 開発インストール（リポジトリルートで）
     - pip install -e .

3. 環境変数 / .env を用意
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨（例 .env）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知等に使用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境 / ログ
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須の環境変数（Settings で _require が使われているもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（これらが未設定の場合、settings.<property> を参照すると ValueError が発生します）

---

## 使い方（簡易ガイド）

最低限のワークフロー例を示します。詳細は各モジュールを参照してください。

1. DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

2. 日次 ETL を実行（J-Quants トークンは settings を利用して自動取得/リフレッシュ）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3. RSS ニュース収集（既知銘柄コードセットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: new_inserted_count}
```

4. 個別 API 呼び出し例（J-Quants）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_tokenを利用
records = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
```

5. 監査スキーマを追加で初期化する場合
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存の DuckDB 接続に監査テーブルを追加
```

ログ出力や詳細なエラー情報は Python の logging を通じて出力されます。必要に応じてログレベルを設定してください（環境変数 LOG_LEVEL または logging.basicConfig を使用）。

---

## ディレクトリ構成

プロジェクトは src/ 配下にパッケージを置く構成です。主要ファイル:

- src/
  - kabusys/
    - __init__.py
    - config.py                    - 環境変数・設定読み込み
    - data/
      - __init__.py
      - jquants_client.py          - J-Quants API クライアント + 保存ロジック
      - news_collector.py          - RSS ニュース収集・正規化・保存
      - pipeline.py                - ETL パイプライン（差分更新、品質チェック）
      - schema.py                  - DuckDB スキーマ定義・初期化
      - audit.py                   - 監査ログ（発注/約定トレース）スキーマ
      - quality.py                 - データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

プロジェクトルートに .env / .env.local（任意）や pyproject.toml があると自動でプロジェクトルートを検出します（config._find_project_root による）。

---

## 注意事項・運用上のポイント

- Python バージョン: 3.10 以上推奨（| 型表記等を使用しているため）
- 依存: duckdb, defusedxml（RSS の安全なパースに使用）
- J-Quants API のレート制限（120 req/min）を遵守するため、jquants_client 内に RateLimiter が実装されています。独自で大量リクエストを行う際は配慮してください。
- .env 自動ロードはプロジェクトルート検出に依存します。CI / テスト環境などで挙動を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用して手動で環境変数を設定してください。
- DuckDB の初期化は冪等です。既存テーブルは上書きされません。
- RSS の URL は http/https のみ許可。SSRF 保護処理があるため内部アドレスへのアクセスは拒否されます。

---

## 参考（ソース上の設計ノート）

- J-Quants クライアント: トークン自動リフレッシュ、HTTP 再試行（指数バックオフ）、ページネーション対応
- News Collector: URL 正規化 → SHA-256 の先頭32文字を記事 ID とする（冪等性）
- ETL: 差分取得 + backfill（デフォルト 3 日） + カレンダー先読み（デフォルト 90 日）
- Quality: 各チェックは QualityIssue を返し、致命的なものは呼び出し元が判断して対処する設計

---

README では主要な使い方と構成を記載しました。より詳しい API の使い方や運用手順は、各モジュール（src/kabusys/data/*.py）内の docstring を参照してください。追加でサンプルスクリプトや CI / デプロイ手順のテンプレートが必要であれば作成します。