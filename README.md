# KabuSys

KabuSys は日本株のデータ収集・品質チェック・特徴量作成・監査ログを備えた自動売買基盤の骨格ライブラリです。J-Quants API や RSS を用いたニュース収集、DuckDB ベースのデータレイヤと ETL パイプライン、監査（audit）スキーマなどを提供します。

---

## 主要な特徴

- データ収集
  - J-Quants API からの株価（日足 OHLCV）、財務データ、JPX マーケットカレンダー取得（ページネーション対応）
  - RSS フィードからのニュース収集（URL 正規化 / トラッキングパラメータ除去、SSRF 対策、XML 脆弱性対策）
- ETL / パイプライン
  - 差分更新（最終取得日に基づく差分取得、バックフィル対応）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- 永続化 / スキーマ
  - DuckDB を用いた階層的データレイヤ（Raw / Processed / Feature / Execution）
  - 監査ログ用スキーマ（signal_events, order_requests, executions 等）
- セキュリティ・堅牢性設計
  - API レート制限（120 req/min）を遵守する RateLimiter、リトライ（指数バックオフ）実装
  - ニュース収集での SSRF 防止、受信サイズ上限、defusedxml を利用した XML パース保護
  - 冪等性（ON CONFLICT ... DO UPDATE / DO NOTHING）を意識した DB 保存

---

## 機能一覧（モジュール概要）

- kabusys.config
  - .env / 環境変数の自動読み込み（.env, .env.local）
  - settings オブジェクト経由で各種設定を取得
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- kabusys.data.news_collector
  - fetch_rss（RSS 取得・パース）
  - save_raw_news / save_news_symbols / run_news_collection（DuckDB へ保存）
- kabusys.data.schema
  - init_schema / get_connection（DuckDB スキーマの初期化）
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl（統合 ETL、品質チェック含む）
- kabusys.data.calendar_management
  - calendar_update_job, is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査ログスキーマ初期化）
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

（strategy, execution, monitoring パッケージはエントリもしくは拡張ポイントとして用意）

---

## セットアップ手順

前提: Python 3.9+（ソースは型ヒントに | を用いているため Python 3.10 以上が望ましい）。必要パッケージは最低限以下。

必須依存（例）
- duckdb
- defusedxml

仮想環境を作成してインストールする例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発用にパッケージ化されている場合:
# pip install -e .
```

環境変数は .env または OS の環境変数で指定できます。プロジェクトルート（.git または pyproject.toml を含む場所）を自動検出し、優先順は OS 環境変数 > .env.local > .env です。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

その他（任意）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live (デフォルト: development)
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

サンプル .env（プロジェクトルートに配置）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

1) DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を生成・テーブル作成
```

2) 日次 ETL を実行（run_daily_etl）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
```

run_daily_etl は市場カレンダー取得→株価取得→財務データ取得→品質チェック の順で実行し、ETLResult を返します。

3) ニュース収集ジョブ（run_news_collection）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は抽出した銘柄コード判定に使う既知コード集合（例: 全銘柄リスト）
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

4) J-Quants の ID トークン取得 / データフェッチ

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を使って取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

5) 監査ログ（audit）スキーマの初期化

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)  # 監査用テーブルを追加
```

6) カレンダー管理ユーティリティ

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

is_td = is_trading_day(conn, date(2025, 1, 1))
next_td = next_trading_day(conn, date.today())
```

注意点:
- jquants_client はレート制限（120 req/min）遵守のため内部で待機し、HTTP エラーに対してリトライやトークンの自動リフレッシュを行います。
- news_collector は SSRF、XML Bomb、過大レスポンスなどを防ぐ設計になっていますが、実運用では取得ソースの管理と監視を行ってください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトのルートに `src/kabusys` 配下に実装があります。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py               — RSS ニュース収集と保存
    - schema.py                       — DuckDB スキーマ定義 / init_schema
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py          — マーケットカレンダー管理 / 営業日判定
    - audit.py                        — 監査ログスキーマ初期化
    - quality.py                      — データ品質チェック
  - strategy/
    - __init__.py                     — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                     — 発注・実行層（拡張ポイント）
  - monitoring/
    - __init__.py                     — 監視（拡張ポイント）

---

## 開発上の注意・設計に関する補足

- 環境自動読み込み:
  - プロジェクトルートが .git または pyproject.toml で検出される場合、.env と .env.local を自動で読み込みます。
  - OS の環境変数を優先し、.env.local は .env 上の設定を上書き可能です。
  - 自動読み込みを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- データ一貫性:
  - DuckDB への保存操作は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）しています。
  - ETL はバックフィルを行い API の後出し修正を吸収する設計です。
- セキュリティ:
  - news_collector は defusedxml を使用し、リダイレクト時にプライベートアドレスや非 http(s) スキームを拒否します。
  - URL 正規化やトラッキングパラメータ削除により記事の冪等性を担保します。
- ログ・監視:
  - 設定の LOG_LEVEL によりログ出力レベルを制御します（DEBUG/INFO/...）。
  - Slack 通知や別途監視層を実装することで運用的な監視を推奨します。

---

## 例: 簡単な運用スクリプト

run_etl.py（概念例）:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

def main():
    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn)
    print(result.to_dict())

if __name__ == "__main__":
    main()
```

---

必要に応じて README にサンプルの .env.example、CI ワークフロー、依存関係ファイル（requirements.txt / pyproject.toml）や実運用での注意事項（API 使用量の監視、トークンのローテーション、監査ログ保管ポリシーなど）を追加できます。必要ならそれらのテンプレートも作成します。どの情報を追記しましょうか？