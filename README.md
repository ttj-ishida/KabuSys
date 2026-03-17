# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。J‑Quants API や RSS フィードから市場データ・ニュースを取得し、DuckDB に蓄積、品質チェック、カレンダー管理、監査ログ（発注〜約定のトレーサビリティ）などの基盤機能を提供します。

この README はプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

主な目的は次のとおりです。

- J‑Quants API から株価（日足）・財務データ・JPX（マーケットカレンダー）を取得して DuckDB に保存する。
- RSS（ニュース）を収集して前処理・重複排除の上で保存し、銘柄コードとの紐付けを行う。
- データ品質チェック（欠損、スパイク、重複、日付不整合）を提供する。
- マーケットカレンダーを管理し、営業日の判定や前後営業日の探索を行う。
- 監査ログ（signal → order_request → execution のトレース）用テーブルを提供する。
- ETL パイプライン（差分更新、バックフィル、品質チェック）を一括で実行できる。

設計時の主な配慮点：

- API レート制限遵守（J‑Quants: 120 req/min 固定間隔スロットリング）
- リトライ（指数バックオフ、最大3回）、401 時のトークン自動リフレッシュ
- Look‑ahead bias 対策のため fetched_at / 取得時刻を記録
- DuckDB への保存は冪等（ON CONFLICT）で実装
- RSS 取得における SSRF / XML bomb 対策（スキームチェック、プライベートアドレス判定、defusedxml、最大受信サイズ）

---

## 機能一覧

- data/
  - jquants_client: J‑Quants API クライアント（取得・保存関数、トークン管理、レート制御、リトライ）
  - news_collector: RSS 収集・前処理・記事ID生成・DuckDB 保存・銘柄紐付け
  - schema: DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution）
  - pipeline: 日次 ETL（差分取得、バックフィル、品質チェック）と個別 ETL ジョブ
  - calendar_management: マーケットカレンダーの管理・営業日判定・ナイトバッチジョブ
  - audit: 監査ログ（signal / order_request / execution）用スキーマと初期化
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
- config: 環境変数読み込み・設定ラッパー（.env 自動ロード機能、必須チェック）
- strategy / execution / monitoring: プレースホルダ（戦略・発注・監視ロジックを配置する想定）

---

## 必要条件・依存

- Python 3.10 以上（型注釈で PEP 604 の `|` を使用しているため）
- 必須パッケージ（例）:
  - duckdb
  - defusedxml

インストール例（仮の環境）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発中はパッケージを編集可能インストール:
# pip install -e .
```

（実プロジェクトでは requirements.txt や pyproject.toml に依存を明記してください）

---

## 環境変数

`kabusys.config.Settings` が環境変数から設定を取得します。プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます（テスト時など自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（将来的な通知に使用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env の例:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: .env.local は .env の上書き（優先）として読み込まれます。OS 環境変数は保護されます。

---

## セットアップ手順

1. リポジトリをクローンしワーク環境を作成

```bash
git clone <repo-url>
cd <repo-dir>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 任意でパッケージを開発インストール
# pip install -e .
```

2. 環境変数を用意

プロジェクトルートに `.env` を作成して必要なキーを設定します（上の例参照）。

3. DuckDB スキーマ初期化

Python REPL かスクリプトで schema を初期化します。例:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを自動作成
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

4. 監査ログ専用 DB 初期化（任意）

```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（基本例）

以下は主要なユースケースの簡単な例です。

1) 日次 ETL を実行する（株価 / 財務 / カレンダー取得 + 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

# DB を初期化して接続を取得（初回）
conn = schema.init_schema("data/kabusys.duckdb")

# ETL 実行（target_date 省略で今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

run_daily_etl は内部で:
- カレンダーETL（先読み）
- 株価差分取得（バックフィル）
- 財務差分取得（バックフィル）
- 品質チェック（quality.run_all_checks）

を順に実行し、ETLResult を返します。

2) 単体で株価差分 ETL を実行する

