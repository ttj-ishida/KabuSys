# KabuSys

日本株向け自動売買システムのライブラリ群（モジュール群のコア実装）。  
データ収集（J-Quants / RSS）、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な目的は「データ基盤（DuckDB）を中心に、戦略実行に必要なデータ取得・整形・監査を安全かつ冪等に行う」ことです。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを検出）
  - 必須設定の取得とバリデーション

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務諸表（四半期）、JPXマーケットカレンダーの取得
  - API レート制御（120 req/min）、自動トークンリフレッシュ、リトライ（指数バックオフ）
  - DuckDB へ冪等（ON CONFLICT）で保存するユーティリティ

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS から記事取得、前処理（URL除去・空白正規化）
  - URL 正規化と記事ID生成（SHA-256 ハッシュの先頭32文字）
  - SSRF / XML BOM 対策（スキーム検証、プライベートIP拒否、defusedxml、サイズ上限）
  - DuckDB へのバルク保存（INSERT ... RETURNING / トランザクション）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化ユーティリティ（init_schema / get_connection）
  - インデックス定義

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日から必要範囲のみ取得）
  - バックフィル（後出し修正吸収）とカレンダー先読み
  - 品質チェック（quality モジュール）との統合
  - 日次 ETL エントリ（run_daily_etl）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日取得、期間内営業日リスト取得
  - 夜間更新ジョブ（calendar_update_job）

- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue 型で詳細情報を返す

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査向けテーブル
  - 監査用スキーマ初期化（init_audit_schema / init_audit_db）
  - UTC タイムゾーン固定、冪等キー管理

---

## 必要要件（概略）

- Python 3.10+（型注釈に union | を利用）
- 依存ライブラリ（例）
  - duckdb
  - defusedxml
  - そのほか標準ライブラリのみで実装されている箇所が多いですが、実行環境に合わせて pyproject/requirements.txt を参照してください。

---

## 環境変数（必須／任意）

必須（アプリ起動前に設定してください）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャネル ID

任意（既定値あり）:
- KABUSYS_ENV — {development, paper_trading, live}（既定: development）
- LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（既定: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動読み込みを無効化
- KABUSYS のデータベースパス:
  - DUCKDB_PATH — 既定: data/kabusys.duckdb
  - SQLITE_PATH — 既定: data/monitoring.db
- KABU_API_BASE_URL — 既定: http://localhost:18080/kabusapi

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

パッケージ起動時はプロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env/.env.local を自動読み込みします。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを配置

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール（例）
   - pip install duckdb defusedxml
   - pip install -e .  # パッケージを開発編集モードでインストールする場合

4. 必須環境変数を .env に設定（上記参照）

5. DuckDB スキーマ初期化
   - Python REPL から:
     >>> from kabusys.data.schema import init_schema
     >>> init_schema("data/kabusys.duckdb")
   - またはスクリプト例:
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

6. 監査ログ専用 DB 初期化（任意）
   - >>> from kabusys.data.audit import init_audit_db
   - >>> init_audit_db("data/audit.duckdb")

---

## 使い方（主要なユースケース）

以下は簡単な使用例です。実行はプロジェクトルートから行ってください。

- DuckDB に接続して ETL を実行する（日次 ETL）
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

# 1回だけ: スキーマ初期化
conn = init_schema("data/kabusys.duckdb")  # 既に初期化済でも安全（冪等）
# あるいは既存 DB へ接続
# conn = get_connection("data/kabusys.duckdb")

# 日次 ETL 実行（target_date を省略すると今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

- 市場カレンダー夜間バッチ（単体実行）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効なコード集合（省略可能）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

- J-Quants から個別データを取得して保存（例: 日足）
```python
from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

- 監査スキーマ初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 開発・運用メモ

- レート制限とリトライ
  - J-Quants API は 120 req/min の制限を想定しており、クライアントは固定間隔スロットリングと指数バックオフを実装しています。
  - 401 が返った場合は自動的にリフレッシュトークンから id_token を更新して一度だけ再試行します。

- NewsCollector のセキュリティ
  - RSS フィード取得時にスキーム検証（http/https 限定）、プライベート IP / ループバックのアクセス拒否、最大受信サイズ制限（既定 10 MB）、defusedxml を利用した XML パース保護を行っています。

- ETL の差分更新
  - 株価・財務は DB に保存された最終日を基に差分取得し、デフォルトで backfill_days=3 を使って直近数日を再フェッチします（API の後出し修正吸収目的）。

- データ品質チェック
  - ETL 後に run_all_checks を呼び、欠損・重複・スパイク・日付不整合を検出できます。チェックは Fail-Fast ではなく問題を集めて返します。

- 自動 env 読み込み
  - プロジェクトルートから .env / .env.local を自動で読み込みます。テストで負荷や isolation が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集 / 保存
    - schema.py              — DuckDB スキーマ定義と初期化
    - pipeline.py            — ETL パイプライン（差分更新/日次ETL）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログ（発注/約定）スキーマ初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略用パッケージ（拡張ポイント）
  - execution/
    - __init__.py            — 発注実行用パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視・メトリクス用（拡張ポイント）

---

## 追加情報 / 注意点

- このリポジトリはライブラリ/内部フレームワークを提供する実装です。実際の自動売買稼働ではリスク管理、発注の安全性、証券会社 API の仕様遵守、法令遵守が必要です。
- 本リードミーはコードベースから抽出した仕様説明です。運用環境に適用する際は .env の機密情報管理やログ・監査ポリシーの整備を行ってください。

---

ご希望があれば、README にサンプル .env.example を追加したり、よく使う CLI スクリプト例（cron ジョブ / systemd タスク用）を追記します。どの利用フローに焦点を当てたいか教えてください。