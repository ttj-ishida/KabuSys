# KabuSys

日本株向けの自動売買基盤ライブラリ。主にデータ収集（J-Quants / RSS）、ETL、データ品質チェック、DuckDB ベースのスキーマおよび監査ログ管理を提供します。戦略・発注（strategy / execution）用のモジュールスケルトンも含まれており、個別戦略やブローカー連携を組み込んで運用できます。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）と固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを抑止
  - DuckDB へ冪等保存（ON CONFLICT / DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードから記事を収集し DuckDB に保存（raw_news）
  - URL 正規化 → SHA-256（先頭32文字）で記事 ID 生成して冪等性確保
  - defusedxml による XML パース（XML Bomb 防止）
  - SSRF 対策（スキーム検証、リダイレクト先のプライベートアドレス検査）
  - レスポンスサイズ上限・gzip 解凍後サイズ検査（メモリ DoS 対策）
  - 銘柄コード抽出（4 桁）と news_symbols への紐付け

- ETL パイプライン
  - 差分更新（DB の最終取得日から必要分のみ取得）
  - バックフィル機能で API の後出し修正を取り込み
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- DuckDB スキーマ（Data 層 / Feature 層 / Execution 層）
  - raw_ / processed / feature / execution 層のテーブル定義
  - 監査用スキーマ（signal_events / order_requests / executions）
  - インデックス定義・初期化ユーティリティ

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）、重複検出、日付整合性検査
  - 問題は QualityIssue オブジェクトで返却（severity 別に処理可能）

- カレンダー管理ユーティリティ
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - JPX カレンダーの夜間更新ジョブ

---

## 必要条件

- Python 3.10 以上（typing の | 演算子を使用）
- パッケージ例（最小）:
  - duckdb
  - defusedxml

任意で（運用環境に応じて）：
- J-Quants のリフレッシュトークン
- kabuステーション API パスワード
- Slack Bot トークン / チャンネル

---

## インストール（開発用）

リポジトリルートで:

```bash
# 任意の仮想環境を作成して有効化した後
pip install -e .
# または最低限の依存を手動インストール
pip install duckdb defusedxml
```

（プロジェクトに requirements ファイルがあればそれを利用してください。）

---

## 環境変数・設定

KabuSys は .env/.env.local または OS 環境変数から設定を読み込みます。
プロジェクトルート判定は .git または pyproject.toml を基準とします。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)（default: development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

例 .env（テンプレート）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `from kabusys.config import settings` 経由で参照できます（プロパティとしてアクセス）。

---

## セットアップ手順（最小例）

1. Python 環境の準備 / 依存インストール
2. .env を作成して必要な環境変数を設定
3. DuckDB スキーマ初期化

例（Python スクリプト / REPL）:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# DUCKDB_PATH のデフォルトが使われる場合
conn = init_schema(settings.duckdb_path)
```

監査ログ専用 DB を別個に初期化する場合:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要な API 例）

- J-Quants の ID トークンを明示的に取得する:

```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使って POST 取得
```

- 日次 ETL を実行する（株価 / 財務 / カレンダー取得 + 品質チェック）:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブを実行する（RSS → raw_news 保存、銘柄紐付け）:

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes

conn = init_schema("data/kabusys.duckdb")

# known_codes は銘柄コードのセット（例: 上場銘柄一覧）
known_codes = {"7203", "6758", "9432", "8306"}  # 実運用では全コードセットを用意

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- 市場カレンダーの夜間更新ジョブ（差分取得）:

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved={saved}")
```

- データ品質チェック単体実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## ディレクトリ構成

リポジトリ（src 配下）のおもなファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py          — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py — RSS ニュース収集・保存・銘柄抽出
    - schema.py         — DuckDB スキーマ定義・初期化
    - pipeline.py       — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py — カレンダー管理・営業日ユーティリティ
    - audit.py          — 監査ログスキーマ（signal/order/execution）
    - quality.py        — データ品質チェック
  - strategy/
    - __init__.py       — 戦略モジュール用プレースホルダ
  - execution/
    - __init__.py       — 発注 / ブローカー連携用プレースホルダ
  - monitoring/
    - __init__.py       — 監視関連プレースホルダ

この README は上記モジュール群の使い方と初期セットアップを案内するためのドキュメントです。

---

## 運用上の注意・設計メモ

- J-Quants API はレート制限（120 req/min）があります。jquants_client は固定間隔スロットリングとリトライロジックを備えていますが、運用側でも呼び出し頻度に注意してください。
- ニュース収集では RSS の内容が大きく異なり得るため、受信サイズ制限（10 MB）・gzip 解凍後サイズチェックを行っています。必要に応じて MAX_RESPONSE_BYTES を調整してください。
- DuckDB のスキーマは冪等に作成できるようになっています（CREATE TABLE IF NOT EXISTS）。既存のデータを上書きしないため、スキーマ変更時は注意が必要です。
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI / テストで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- すべてのタイムスタンプは UTC を推奨（監査用 init_audit_schema は接続で TimeZone を UTC に固定します）。

---

## 開発・貢献

バグ報告や機能追加はプルリクエストで歓迎します。コードスタイル、テスト、CI の追加は将来的な改善ポイントです。

---

質問や README の拡張（利用例の追加、SQL スキーマ図、運用手順書など）が必要であれば教えてください。必要に応じて具体的なスクリプト例や運用 runbook を追記します。