# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム向けライブラリです。  
J-Quants API からのデータ取得、DuckDB によるデータ保管・スキーマ管理、ETL パイプライン、ニュース収集、ファクター計算（研究用）などを提供します。

主な設計方針:
- DuckDB を中心としたローカル DB による冪等的なデータ保存
- API 呼び出しはレートリミット・リトライ・トークン自動更新に対応
- Research / Strategy 層は本番発注に影響を与えない（DB と標本データのみ参照）
- セキュリティ考慮（RSS の SSRF 防止、defusedxml 等）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー
- データ取得（kabusys.data.jquants_client）
  - 株価日足、財務データ、JPX カレンダー取得（ページネーション対応）
  - レートリミット制御、リトライ、401 時のトークン自動更新
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT）
- DB スキーマ管理（kabusys.data.schema / audit）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - init_schema / init_audit_db による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（backfill 対応）、calendar/prices/financials の ETL
  - 品質チェックの統合実行（kabusys.data.quality）
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、ID 生成、DuckDB への冪等保存、銘柄抽出
  - SSRF 対策、gzip サイズ上限、XML 安全パーサを採用
- 研究用ファクター計算（kabusys.research）
  - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - zscore 正規化ユーティリティの再エクスポート
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などトレーサビリティ用テーブル

---

## 要件

- Python 3.10+
- 主要依存（プロジェクトに requirements ファイルがある場合はそちらを使用）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクトルートで
# python -m pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／配置する

2. Python と依存パッケージをインストール
   - Python 3.10 以上推奨
   - duckdb, defusedxml をインストール

3. 環境変数を用意する
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（コード中で _require() を使っているもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード
- SLACK_BOT_TOKEN       : Slack Bot トークン（監視通知などに利用）
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）

サンプル .env（例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な操作例）

以下は Python REPL やスクリプトから利用する例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルベース DB を作成してスキーマを初期化
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = init_schema(":memory:")
```

2) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes: 抽出対象の有効銘柄コードセット（例: {'7203', '6758', ...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
print(res)
```

4) J-Quants から日足を直接取得（テストや部分取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使って取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

5) 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.research import calc_momentum, zscore_normalize

conn = get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024,1,31))
# Zスコア正規化（列名は返り値に合わせて指定）
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

6) IC（情報係数）計算例
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1])
factors = ...  # 例えば calc_momentum の戻り値
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print(ic)
```

7) 監査ログの初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 重要な注意点 / 動作方針

- research/strategy モジュールは prices_daily / raw_financials 等の DB テーブルのみを参照し、本番の発注 API にアクセスしない設計です（研究段階で誤発注を防止）。
- J-Quants API 呼び出しはレート制御とリトライ・トークンリフレッシュを行いますが、API キーやトークンの管理は慎重に行ってください。
- news_collector は外部 RSS を処理するため SSRF 対策、制限付きの受信サイズ、XML の安全パーサを導入しています。それでも RSS の内容に依存する処理は実用環境で監視してください。
- DuckDB のバージョンや SQL の差異によって一部の外部キーや制約の挙動が異なることがあります（README 中のコメントにあるように DuckDB の未サポート機能はアプリ側で制御する設計になっています）。

---

## ディレクトリ構成

以下はコードベースの主なファイル／ディレクトリ構成（src/kabusys 以下抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py              — RSS ニュース収集・保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - stats.py                       — 統計ユーティリティ（zscore 等）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - features.py                    — 特徴量ユーティリティ公開
    - calendar_management.py         — 市場カレンダー管理
    - audit.py                       — 監査ログテーブル初期化
    - etl.py                         — ETL 公開インターフェース
    - quality.py                     — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py         — 将来リターン / IC / 統計サマリ
    - factor_research.py             — Momentum / Volatility / Value 計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールは README 中で説明した役割に従って機能が分離されています。

---

## 開発・テスト

- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから読み込みます。テスト時に自動ロードを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を用いた単体テストはインメモリ DB（":memory:"）で実行できます。
- ネットワーク依存のテスト（J-Quants / RSS）は外部 API に依存するため、モックや vcr 的な再生機構の利用が推奨されます。

---

この README はコードベースに含まれる実装に基づく要約です。具体的な関数の引数・戻り値や挙動は各モジュールの docstring を参照してください。質問や具体的な利用例があれば教えてください。