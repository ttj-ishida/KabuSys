# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants や RSS 等から市場データを取得し、DuckDB に蓄積して ETL → 品質チェック → 戦略 / 実行ロジックへ渡すための基盤モジュール群を含みます。

主な設計方針：
- データの冪等性（ON CONFLICT / idempotent 保存）
- Look-ahead bias 回避（fetched_at 等で取得時刻を追跡）
- API レート制御・リトライ・トークン自動更新
- セキュリティ考慮（RSS の SSRF 対策、defusedxml など）
- DuckDB を中心とした軽量ローカルデータベース

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env/.env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数の取得とバリデーション
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークン更新
  - DuckDB への冪等保存関数（save_*）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集、前処理、記事ID生成（URL 正規化→SHA-256）
  - SSRF 対策、gzip サイズ制限、defusedxml による XML 安全処理
  - raw_news / news_symbols への保存（チャンク・トランザクション管理）
- スキーマ管理（kabusys.data.schema）
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(), get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（バックフィル対応）、保存、品質チェックの統合ジョブ（run_daily_etl）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
  - 品質チェック（kabusys.data.quality）との連携（欠損、重複、スパイク、日付整合性）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日取得・夜間更新ジョブ（calendar_update_job）
- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定まで追跡可能な監査用テーブル群、初期化ユーティリティ
- 監視 / 実行 / 戦略用の名前空間（kabusys.strategy, kabusys.execution, kabusys.monitoring）を用意

---

## セットアップ手順

前提
- Python 3.10 以上（typing の |（Union）構文を使用）
- ネットワークアクセス（J-Quants / RSS）

推奨パッケージ（例）
- duckdb
- defusedxml

pip でインストール例:
```
python -m pip install duckdb defusedxml
```

（プロジェクトに requirements.txt がある場合はそれを使用してください）

環境変数
- 以下の環境変数を設定してください（.env ファイルも利用可）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（fetch のため必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注等）
- SLACK_BOT_TOKEN — Slack 通知（必要な場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必要な場合）

オプション（デフォルトあり）:
- KABUSYS_ENV — application mode: development / paper_trading / live （デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると自動 .env ロードを無効化
- KABUSYS_API_BASE_URL — kabuAPI ベース URL（必要に応じて）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite 等のパス（デフォルト data/monitoring.db）

.env の自動ロードについて
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に自動で .env を読み込みます。
- 読み込み順序（優先度）: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要な例）

以下は Python スクリプト / REPL から利用する際の簡単な例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行する（市場データ・財務・カレンダーを取得し品質チェックを行う）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())  # ETLResult を辞書化して確認
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes に有効な銘柄コードセットを渡すと銘柄紐付けも行う
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)  # 各ソースごとの新規保存件数
```

4) マーケットカレンダーの夜間更新
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved_calendar_records={saved}")
```

5) 監査ログ用スキーマを初期化（専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

ログ出力や例外ハンドリングは各関数で適切に行われます。run_daily_etl は ETLResult を返し、品質チェック結果やエラー概要を確認できます。

---

## ディレクトリ構成

（リポジトリ内の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + 保存）
    - news_collector.py      — RSS ニュース収集と保存
    - pipeline.py            — ETL パイプライン（差分取得, run_daily_etl）
    - schema.py              — DuckDB スキーマ定義・初期化（init_schema）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py               — 監査ログテーブル初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略関連名前空間（拡張用）
  - execution/
    - __init__.py            — 発注／ブローカー連携の名前空間（拡張用）
  - monitoring/
    - __init__.py            — 監視／メトリクス用名前空間（拡張用）

---

## 実装上の注意 / 補足

- J-Quants API
  - レート制御 (120 req/min) を実装。短時間で大量リクエストをかけないでください。
  - リトライロジック（最大3回）、429 の場合は Retry-After ヘッダを優先。
  - 401 を受けた場合はリフレッシュトークンで id_token を再取得して 1 回リトライします。
  - fetch_* はページネーションに対応（pagination_key）。

- ニュース収集
  - URL 正規化により utm_* 等のトラッキングパラメータを除去して id を生成（冪等性）。
  - SSRF 対策（スキーム検証・プライベート IP のブロック・リダイレクト検査）。
  - レスポンスサイズは最大 10MB に制限（gzip 解凍後もチェック）。

- データ品質チェック
  - 欠損（OHLC）、重複、スパイク（前日比）、日付整合性（未来日・非営業日）を検出。
  - 問題は QualityIssue のリストとして返却。重大度に応じて呼び出し側で対応を決定してください。

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution 層を分離。
  - 多数のインデックスを作成して一般的なクエリを高速化。
  - init_schema(db_path) は親ディレクトリを自動作成します（":memory:" も利用可能）。

---

## ライセンス・貢献

- 本 README はコードベースからの説明に基づいて自動生成されています。実際の公開・利用はプロジェクトの LICENSE に従ってください。
- 拡張やバグ修正、テスト追加を歓迎します。CLI / サービス用エントリポイントやユニットテスト、CI の追加が次の改善候補です。

---

不明点や README に追記したい使用例（例: cron で run_daily_etl を定期実行する方法、Slack 通知の連携例など）があれば教えてください。サンプルスクリプトや systemd / cron 設定例も作成します。