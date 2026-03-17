# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants（市場データ）やRSSニュースを収集して DuckDB に保存し、ETL・品質チェック・監査ログを備えたデータ基盤を提供します。取引実行（kabuステーション）や戦略モジュールと組み合わせて自動売買システムを構築できます。

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、財務諸表、JPX カレンダーの取得
  - レート制限（120 req/min）厳守、リトライ／トークン自動リフレッシュ、ページネーション対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS から記事を収集・正規化し raw_news に冪等保存
  - URL 正規化（トラッキング除去）、SSRF 対策、応答サイズ上限、XML 攻撃対策（defusedxml）
  - 記事 → 銘柄コードの紐付け機能（news_symbols）

- DuckDB スキーマ & 初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 監査ログ用スキーマ（signal / order_request / executions）を別途初期化可能

- ETL パイプライン
  - 日次差分更新（市場カレンダー → 株価 → 財務）と品質チェック
  - バックフィル機能（後出し修正吸収）、営業日自動調整
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- 監査ログ（トレーサビリティ）
  - signal → order_request → executions の UUID 連鎖でフローを完全に追跡

---

## 必要な環境変数

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視/モニタリング）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

例（`.env.example`）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# optional
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージ（例）
   - 本コードで利用している主な外部ライブラリ:
     - duckdb
     - defusedxml

   requirements.txt を作る場合の例:
   ```
   duckdb
   defusedxml
   ```

   インストール:
   ```
   pip install -r requirements.txt
   ```

3. 環境変数を用意
   - プロジェクトルートに `.env` を作成するか、上記必須変数を環境に設定します。

4. DuckDB スキーマ初期化
   - 初回は DB ファイルを初期化してテーブルを作成します（例は Python スニペット参照）。

---

## 使い方（代表的な API）

以下は簡単な Python の利用例です。プロジェクト配下で実行してください。

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
```

- J-Quants データ取得（手動でトークンを取得して呼ぶ例）:
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# トークンは settings.jquants_refresh_token を利用して内部で取得されます
quotes = jq.fetch_daily_quotes(code="7203", date_from=None, date_to=None)
# DuckDB に保存
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
jq.save_daily_quotes(conn, quotes)
```

- RSS ニュース収集と保存:
```python
from kabusys.data import news_collector
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
articles = news_collector.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
new_ids = news_collector.save_raw_news(conn, articles)
# 銘柄紐付け（known_codes を用意している場合）
known_codes = {"7203", "6758"}
if new_ids:
    pairs = []
    for art in articles:
        if art["id"] in new_ids:
            codes = news_collector.extract_stock_codes(art["title"] + " " + art["content"], known_codes)
            for c in codes:
                pairs.append((art["id"], c))
    news_collector._save_news_symbols_bulk(conn, pairs)  # 内部関数だが参考用
```

- 日次 ETL を実行する（推奨エントリポイント）:
```python
from kabusys.data.pipeline import init_schema, run_daily_etl
import duckdb
from kabusys.data.schema import init_schema as init_db_schema

conn = init_db_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 今日を対象に ETL 実行（トークンは自動管理）
print(result.to_dict())
```

- 監査スキーマ初期化（監査ログを追加したい場合）:
```python
from kabusys.data.audit import init_audit_schema
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn)
```

---

## 環境 / ログ設定

- 自動 `.env` 読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml を検出）を基準に `.env` / `.env.local` を自動で読み込みます。
  - 読み込み順: OS環境変数 > .env.local > .env
  - テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- 環境モード
  - KABUSYS_ENV は以下が有効値:
    - development
    - paper_trading
    - live
  - これによりシステムでの振る舞い（例えば実際の発注抑制など）を切り分けます。

- ログレベル
  - LOG_LEVEL で制御（デフォルト INFO）。

---

## ディレクトリ構成

パッケージの主要ファイル群（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存ロジック）
    - news_collector.py — RSS 収集・前処理・保存
    - schema.py — DuckDB スキーマ定義と初期化
    - pipeline.py — ETL パイプライン（差分更新・品質チェック）
    - audit.py — 監査ログ（signal/order_requests/executions）
    - quality.py — データ品質チェック
  - strategy/
    - __init__.py — 戦略関連のエントリ（拡張ポイント）
  - execution/
    - __init__.py — 発注実行関連（kabuステーション等を実装）
  - monitoring/
    - __init__.py — 監視・メトリクス（拡張ポイント）

（プロジェクトルート）
- .env, .env.local（任意）
- pyproject.toml / setup.cfg（配布用設定）
- requirements.txt（依存パッケージ）

---

## 開発や拡張のヒント

- 戦略層（strategy）と発注層（execution）は本パッケージの外側で独自実装することを想定しています。ETL と監査ログは共通基盤として利用できます。
- ETL では id_token を注入可能にしてあるため、ユニットテスト時は get_id_token の呼び出しをモックしてテストできます。
- news_collector は SSRF・XML 爆弾対策やレスポンスサイズ上限などセキュリティに配慮した実装になっています。外部ソースの追加は DEFAULT_RSS_SOURCES を拡張してください。
- DuckDB はファイルベースで軽量に動作します。データ量が増える場合は適切なファイル配置とバックアップを検討してください。

---

## ライセンス / コントリビューション

本リポジトリのライセンスとコントリビューションルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

---

README の内容や使用例の追加（Slack 通知、kabuステーション連携、CI/CD 用のジョブ定義など）を希望する場合は、目的に合わせたサンプルやテンプレートを追加で用意します。必要な内容を教えてください。