# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に採用し、J-Quants API からのデータ取得、ETL・品質チェック、特徴量計算、ニュース収集、監査ログなどの共通ユーティリティを提供します。  
このリポジトリは研究（Research）、データ（Data）、戦略（Strategy）、実行（Execution）、監視（Monitoring）を分離して実装する設計思想に基づいています。

バージョン: 0.1.0

---

## 主な機能

- 環境変数 / 設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動ロード（無効化可能）
  - 必須環境変数取得時のチェック

- データ取得 / 保存（J-Quants）
  - 株価日足（OHLCV）、財務データ（四半期）、JPX カレンダーの取得（ページネーション対応）
  - 取得データを DuckDB テーブルに冪等（ON CONFLICT）で保存
  - レート制限・リトライ・トークン自動リフレッシュ対応

- ETL パイプライン
  - 差分取得（最終取得日を参照して未取得分のみ取得）
  - バックフィル（API 後出し修正吸収）
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- スキーマ管理
  - Raw / Processed / Feature / Execution 層の DuckDB DDL を定義
  - スキーマ初期化ユーティリティ

- データ品質チェック
  - 欠損データ、スパイク、重複、未来日付 / 非営業日データの検出
  - QualityIssue を返却し呼び出し側で対応可能

- ニュース収集
  - RSS フィード収集（SSRF 対策、gzip 制限、XML セキュリティ）
  - URL 正規化・トラッキング除去、記事ID は SHA-256 ハッシュで冪等
  - 記事と銘柄コードの紐付け補助

- 研究用ユーティリティ
  - ファクター（Momentum / Volatility / Value）計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - シグナル→発注→約定までのトレーサビリティ用テーブル群と初期化ユーティリティ

---

## 必要な依存パッケージ（例）

KabuSys のコードベースで直接参照されているライブラリ（最低限）:

- Python 3.9+
- duckdb
- defusedxml

開発 / 実行環境に応じて追加パッケージ（例: slack SDK, requests 等）を導入してください。requirements.txt がない場合は手動でインストールします:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数 / .env

KabuSys は環境変数または `.env` / `.env.local` から設定を読み込みます。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化できます。

主な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API 用パスワード（発注関連）
  - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID      : Slack チャンネル ID

- 任意（デフォルトあり）
  - KABUSYS_ENV : `development` / `paper_trading` / `live`（デフォルト: development）
  - LOG_LEVEL   : `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込み無効化（値があれば無効）

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=changeme
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

注意: `.env.local` は `.env` の上書きとして優先読み込みされます（OS 環境変数はさらに優先）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし仮想環境を作成

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

2. 必要な環境変数を設定（または `.env` を作成）

3. DuckDB スキーマを初期化

例: Python REPL またはスクリプトから

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 必要に応じて監査ログ用スキーマを追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

または監査ログ専用 DB を作る:

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要ユースケースと例）

以下は主要なユーティリティの呼び出し例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- 日次 ETL（価格・財務・カレンダー取得 + 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別 ETL ジョブの実行（価格のみ）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- ニュース収集ジョブ

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 事前に用意した銘柄コードセット（例: 全上場銘柄）
known_codes = {"7203", "6758", "9432", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- 研究用: ファクター計算・IC 計算

```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = init_schema("data/kabusys.duckdb")
d = date(2024, 1, 31)
momentum = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
value = calc_value(conn, d)
forward = calc_forward_returns(conn, d, horizons=[1,5,21])
# 例: mom_1m と fwd_1d の IC
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- J-Quants から直接データ取得（クライアント使用例）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

- データ品質チェックの実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 便利な設定・注意点

- 自動 .env 読み込みは config モジュール内で行われます。テスト時などで無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）を尊重する設計になっています。fetch 関数は内部でスロットリング・リトライを行います。
- DuckDB の初期化は冪等（CREATE TABLE IF NOT EXISTS）になっています。`init_schema()` を複数回呼んでも問題ありません。
- ニュース収集は RSS の多様な形式を扱うため堅牢化（XML 安全、SSRF 対策、gzip サイズ制限）を行っています。
- 本システムは本番口座への発注機能を含むため、`KABUSYS_ENV` を `live` に設定する際は十分な注意と本番用の安全策を実装してください。

---

## ディレクトリ構成

プロジェクトの主要ファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 & 保存）
    - news_collector.py            — RSS ニュース収集・前処理・DB保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 統計ユーティリティ（zscore 等）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       — マーケットカレンダー管理
    - etl.py                       — ETL 結果型の再エクスポート
    - audit.py                     — 監査ログスキーマ & 初期化
    - quality.py                   — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py       — 将来リターン計算・IC・サマリー
    - factor_research.py           — ロジック層のファクター計算（momentum/value/vol）
  - strategy/                       — 戦略層（未実装の空パッケージ）
  - execution/                      — 発注 / 実行層（未実装の空パッケージ）
  - monitoring/                     — 監視関連（未実装の空パッケージ）

（README に掲載したコード抜粋は主要モジュールを示しています）

---

## 今後の拡張案 / 注意

- Strategy / Execution / Monitoring パッケージは空の初期化モジュールのみで、各種アルゴリズムやブローカ接続はプロジェクト固有に実装する想定です。
- Slack 連携、実口座での発注フロー、リスク管理ミドルウェア等は別途実装・検証が必要です。
- 大量データ運用では DuckDB のファイル配置、バックアップ、VACUUM（該当機能）等の運用設計が重要です。

---

この README はコードベース（src/kabusys）を元に作成しました。詳細は各モジュールの docstring / 関数ドキュメントを参照してください。必要であれば、導入ガイド（より詳しい手順）、API リファレンス、ユニットテスト例の追加も作成できます。