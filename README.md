# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。J-Quants API や RSS ニュース、DuckDB を用いてデータ取得・保存・品質チェック・監査ログまでをカバーするコンポーネント群を提供します。

主な用途は以下のとおりです。
- J-Quants からの株価・財務・マーケットカレンダー取得（差分取得・ページネーション対応）
- RSS からのニュース収集と銘柄紐付け（冪等保存）
- DuckDB ベースのスキーマ初期化・ETL パイプライン（差分更新・バックフィル）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定・next/prev/trading day）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

---

## 機能一覧

- 環境設定
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須環境変数は Settings 経由で参照可能（未設定時は例外）

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーを取得
  - レート制限遵守（120 req/min）・リトライ（指数バックオフ）・401 時の自動トークンリフレッシュ
  - データ取得時に fetched_at を UTC で付与
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得して前処理（URL 除去、空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性確保
  - defusedxml を使った安全な XML パース、SSRF 対策、受信サイズ制限
  - raw_news / news_symbols へのバルク保存（トランザクション・INSERT ... RETURNING）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層を含む DuckDB スキーマ定義
  - init_schema() で初期化（冪等）。インデックス作成も含む

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新、バックフィル、品質チェックの実行と結果を ETLResult で返却

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、期間内営業日取得
  - 夜間バッチでカレンダー更新（calendar_update_job）

- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合のチェックを SQL ベースで実行
  - QualityIssue オブジェクトで詳細を返却

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルを提供
  - init_audit_schema / init_audit_db による初期化（UTC タイムゾーン固定）

---

## セットアップ手順

前提: Python 3.9+（コードは型ヒントで | を使っているため 3.10 以降を想定している箇所もありますが、必要に応じて適合させてください）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - defusedxml
   - 例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数を用意
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただしテスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須となる主な環境変数:
     - JQUANTS_REFRESH_TOKEN  (J-Quants リフレッシュトークン)
     - KABU_API_PASSWORD      (kabu API のパスワード)
     - SLACK_BOT_TOKEN        (Slack 通知用ボットトークン)
     - SLACK_CHANNEL_ID       (通知先チャンネル ID)
   - オプション:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL (kabu API のベース URL) — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH, SQLITE_PATH

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=your_kabu_pwd
   SLACK_BOT_TOKEN=xoxb-xxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. スキーマ初期化
   - Python REPL かスクリプトから:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```
   - 監査ログ用 DB を別途初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主な API と例）

以下は代表的な使い方例です。実際はアプリケーションの要件に合わせて組み合わせてください。

- 設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live)
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 省略で今日を対象に実行
print(result.to_dict())
```

- カレンダー夜間バッチ更新
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出に利用する有効な銘柄コードの集合（例: 上場銘柄リスト）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

- J-Quants による直接データ取得（テストや詳細制御用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()
rows = fetch_daily_quotes(id_token=token, code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 環境変数と自動読み込みの挙動

- 自動読み込み順:
  1. OS 環境変数
  2. .env（プロジェクトルート）
  3. .env.local（上書き可）

- 自動読み込みを無効化:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動ロードを停止します（テスト時に利用）。

- 設定の検証:
  - settings.env は "development" / "paper_trading" / "live" のいずれかである必要があります。
  - settings.log_level は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" のいずれかである必要があります。

---

## セキュリティ / 設計上の注意点

- jquants_client:
  - API レート制限（120 req/min）を守るため固定間隔レートリミッタを実装。
  - リトライ（最大 3 回、指数バックオフ）、401 時の自動トークンリフレッシュを備えています。
  - データは fetch 時に fetched_at を UTC で付与し、Look-ahead Bias を防止。

- news_collector:
  - defusedxml を利用して XML 攻撃を防止。
  - SSRF 対策: スキーム検証（http/https のみ）、リダイレクト先のプライベート IP 検査。
  - レスポンスサイズの上限を設けてメモリ DoS を防止。

- DB 操作:
  - DuckDB を用い、INSERT ... ON CONFLICT で冪等性を確保。
  - トランザクションを使ってバルク挿入の整合性を担保。

---

## ディレクトリ構成

（主要ファイルを抜粋した構成）

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
   │  ├─ schema.py
   │  ├─ calendar_management.py
   │  ├─ audit.py
   │  └─ quality.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

- data/ 以下がデータ取得・ETL・スキーマ・監査・品質チェックの主要実装です。
- config.py は環境設定の読み込みと Settings を提供します。
- strategy/ や execution/ は将来的な戦略・実行ロジックのための名前空間です（現状は空の __init__）。

---

## 開発・テストのヒント

- 自動 .env ロードを無効にしてテスト用の環境を用意したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  その後テスト用の環境変数を明示的にセットしてください。

- DuckDB をインメモリでテストするとき:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```

- jquants_client のネットワーク依存部分（_urlopen 相当）はモックしやすい設計になっています。news_collector の _urlopen などはテストで差し替え可能です。

---

## 参考・補足

- このリポジトリはライブラリ的な構成で、CLI やサービス起動スクリプトは含まれていません。必要に応じて小さなランナー（スケジューラから呼ぶバッチスクリプトや Airflow / Prefect のタスク）を作って利用してください。
- DuckDB のスキーマ定義や SQL は DataPlatform.md 等の設計ドキュメントに基づいています。スキーマ変更時は互換性に注意してください。
- 監査ログは削除を想定していません。監査テーブルを操作する際は慎重に行ってください。

---

必要であれば README に追記する内容（例: CI/CD 手順、詳細な .env.example、サンプル SQL クエリ、運用フロー図など）も作成します。どの情報を追加しますか？