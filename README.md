# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に永続化し、ニュース収集や品質チェック、監査ログ用スキーマなどを提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、四半期財務諸表、JPX マーケットカレンダーをページネーション対応で取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 発生時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を抑止

- データ保存（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のスキーマ定義と初期化
  - 冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）により重複を排除

- ETL パイプライン
  - 差分更新（最終取得日の差分のみ取得）/ バックフィル対応
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集
  - RSS フィードからニュースを取得し raw_news に保存
  - URL 正規化・トラッキングパラメータ除去・記事 ID の SHA-256 ハッシュ化（先頭32文字）
  - SSRF 対策、受信サイズ制限、XML 安全パーサ（defusedxml）

- マーケットカレンダー管理
  - 営業日判定、前後営業日・期間内営業日の取得、夜間バッチ更新ジョブ

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用スキーマ（UUID を用いた追跡）
  - タイムゾーンを UTC に固定

- データ品質チェック（quality）
  - 欠損検出、スパイク検出、重複検出、将来日付・非営業日の検出

---

## 必要な環境変数（主なもの）

以下は Settings クラスが参照する主要な環境変数です（.env に定義可能）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス、デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — SQLite（モニタリング用）パス、デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（ただし環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化）。

---

## セットアップ

前提: Python 3.9+（コードの型や記法から）と pip が利用可能であること。

1. リポジトリをクローン（またはソースを入手）

2. 仮想環境の作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

3. 依存パッケージのインストール（例）
```bash
pip install duckdb defusedxml
```
プロジェクトに packaging ファイルがあれば `pip install -e .` も可。

4. 環境変数を設定（例: `.env` をプロジェクトルートに作成）
```env
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主なユースケースとコード例）

以下は Python スクリプトや対話環境から直接呼び出す最小例です。

- スキーマの初期化（DuckDB の作成）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブを実行（RSS 取得→raw_news 保存→銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- マーケットカレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

- 監査ログ専用 DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- 設定（環境変数）を読む
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live
```

- 直接 J-Quants API からデータ取得（テストやカスタム用途）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# 省略時は settings.jquants_refresh_token 経由でトークンを取得
records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ロギング／エラーハンドリング

- モジュールは Python 標準の logging を使用します。起動スクリプトでロガー設定（ハンドラ・フォーマット・レベル）を行ってください。
- 設定は環境変数 `LOG_LEVEL` により制御されます（Settings.log_level）。
- ETL の各ステップは独立して例外処理され、1 ステップ失敗でも他のステップは継続する設計です。最終的な問題は ETLResult.errors や quality の戻り値で確認できます。

---

## セキュリティと堅牢性に関するポイント

- J-Quants クライアントはレート制限、再試行、401 の自動リフレッシュ等の対策を実装。
- NewsCollector は defusedxml を使用、レスポンスサイズ上限、gzip 解凍後の上限チェック、SSRF 対策（リダイレクト先とホストの private チェック）を備えています。
- DuckDB への保存は基本的に冪等（ON CONFLICT）で重複を回避します。

---

## ディレクトリ構成

リポジトリの主要なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定の管理（Settings）
  - data/
    - __init__.py
    - schema.py                    — DuckDB スキーマ定義・初期化
    - jquants_client.py            — J-Quants API クライアント（取得＋保存ユーティリティ）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py       — マーケットカレンダー管理・バッチ更新
    - audit.py                     — 監査ログスキーマ（signal/order/execution）
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py                  — （戦略関連：拡張ポイント）
  - execution/
    - __init__.py                  — （発注・約定・接続関連：拡張ポイント）
  - monitoring/
    - __init__.py                  — （監視／メトリクス：拡張ポイント）

各ファイルは docstring とコメントで設計方針や安全・堅牢性の考慮点を明記しています。

---

## 開発・テスト時の注意

- 自動で .env を読み込むため、テスト時に環境依存を切り離す場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を付与してください。
- DuckDB のパスにデフォルトは `data/kabusys.duckdb` が使われます。テストでは `":memory:"` を使ってインメモリ DB を利用できます。
- 外部 API を叩くテストは（取得レートや課金、環境依存のため）モックすることを推奨します。news_collector では `_urlopen` を差し替えやすいよう実装されています。

---

## ライセンス / 貢献

本 README はコードベースに基づくドキュメントです。実際のライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（無ければプロジェクト方針に従って追加してください）。

---

必要なら、典型的な運用スクリプト（systemd / cron 用の起動スクリプト例）、.env.example、より詳細な API 使用例や SQL のスキーマ説明（各テーブルの列説明）を追補できます。どの情報を優先して追加しますか？