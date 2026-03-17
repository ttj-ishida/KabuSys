# KabuSys

日本株向け自動売買基盤コンポーネント集 (KabuSys)

このリポジトリは、日本株自動売買プラットフォームのデータ収集・ETL・監査・品質チェック等の基盤モジュール群を提供します。J-Quants API や RSS フィードからのデータ取得、DuckDB を用いたスキーマ定義／永続化、日次 ETL パイプライン、ニュース収集、マーケットカレンダー管理、監査ログ用スキーマなどを含みます。

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 自動リフレッシュ
  - ページネーション対応、取得時刻（fetched_at）の記録

- ニュース収集
  - RSS から記事を取得して正規化・前処理し DuckDB に保存
  - URL 正規化（トラッキングパラメータ除去）、SSRF 対策、gzip / サイズ制限、XML の安全パース

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義を提供
  - 冪等なテーブル作成・インデックス作成、監査用スキーマの初期化

- ETL パイプライン
  - 差分取得（最終取得日からの差分 + バックフィル）、品質チェックの統合実行
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- マーケットカレンダー管理
  - JPX カレンダーの差分更新、営業日判定ユーティリティ（next/prev/get_trading_days 等）

- 監査ログ
  - シグナル → 発注 → 約定 のトレースを保証する監査テーブル群（UUID ベース）

---

## 要件

- Python 3.10+
  - （ソース内で | を用いた型注釈を使用しているため）
- 必要パッケージ例
  - duckdb
  - defusedxml

インストールは任意の Python 仮想環境で行ってください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージとして編集インストールする場合（pyproject / setup がある前提）
pip install -e .
```

※ pyproject.toml / setup.py がある場合は上記でパッケージインストールできます。無ければ `src` を PYTHONPATH に追加して利用してください。

---

## 環境設定

このプロジェクトは環境変数または .env ファイルから設定を読み込みます（自動ロードの実装は `kabusys.config` 内にあります）。

読み込み順（優先度）:
1. OS 環境変数
2. .env.local（存在すれば .env を上書き）
3. .env

自動読み込みを無効化する場合:
- 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

その他（任意）
- KABUSYS_ENV — 実行環境 (development|paper_trading|live)、デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）、デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視用途など）（デフォルト `data/monitoring.db`）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. Python 仮想環境を作る
2. 必要ライブラリをインストール（例: duckdb, defusedxml）
3. 環境変数を設定（または .env を作成）
4. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.data import schema

# ファイル DB を作成してスキーマを初期化
conn = schema.init_schema("data/kabusys.duckdb")

# 監査スキーマを追加する場合
from kabusys.data import audit
audit.init_audit_schema(conn)
```

※ `schema.init_schema` は親ディレクトリがなければ自動作成します。

---

## 使い方（主要な操作例）

- J-Quants トークン取得:
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を利用して idToken を取得
```

- 生データ取得（例: 日足取得）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- データ保存（DuckDB へ）:
```python
from kabusys.data import schema, jquants_client
conn = schema.get_connection("data/kabusys.duckdb")
# fetch した records を保存
saved = jquants_client.save_daily_quotes(conn, records)
```

- 日次 ETL 実行:
```python
from kabusys.data import schema, pipeline
conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)  # 今日を対象に ETL を実行
print(result.to_dict())
```

- ニュース収集ジョブ:
```python
from kabusys.data import schema, news_collector
conn = schema.get_connection("data/kabusys.duckdb")
# デフォルト RSS ソースから収集
results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # source_name: 新規保存数
```

- マーケットカレンダー夜間更新:
```python
from kabusys.data import schema, calendar_management
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved={saved}")
```

- 品質チェック（個別／一括）:
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 主要モジュール概要

- kabusys.config
  - 環境変数管理、自動 .env ロード、settings オブジェクト（プロパティで設定値を取得）

- kabusys.data.jquants_client
  - J-Quants API リクエスト、get_id_token、fetch_*/save_* 関数（daily_quotes, financials, market_calendar）

- kabusys.data.news_collector
  - RSS 取得、テキスト前処理、記事ID生成、raw_news への保存、銘柄抽出と news_symbols 保存、SSRF 対策

- kabusys.data.schema
  - DuckDB のスキーマ定義・初期化（raw/processed/feature/execution 層）

- kabusys.data.pipeline
  - ETL の差分取得ロジック、日次 ETL エントリポイント（run_daily_etl）

- kabusys.data.calendar_management
  - カレンダー更新ジョブ、営業日判定ユーティリティ（is_trading_day, next_trading_day 等）

- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）用スキーマ初期化

- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合等の品質チェック

- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - パッケージエントリ（将来の戦略、発注実行、監視ロジックの追加箇所）

---

## ディレクトリ構成

以下は主要ファイル構成の抜粋（src ベース）:

src/
- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
    (戦略関連モジュールを配置)
  - execution/
    - __init__.py
    (発注実行関連モジュールを配置)
  - monitoring/
    - __init__.py
    (監視・メトリクス関連を配置)

---

## 開発 / 貢献

- 新しい機能は該当サブパッケージ（data, strategy, execution, monitoring）に実装してください。
- DB スキーマを変更する場合は `kabusys.data.schema` に DDL を追記し、互換性・マイグレーション方針を検討してください。
- ネットワーク／外部 API へのアクセス部は可能な限り差し替え（モック）可能にしてテストを容易にしてください（例: news_collector の _urlopen をモック可能）。

---

## トラブルシューティング（よくある問題）

- 環境変数が見つからない:
  - `kabusys.config.Settings` のプロパティは必須キー未設定で ValueError を投げます。`.env` を作成するか OS 環境変数を設定してください。

- DuckDB ファイルの場所:
  - デフォルト `data/kabusys.duckdb`。親ディレクトリがなければ自動で作成されます。

- J-Quants 401 / トークン関連:
  - `jquants_client` は 401 を検出するとリフレッシュ（get_id_token）し1回だけリトライします。トークンが無効な場合は設定を確認してください。

- RSS 取得でリダイレクトやプライベートホストエラーが出る:
  - SSRF 対策としてプライベート IP / ホストは拒否されます。正しい公開 URL か確認してください。

---

## ライセンス・その他

本 README にはライセンス情報を含めていません。実際の運用・配布時は適切なライセンスファイルを追加してください。

---

以上がこのコードベースの README.md（日本語）です。必要があれば、導入手順のさらに詳細な手順（systemd/jupyter/cron での定期実行例、CI 設定、テストの実行方法等）を追加します。どの情報を補足しましょうか？