# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ用 README

このドキュメントはコードベースに含まれるモジュール群の概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python モジュール群です。  
主な目的は以下の通りです。

- J-Quants API 等からのマーケットデータ取得（株価日足、財務データ、マーケットカレンダー）
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いたデータスキーマの管理（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- （将来的には）戦略・発注（execution）・モニタリングの統合

設計上の特徴：
- API レートリミット遵守、リトライロジック、トークン自動リフレッシュ
- データ取得時に fetched_at を記録して Look‑ahead bias を防止
- DuckDB への保存は冪等（ON CONFLICT）で上書き/重複除去
- RSS 収集時の SSRF / XML Bomb 等の安全対策やレスポンスサイズ制限

---

## 機能一覧

主要な機能モジュールとその役割：

- kabusys.config
  - 環境変数の読み込み（.env / .env.local の自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定の取得ラッパー（settings オブジェクト）
  - 実行環境判定（development / paper_trading / live）とログレベル検証

- kabusys.data.jquants_client
  - J-Quants API クライアント（ID トークン取得、自動リフレッシュ）
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - DuckDB へ冪等に保存する save_* 関数

- kabusys.data.news_collector
  - RSS フィード取得・パース・前処理（URL 除去・空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF / プライベートアドレス / gzip サイズ検査 等の安全対策
  - raw_news / news_symbols への保存（チャンク挿入・トランザクション）

- kabusys.data.schema
  - DuckDB の全テーブル定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) で初期化して接続を返す
  - get_connection() で既存 DB の接続を取得

- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）: 市場カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新、バックフィル、品質チェック（欠損・重複・スパイク・日付整合性）
  - ETLResult により実行結果を集約

- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - QualityIssue を返すことで問題を詳細に報告

- kabusys.data.audit
  - 監査ログ用テーブルの初期化（signal_events / order_requests / executions）
  - 発注・約定のトレーサビリティを保証

その他:
- strategy/, execution/, monitoring/ はパッケージスケルトン（将来機能追加想定）

---

## セットアップ手順

前提:
- Python 3.10 以上（`Path | None` 等の構文を使用）
- 仮想環境の利用を推奨

1. リポジトリをクローンし仮想環境を作成
```bash
git clone <repository-url>
cd <repository>
python -m venv .venv
source .venv/bin/activate   # Unix/macOS
# .venv\Scripts\activate     # Windows
```

2. 依存パッケージをインストール（最低限）
```bash
pip install duckdb defusedxml
```
※ 実プロダクションではロギング・Slack や HTTP ライブラリ等の追加依存が必要になる場合があります。プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください。

3. パッケージを開発モードでインストール（任意）
```bash
pip install -e .
```

4. 環境変数の設定
以下の環境変数が少なくとも必要です（用途に応じて）：

必須（J-Quants / kabu API / Slack 等を使う場合）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- LOG_LEVEL (DEBUG / INFO / ...) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

プロジェクトルートに `.env` / `.env.local` を置くと、kabusys.config が自動で読み込みます（OS 環境を上書きしない挙動や `.env.local` の上書き動作あり）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル `.env`（例）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

以下は主要ユースケースの最小サンプルです。実運用ではログ設定やエラーハンドリング、認証情報保護等が必要です。

1) DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema

# ファイル DB を作成してスキーマを初期化
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date, id_token 等を引数で渡せます
print(result.to_dict())
```

3) J-Quants から株価を直接取得する
```python
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
print(len(records))
```

4) RSS ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出に使う有効銘柄コードのセット
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

5) 監査ログ（audit）用スキーマを初期化する（既存の conn に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

注意点:
- J-Quants API 呼び出しはレート制限に従います（120 req/min）。
- API トークンは自動リフレッシュされますが、リフレッシュトークンは環境変数で提供する必要があります。
- ETL の品質チェックは run_daily_etl のオプションで制御できます（spike_threshold 等）。

---

## ディレクトリ構成

リポジトリ内に含まれる主要ファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境設定ロード / Settings
  - data/
    - __init__.py
    - jquants_client.py             -- J‑Quants API クライアント、取得／保存関数
    - news_collector.py             -- RSS ニュース収集・前処理・DB 保存
    - pipeline.py                   -- ETL パイプライン
    - schema.py                     -- DuckDB スキーマ定義と init_schema
    - audit.py                      -- 監査ログ（signal/order/execution）スキーマ
    - quality.py                    -- データ品質チェック
  - strategy/
    - __init__.py                   -- 戦略モジュール（拡張用）
  - execution/
    - __init__.py                   -- 発注関連（拡張用）
  - monitoring/
    - __init__.py                   -- 監視 / メトリクス（拡張用）

（ファイル構成は開発状況により変化します）

---

## 追加情報 / 運用上の注意

- 環境（KABUSYS_ENV）が `live` の場合は実際の発注処理を厳重にテストした上で有効化してください。paper_trading モードや development モードを活用して検証を行ってください。
- ニュース収集は外部 HTTP に依存するため、タイムアウトやネットワーク障害、RSS 形式差異に対して堅牢化されていますが、監視（ログ・Slack 通知等）を行うことを推奨します。
- DuckDB ファイルはバックアップやローテーションが必要になる場合があります。DB ファイルの配置（DUCKDB_PATH）や権限設定には注意してください。
- セキュリティ：.env ファイルに API トークン等を平文で置く場合はリポジトリに含めないようにし、適切なアクセス制御を行ってください。

---

問題・改善提案や追加したい機能があれば issue を作成してください。