```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.init_schema("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

3) RSS（ニュース）収集ジョブを実行する

```python
from kabusys.data import news_collector, schema
from kabusys.data.news_collector import DEFAULT_RSS_SOURCES

conn = schema.init_schema("data/kabusys.duckdb")

# known_codes に抽出対象の銘柄コードセットを渡すと、記事と銘柄の紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 例
results = news_collector.run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数, ...}
```

4) カレンダー夜間更新ジョブ

```python
from kabusys.data import calendar_management, schema

conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

5) J‑Quants の ID トークンを直接取得（テスト等）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

---

## API の振る舞い（重要ポイント）

- jquants_client:
  - レート制御: 120 req/min（固定間隔スロットリング）
  - リトライ: 最大 3 回（指数バックオフ）。408/429/5xx を対象
  - 401 受信時: 自動でリフレッシュトークンを使って id_token を再取得し、1 回だけリトライ
  - ページネーション対応（pagination_key）
  - DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING で冪等性を確保

- news_collector:
  - 記事 ID は正規化 URL の SHA‑256（先頭32文字）で一意化
  - defusedxml で XML パース（XML Bomb 対策）
  - URL スキーム検証（http/https のみ）・プライベートアドレス判定（SSRF 対策）
  - 最大受信バイト数制限（デフォルト 10MB）＋ gzip 解凍後のサイズ確認
  - DB 保存はチャンク分割してトランザクションで処理し、挿入済みのみを返す（INSERT ... RETURNING）

- quality:
  - 欠損（OHLC）→ error
  - 主キー重複 → error
  - スパイク（前日比閾値）→ warning（デフォルト 50%）
  - 将来日付 / 非営業日データ → error/warning

- calendar_management:
  - market_calendar が存在しない場合は曜日ベースのフォールバック（土日は非営業日）
  - next_trading_day / prev_trading_day / get_trading_days 等を提供
  - calendar_update_job はバックフィル（最近数日分）を常にリフェッチして API の修正を取り込む

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py  -- J‑Quants API クライアント（取得・保存）
    - news_collector.py  -- RSS 収集・前処理・保存・銘柄抽出
    - schema.py          -- DuckDB スキーマ定義と初期化
    - pipeline.py        -- ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py -- マーケットカレンダー管理
    - audit.py           -- 監査ログスキーマ（signal/order_request/execution）
    - quality.py         -- データ品質チェック
  - strategy/
    - __init__.py  -- 戦略層用プレースホルダ
  - execution/
    - __init__.py  -- 発注/ブローカー連携プレースホルダ
  - monitoring/
    - __init__.py  -- 監視機能プレースホルダ

その他:
- pyproject.toml（存在する場合はプロジェクトルート判定に使用）
- .git（存在する場合はプロジェクトルート判定に使用）
- .env / .env.local（環境変数定義）

---

## 開発上の注意点

- Python 3.10 以上での実行を想定しています。型ヒントに PEP 604（|）が使われています。
- DuckDB は組み込みデータベースで高速ですが、複数プロセス／多重接続時の挙動には注意してください。
- J‑Quants API のレート制限や利用規約は常に遵守してください。実際に運用する際は API キーの管理と権限に注意すること。
- news_collector は外部 URL を取得します。社内ネットワーク環境やプロキシ、ファイアウォール設定との整合性に注意してください。
- ETL 実行は失敗を柔軟に扱い、各ステップは独立してエラーハンドリングされます（ログで原因を把握して運用判断を行ってください）。

---

## 参考 / 次のステップ

- 戦略層 (strategy) / 発注層 (execution) の実装を追加して、signals → order queue → ブローカー送信 → 約定取得の一連フローを統合してください。
- Slack 通知や監視ダッシュボードを構築して運用アラートを受け取れるようにしてください。
- CI（単体テスト・品質チェック）や周回実行（cron / Airflow / Prefect など）で ETL を自動化してください。

---

この README はコードベース内の実装（src/kabusys 配下）を元に作成しています。追加で README に記載したい運用手順やサンプルスクリプトがあれば教えてください。必要に応じて README を拡張します。