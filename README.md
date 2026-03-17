# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
J-Quants API や RSS ニュースを収集して DuckDB に保存し、ETL／品質チェック／マーケットカレンダー管理・監査ログなどの基盤機能を提供します。

現在のバージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数（.env）一覧
- 使い方（簡単なコード例）
- ディレクトリ構成
- 注意事項

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集して前処理・銘柄紐付けして保存
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日/半日/SQ判定、前後営業日取得）
- 監査ログ（シグナル → 発注 → 約定のトレース用スキーマ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント：
- API レート制御、リトライ、トークン自動リフレッシュを実装
- DuckDB へは冪等（ON CONFLICT）で保存
- RSS 収集では SSRF や圧縮爆弾対策、XML の安全なパーシングを実施

---

## 主な機能一覧

- data.jquants_client
  - J-Quants から日足、財務、マーケットカレンダーを取得／保存
  - レートリミッタ、リトライ、401 時のトークン自動更新
- data.news_collector
  - RSS 取得、URL 正規化、トラッキング除去、記事 ID 生成（SHA-256 ベース）
  - SSRF ブロック、受信サイズ制限、DuckDB への冪等保存
  - 銘柄コード抽出（4 桁数字）と news_symbols への紐付け
- data.schema / audit
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - 監査ログ（signal_events / order_requests / executions）
- data.pipeline
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分取得・バックフィル・品質チェックの統合
- data.calendar_management
  - 営業日判定、next/prev 営業日、期間内の営業日リスト
- data.quality
  - 欠損、スパイク、重複、日付不整合のチェック関数群
- config
  - .env / 環境変数の自動ロード（.env, .env.local、OS 環境優先）
  - アプリ設定 accessor（settings）

---

## 前提条件 / 依存関係

推奨 Python バージョン: 3.10+

主な Python パッケージ（最低限）:
- duckdb
- defusedxml

（プロジェクトで他に必要なパッケージがある場合は requirements.txt に記載してください）

---

## セットアップ手順

1. リポジトリをクローン、またはプロジェクトを取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   例（最低限）:
   ```
   pip install duckdb defusedxml
   ```
   実運用では追加パッケージ（Slack SDK など）が必要な場合があります。

4. 環境変数 (.env) を用意
   プロジェクトルートに `.env`（開発環境用）や `.env.local`（ローカル上書き）を配置します。自動ロード機能はデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

5. DuckDB スキーマ初期化（例）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   これで必要なテーブルとインデックスが作成されます。

---

## 環境変数（.env）一覧

以下はコードから読み取れる主な環境変数です。必須（必ず設定する必要がある）なものとデフォルト値があるものを区別しています。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env をロードする仕組みを無効化します（テスト等で便利です）。

注意: .env ファイルに機密情報（トークン等）を保存する場合は適切に管理し、ソース管理下に置かないでください（.gitignore に追加）。

---

## 使い方（簡単なコード例）

以下は主要な操作の一例です。実際にはログ設定や例外処理、認証情報の管理を適切に行ってください。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

- J-Quants から日足を直接取得して保存する
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- RSS を収集して保存し、銘柄紐付けを行う
```python
from kabusys.data import news_collector as nc
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# 既知の銘柄コードセット（実運用では銘柄マスタなどから取得）
known_codes = {"7203", "6758", "9984"}
results = nc.run_news_collection(conn, known_codes=known_codes)
print(results)
```

- マーケットカレンダーの判定例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- 品質チェックを実行する
```python
from kabusys.data import quality
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn)
for i in issues:
    print(i)
```

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得／保存）
    - news_collector.py      — RSS 収集・前処理・保存
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理ユーティリティ
    - audit.py               — 監査ログ（signal / order / execution）
    - quality.py             — データ品質チェック
  - strategy/                 — 戦略関連（雛形）
  - execution/                — 発注／約定関連（雛形）
  - monitoring/               — 監視用モジュール（雛形）

プロジェクトルート:
- pyproject.toml など（存在すればプロジェクトルート検出に利用）

---

## 注意事項 / 運用上のポイント

- 環境変数：機密トークンは必ず安全に管理してください。`.env` を含むファイルをバージョン管理に含めないでください。
- API レート：J-Quants へのリクエストはモジュール内部でレート制御を行いますが、利用状況に応じた追加の調整が必要な場合があります。
- DuckDB のファイルパスは settings.duckdb_path で設定可能。運用時はバックアップ・ローテーションを検討してください。
- RSS 取得では外部 URL を扱うため、SSRF・XML インジェクション・圧縮爆弾対策を実装済みですが、追加のセキュリティポリシーの適用を推奨します。
- KABUSYS_ENV により動作モード（development/paper_trading/live）を切り替えられます。ライブ運用時はより厳格なログ・監視・確認を行ってください。

---

ご不明点や README の追加項目（例：CI / デプロイ手順、詳細な API 使用例、テストの実行方法）をご希望であれば教えてください。README を拡張して追記します。