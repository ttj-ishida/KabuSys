# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB を内部データベースとして用い、J-Quants 等の外部データソースからデータを取得・整形し、特徴量計算やETL・監査ログ・ニュース収集などのユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API 等から株価・財務・カレンダー・ニュースを取得して DuckDB に保管（冪等保存）
- ETL パイプラインによる差分取得と品質チェック
- 研究（research）用途のファクター計算・特徴量探索ユーティリティ
- ニュース収集（RSS）と記事 → 銘柄紐付け
- 監査ログ（シグナル → 発注 → 約定）のスキーマ・初期化機能

設計方針としては「外部（ブローカー）への発注を行わない研究用／運用補助ライブラリ」となり、DuckDB のテーブル設計、ETL、品質チェック、ファクター計算などを含みます。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読込（プロジェクトルート検出）
  - 必須環境変数チェック（Settings）
- データ取得・保存（kabusys.data.jquants_client）
  - 日次株価（OHLCV）取得（ページネーション対応、レート制御、リトライ、トークン自動リフレッシュ）
  - 財務データ取得
  - JPX マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE 等）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からの差分 + backfill）
  - 市場カレンダー先読み
  - 品質チェック実行（欠損・スパイク・重複・日付不整合）
  - ETL 結果を ETLResult で返却
- スキーマ初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層を定義した DuckDB テーブルを作成
  - 便利な init_schema / init_audit_schema 等
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策、gzip 対応、レスポンスサイズ制限）
  - 記事正規化・ID 生成（URL 正規化 → SHA256）
  - raw_news へ冪等保存、news_symbols への銘柄紐付け
  - 銘柄抽出（4桁コード候補のフィルタリング）
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - z-score 正規化ユーティリティ再エクスポート
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（外部ライブラリに依存しない実装）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等、監査用テーブルと初期化ロジック

---

## 必要条件

- Python 3.10 以上（typing の `|` 記法を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb>=0.8" defusedxml
```
（実際の要件バージョンはプロジェクトの requirements を用意することを推奨します）

---

## 環境変数（.env）

自動でプロジェクトルート（.git または pyproject.toml）を探し、`.env` → `.env.local` の順に読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（Settings._require が要求するもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注関連を使う場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: 同上

その他（任意・デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite path（監視用DB等、デフォルト: data/monitoring.db）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python の準備（3.10+ を推奨）
2. 依存ライブラリのインストール
   ```bash
   python -m pip install duckdb defusedxml
   ```
3. プロジェクトルートに .env を作成（.env.example を参考に）
4. DuckDB スキーマの初期化（例: Python REPL / スクリプト）
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   - :memory: を指定するとインメモリ DB を作成できます
5. （任意）監査ログ用スキーマの初期化
   ```python
   from kabusys.data.audit import init_audit_db
   init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

### DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

### 日次 ETL の実行
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

# 初回は init_schema を実行してテーブルを作成
conn = init_schema("data/kabusys.duckdb")

# 日次ETLを実行（target_date を省略すると今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

run_daily_etl は市場カレンダー、株価、財務データの差分取得と品質チェックを行い、ETLResult を返します。

### ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は既知の有効な銘柄コード集合（例: データベースから抽出）
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

### 研究用ファクター計算（例）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
# 必要に応じて zscore_normalize を適用
from kabusys.data.stats import zscore_normalize
mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

### J-Quants からのデータ取得（低レベル）
kabusys.data.jquants_client にはデータ取得と保存のユーティリティがあります。テストやユーティリティ用途で id_token を注入可能です。
例:
```python
from kabusys.data import jquants_client as jq
from datetime import date

rows = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
```

---

## 開発向けメモ

- .env の自動読込はプロジェクトルート（.git/pyproject.toml）を基準に行われます。テスト環境で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB への挿入は冪等性を考慮（ON CONFLICT / DO UPDATE / DO NOTHING）しています。
- RSS 収集時は SSRF 対策や gzip 展開・最大サイズ制限等の保護が組み込まれています。
- J-Quants API 呼び出しには内部的にレート制御とリトライ（指数バックオフ）があります。401 は自動トークンリフレッシュで1回リトライします。

---

## ディレクトリ構成

プロジェクトの主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - etl.py
    - quality.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要なモジュールの役割:
- config.py: 環境変数・設定管理
- data/schema.py: DuckDB スキーマ定義・初期化
- data/jquants_client.py: J-Quants API クライアント + 保存ユーティリティ
- data/pipeline.py: ETL パイプライン
- data/news_collector.py: RSS ニュース収集と DB 保存
- data/quality.py: データ品質チェック
- research/*: ファクター計算・特徴量探索
- data/audit.py: 監査ログ用スキーマと初期化

---

## よくある質問 / 注意点

- Python バージョンは 3.10 以上を推奨（typing の `|` を使用）。
- 外部 API キー（J-Quants のリフレッシュトークン等）は機密情報なので .env を .gitignore に追加してください。
- 実際に発注・決済を行うモジュール（kabu API 連携など）を運用する場合は、paper_trading/live の env 設定と十分なテストを行ってください。
- DuckDB のバージョンによっては一部の DDL・インデックス挙動が異なる可能性があります。テスト環境で確認のうえ運用してください。

---

この README はコードベースの現行実装（0.1.0）に基づいて作成しています。機能追加・API 変更があった場合は随時更新してください。