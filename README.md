# KabuSys

日本株向け自動売買システムのコアライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、DuckDB ベースのスキーマ、ETL パイプライン、ファクター計算（リサーチ用）、ニュース収集、監査ログ用スキーマなどを提供します。

---

## 概要

KabuSys は次の機能を中心に設計されたライブラリ群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動更新対応）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・トラッキング除去・冪等保存）
- DuckDB を使った 3 層（Raw / Processed / Feature）スキーマ定義と初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ（Zスコア正規化・IC等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）のスキーマと初期化
- 環境設定管理（.env 自動読み込み、必須環境変数のラッパ）

設計方針として、本ライブラリは本番発注 API への直接アクセスを行わないモジュール（Data / Research 層）と、
発注・監視等を扱うレイヤーを分離しており、冪等性・トレーサビリティ・RateLimit・セキュリティ対策を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・トークン管理）
  - news_collector: RSS 取得・前処理・DuckDB への冪等保存・銘柄抽出
  - schema: DuckDB スキーマ定義（Raw / Processed / Feature / Execution 等）と初期化
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー管理・営業日の判定ユーティリティ
  - audit: 監査ログ向けスキーマ（signal / order_request / executions 等）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、ファクターサマリ
- config: 環境変数読み込み・設定ラッパ（自動 .env ロード, 必須チェック）
- execution / strategy / monitoring: （パッケージ構成あり、実装を拡張する想定）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに PEP 604 の union 型（A | B）を使用）
- DuckDB と defusedxml を使用

例: 仮想環境作成と最低限の依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
```

（プロジェクト配布物に requirements.txt があればそれを使用してください。）

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注系コンポーネント用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意 / デフォルト
- KABUSYS_ENV           : development | paper_trading | live（デフォルト development）
- LOG_LEVEL             : DEBUG|INFO|...（デフォルト INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視データ等（デフォルト data/monitoring.db）

.env 自動ロード
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。
- 読み込み順: OS 環境 > .env.local > .env
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（代表例）

以下はライブラリの代表的な使用例です。実運用ではエラーハンドリングやログ設定、スケジューリングを適切に行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリは自動作成されます）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 市場カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn, lookahead_days=90)
print("saved calendar rows:", saved)
```

4) ニュース収集ジョブ（既知の銘柄コードセットを渡すと記事→銘柄紐付けを行います）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

5) ファクター計算（リサーチ）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date

d = date(2024, 1, 4)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
```

6) 設定値参照
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
```

7) 監査ログスキーマの初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## よくある操作・補足

- J-Quants API のレート制限: 120 req/min を厳守する実装（内部で固定間隔スロットリングを行います）。大量取得時は適切に遅延を設けてください。
- トークン更新: get_id_token は refresh token を使い id token を取得し、401 を受けた場合は自動で1回リフレッシュして再試行します。
- ETL の差分ロジック: raw_prices / raw_financials の最終取得日を参照して差分取得・バックフィル（デフォルト3日）します。
- NewsCollector は SSRF 対策（リダイレクト先の検査）、Content-Length/受信サイズ制限、XML パースの安全ライブラリ（defusedxml）を使用しています。
- データ品質チェック: pipeline.run_daily_etl のオプションで品質チェックを実行できます（欠損・スパイク・重複・日付不整合）。
- 型要件: ライブラリ内部で Path | None 等の Python 3.10+ 構文を使用しているため Python 3.10 以上を推奨します。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要なモジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - etl.py
    - quality.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - (戦略実装を置く)
  - execution/
    - __init__.py
    - (発注・約定管理を置く)
  - monitoring/
    - __init__.py
    - (監視・アラート系を置く)

（上記は現状の実装ファイル一覧に基づく。strategy/execution/monitoring は拡張箇所です。）

---

## 環境変数のサンプル (.env.example)

例として .env に置くべき主要キー:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```
注意: 実運用では秘密情報を Git などにコミットしないでください。`.env.local` は開発環境固有の上書き用に利用できます。

---

## 開発・貢献

- 新しい ETL ジョブ、品質チェック、ファクターや戦略を追加する場合は、既存の設計方針（冪等性、トレーサビリティ、外部API呼び出しの安全性）に従ってください。
- DuckDB のスキーマを変更する場合は schema.py の DDL と init ロジックを更新し、マイグレーション方針を明示してください。

---

以上がプロジェクトの概要、セットアップ、主要な使い方、ディレクトリ構成の説明です。  
特定の機能について詳細な使い方（例: ETL のパラメータやファクター出力のフォーマット）を知りたい場合は教えてください。追加の使用例やサンプルスクリプトを作成します。