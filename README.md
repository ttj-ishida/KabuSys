# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ (KabuSys)

軽量な ETL、データ品質チェック、ニュース収集、監査ログ（発注〜約定のトレーサビリティ）など
日本株の自動売買システムの基盤機能を提供する Python パッケージです。

主な設計方針:
- DuckDB をデータストアに使った三層データレイヤ（Raw / Processed / Feature）と実行（Execution）層
- J-Quants API からの差分取得（レート制限・リトライ・トークン自動更新対応）
- ニュース RSS 収集は SSRF / XML Bomb 等の脅威に配慮した堅牢な実装
- ETL は冪等性（ON CONFLICT）と品質チェックを備えた安全設計
- 発注〜約定までの監査ログを別途管理しトレーサビリティを保証

---

## 機能一覧

- 環境設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化可能）
  - 必須環境変数の取得と検証
- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）のページネーション対応取得
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レート制限、リトライ、401 時のトークン自動更新、fetched_at の記録
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分更新（最終取得日に基づく自動算出）
  - バックフィル（後出し修正対応）
  - 市場カレンダー先読み、品質チェックの統合
  - run_daily_etl による一括処理
- ニュース収集
  - RSS 取得、URL 正規化（UTM 等除去）、記事ID は正規化 URL の SHA-256（先頭32文字）
  - defusedxml を用いた安全な XML パース
  - SSRF 対策（スキーム検証・プライベートIP遮断・リダイレクト検査）
  - DuckDB への冪等保存と銘柄紐付け
- データ品質チェック
  - 欠損（OHLC の NULL）
  - 主キー重複
  - 前日比スパイク検出
  - 将来日付・非営業日のデータ検出
  - QualityIssue 型で詳細を返す
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマ定義
  - UUID ベースのトレースチェーンを保証
  - 全 TIMESTAMP を UTC で保存

---

## 要件

- Python 3.10 以上（型ヒントで `X | Y` を使用）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

インストールはプロジェクトで依存定義があればそのまま、ない場合は手動で：

```bash
python -m pip install duckdb defusedxml
```

（実運用では仮想環境を推奨します）

---

## セットアップ手順

1. リポジトリをクローンする

```bash
git clone <your-repo-url>
cd <repo-root>
```

2. 仮想環境を作成（任意）

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
```

3. 環境変数を設定する（.env ファイルをプロジェクトルートに置く）

プロジェクトは起点ファイル位置から親ディレクトリに `.git` または `pyproject.toml` を探してプロジェクトルートを判断し、
`.env` / `.env.local` を自動読み込みします。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env.example`（プロジェクトルートに `.env` を作成して設定してください）

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知等で用いる場合)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で `require` されます（使用する機能に応じて必須）。

4. DuckDB スキーマ初期化

Python REPL やスクリプトから初期化できます。例:

```python
from kabusys.data import schema
from kabusys.config import settings

# ファイルパスは settings.duckdb_path で指定される（.env で上書き可）
conn = schema.init_schema(settings.duckdb_path)
```

またはコマンドラインで（簡易）:

```bash
python -c "from kabusys.data import schema; from kabusys.config import settings; schema.init_schema(settings.duckdb_path); print('init done')"
```

監査ログ（audit）テーブルを追加したい場合:

```python
from kabusys.data import audit
# conn は schema.init_schema の戻り値
audit.init_audit_schema(conn)
```

---

## 使い方（代表的な API）

以下は一例です。実際はアプリケーション側から呼び出すことを想定しています。

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得・保存・品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定すればその日で実行
print(result.to_dict())
```

- ニュース収集ジョブを実行する

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes は銘柄抽出に使う有効コードのセット（例: 取引所の 4 桁コード一覧）
known_codes = {"7203", "6758", "9984"}  # 実運用では完全なリストを用意
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants から日足を直接取得して保存する（テスト用）

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
id_token = None  # 省略時は内部キャッシュで自動取得
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

- 品質チェック単体の実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
issues = run_all_checks(conn, target_date=None, reference_date=date.today())
for i in issues:
    print(i)
```

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須、Slack 機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須、Slack 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用などで使用）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動読み込みを無効化

---

## ディレクトリ構成

プロジェクトの主要ファイル構成（一部抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py                — DuckDB スキーマ定義 & init_schema / get_connection
    - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - news_collector.py        — RSS ニュース収集 / 前処理 / 保存
    - audit.py                 — 監査ログ（signal, order_request, executions）
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py
    (戦略モジュール: シグナル生成等を配置する場所)
  - execution/
    - __init__.py
    (発注・ブローカー連携関連を配置する場所)
  - monitoring/
    - __init__.py
    (監視・メトリクス、アラート連携等)

ルート:
- pyproject.toml (存在する場合)
- .git/
- .env, .env.local  (環境変数)
- README.md (本ファイル)

---

## 開発 / テスト

- 依存パッケージは個別にインストールしてください（requirements.txt がある場合はそれを利用）
- 単体モジュールのテストを書く場合は、J-Quants 等の外部依存をモックし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って環境読み込みを制御すると便利です
- news_collector._urlopen などはテスト用に差し替え可能な設計になっています（モジュールレベルの関数をモック）

---

## 注意事項 / 運用上のポイント

- J-Quants のレート制限（120 req/min）を守るよう内部でスロットリングしていますが、実運用で大量のリクエストが想定される場合は運用設計上の配慮が必要です。
- DuckDB のファイルはアプリケーション側でバックアップやローテーションの方針を定めてください。
- 監査ログは削除しない前提（FK による制約）で設計しています。過去データの扱いに注意してください。
- 本ライブラリは基盤機能を提供するものであり、実際の売買ロジック・リスク管理・接続先の証券会社 API 実装は別途実装する必要があります。

---

以上が KabuSys の概要と導入ガイドです。README の内容は今後の実装拡張に合わせて随時更新してください。質問や追加したいドキュメントがあれば教えてください。