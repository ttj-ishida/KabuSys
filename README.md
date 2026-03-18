# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ層）。  
データ取得・ETL・品質チェック・監査ログ・ニュース収集など、トレーディングシステムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買プラットフォームを構成する内部コンポーネント群です。  
主な設計方針：

- J-Quants API を用いた市場データ（株価日足・財務・マーケットカレンダー）の取得
- DuckDB を用いたローカルデータベース（スキーマ設計・冪等保存）
- ETL パイプライン（差分更新・バックフィル）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と銘柄抽出
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）
- セキュリティ考慮（SSRF対策、XML攻撃対策、受信サイズ制限、レート制御 等）

ライブラリはモジュール単位で提供され、戦略層（strategy/）や発注実行層（execution/）とは分離されています（strategy と execution パッケージはエントリのみ）。

---

## 主な機能一覧

- 環境設定管理（自動 .env 読み込み、必須環境変数チェック）
- J-Quants API クライアント
  - 株価日足（OHLCV）/ 財務データ（四半期）/ マーケットカレンダー取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
- DuckDB スキーマ定義および初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集モジュール（RSS → 前処理 → DuckDB に冪等保存）
  - URL 正規化、トラッキングパラメータ除去、SSRF/圧縮バイパス対策
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）
- マーケットカレンダー管理（営業日判定、次/前営業日取得、夜間更新ジョブ）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化

---

## 要件

- Python 3.10 以上（型ヒントで | を使用しているため）
- 必須ライブラリ（最低限）:
  - duckdb
  - defusedxml
- （HTTP 操作には標準ライブラリ urllib を利用）

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクト配布形態に合わせて requirements.txt / pyproject.toml を整備してください。

---

## セットアップ手順

1. リポジトリをチェックアウト / コピー
2. 必要なパッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   # または最低限:
   python -m pip install duckdb defusedxml
   ```
3. 環境変数を設定
   - プロジェクトルートに `.env` および（任意で）`.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。
4. DuckDB スキーマ初期化（下記参照）

必須環境変数（ライブラリが参照する主要設定）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

オプション（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 開発環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

注意: settings オブジェクトから必須変数が見つからないと ValueError が発生します。

---

## データベース初期化（例）

DuckDB スキーマを初期化して接続を得る例:

```python
from kabusys.data import schema

# ファイル DB を作成してスキーマを初期化
conn = schema.init_schema("data/kabusys.duckdb")
# インメモリ DB を使う場合:
# conn = schema.init_schema(":memory:")
```

監査ログ専用 DB を初期化する例:

```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要 API の例）

- ETL（日次処理）を実行する:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 当日分の ETL を実行（品質チェック有効）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブを実行する:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes は銘柄コードセット（例: {"7203", "6758", ...}）
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)  # {source_name: new_count, ...}
```

- J-Quants クライアントを直接使ってデータ取得→保存:

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 例: ある銘柄の過去日足を取得して保存
records = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

- 環境設定を参照する:

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

---

## 注意点 / 実装上の挙動

- J-Quants クライアントは 120 req/min のレート制御を内部で行います（_RateLimiter）。
- HTTP 失敗時は最大 3 回のリトライ（指数バックオフ）。401 はトークン自動リフレッシュを一度試行します。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）として実装されています。
- NewsCollector は XML の脆弱性対策に defusedxml を使用し、SSRF 対策・受信バイト上限などを備えています。
- カレンダー情報が不足する場合、営業日判定は曜日（土日）でのフォールバックを行います。
- settings は自動でプロジェクトルート（.git または pyproject.toml）を探索し、.env/.env.local を読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  -- 環境設定 / .env 自動ロード
    - data/
      - __init__.py
      - jquants_client.py    -- J-Quants API クライアント（取得・保存）
      - news_collector.py    -- RSS ニュース収集・前処理・保存
      - schema.py            -- DuckDB スキーマ定義・初期化
      - pipeline.py          -- ETL パイプライン（差分更新 / 品質チェック）
      - calendar_management.py -- マーケットカレンダー管理（営業日判定・更新ジョブ）
      - audit.py             -- 監査ログスキーマ（信頼可能なトレーサビリティ）
      - quality.py           -- データ品質チェック
    - strategy/
      - __init__.py          -- 戦略層エントリ（拡張用）
    - execution/
      - __init__.py          -- 発注実行層エントリ（拡張用）
    - monitoring/
      - __init__.py          -- 監視用コンポーネント（空）

各モジュールはドキュメント文字列とログ出力を備えており、外部から関数を呼び出してパイプラインを組み立てられるようになっています。

---

## 開発・運用メモ

- テスト時は .env の自動ロードを無効にし、テスト環境専用の環境変数注入を推奨します。
  - 例: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB ファイルはデフォルトで data/ 配下に配置されます。パスは settings.duckdb_path で変更可能です。
- ログレベルは環境変数 LOG_LEVEL で制御可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 本 README はコードベースの概観を示すもので、運用ポリシー（発注の安全策、資金管理、実動作の監査等）は別途策定してください。

---

この README はコードベースの主要機能とセットアップ方法をまとめたものです。実装や API を拡張する場合は各モジュールの docstring を参照してください。