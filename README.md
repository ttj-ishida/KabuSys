# KabuSys

日本株向け自動売買データ基盤ライブラリ（KabuSys）の軽量 README。  
このリポジトリはデータ取得（J-Quants）、ETL パイプライン、ニュース収集、DuckDB スキーマ、監査ログ用スキーマなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたデータ基盤ライブラリです。主に以下を目的としています。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レートリミット・リトライ・トークン自動リフレッシュ対応）
- RSS ベースのニュース収集（SSRF 対策・トラッキングパラメータ除去・冪等保存）
- DuckDB に対するスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティを確保）

設計上、API のレート制御・リトライ・ID トークン自動更新、データ保存の冪等性（ON CONFLICT）、
ニュース収集時のセキュリティ（SSRF 対策・XML 脆弱性対策）に配慮しています。

---

## 機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミット（120 req/min）とリトライ（指数バックオフ、401 時のトークン自動更新）
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar 等）

- ニュース収集（RSS）
  - RSS フィード取得、前処理（URL 除去・空白正規化）
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256（先頭32文字）で記事ID生成（冪等）
  - defusedxml を使用した安全な XML パース
  - SSRF 対策（スキーム検証、ホスト/IP のプライベート判定、リダイレクト検査）
  - DuckDB へのバルク挿入（トランザクション・チャンク処理）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution のテーブル DDL を定義
  - 初期化関数（init_schema）で必要なテーブル・インデックスを作成

- ETL パイプライン
  - 日次 ETL（カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
  - 差分取得（最終取得日を基に自動算出）と backfill
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- 監査ログ（Audit）
  - signal_events / order_requests / executions など監査用テーブル
  - init_audit_schema / init_audit_db による初期化（UTC タイムゾーン固定）

---

## 必要環境 / 依存ライブラリ

主な依存ライブラリ（例）:

- Python 3.9+
- duckdb
- defusedxml

インストール例:

```bash
python -m pip install duckdb defusedxml
```

※他に標準ライブラリ（urllib 等）を使用します。必要に応じてプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（任意）
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（またはプロジェクトルートに `.env` / `.env.local` を用意）

重要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（任意、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（任意、デフォルト: data/monitoring.db）
- KABUSYS_ENV: 開発環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

自動 .env ロード:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順で読み込みます。
- テストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 `.env`（参考）:

```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な API と実行例）

以下は Python REPL やスクリプトでの基本的な使い方例です。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

2) 監査ログ用 DB 初期化（監査専用 DB を分離する場合）

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL を実行（J-Quants から差分取得→保存→品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
# 既に init_schema で conn を作成している想定
result = run_daily_etl(conn)
print(result.to_dict())
```

- 引数で `target_date` / `id_token` / `run_quality_checks` / `backfill_days` などを調整できます。

4) ニュース収集ジョブを実行（RSS 取得 → raw_news 保存 → 銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効コード集合 (例: DB から収集)
known_codes = {"7203", "6758", "6954", ...}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

5) J-Quants クライアント単体使用例

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# id_token を明示的に渡すことも、モジュールキャッシュを使うことも可能
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
```

注意点:
- J-Quants へのリクエストは内部でレート制御・リトライ処理されます。
- 401 受信時はトークンを自動リフレッシュして 1 回だけリトライします。

---

## 監視・品質チェック

ETL 実行後、品質チェック（quality モジュール）で以下を検査できます。

- 欠損データ（OHLC の NULL）
- 主キー重複
- スパイク（前日比の急変）
- 日付不整合（未来日付、非営業日のデータ）

run_daily_etl 内で既定で品質チェックが実行されますが、個別に `quality.run_all_checks(conn, ...)` を呼ぶことも可能です。

---

## ディレクトリ構成

ソースの主要構成（`src/kabusys` 以下）:

- kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - news_collector.py      # RSS ニュース収集・前処理・保存
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（差分更新、品質チェック）
    - calendar_management.py # マーケットカレンダー運用ヘルパー
    - audit.py               # 監査ログスキーマ・初期化
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py            # 戦略関連モジュール（プレースホルダ）
  - execution/
    - __init__.py            # 発注実行関連（プレースホルダ）
  - monitoring/
    - __init__.py            # 監視・メトリクス（プレースホルダ）

ドキュメント参照元（実装を説明する設計ドキュメント等）はリポジトリ内の DataPlatform.md や関連ドキュメントを参照してください（存在する場合）。

---

## 運用上の注意 / ベストプラクティス

- 環境変数やシークレットは `.env` に保存する場合、適切にアクセス制御を行ってください。リポジトリに `.env` をコミットしないでください。
- DuckDB のファイルはバックアップと排他制御（複数プロセスからの同時書き込み設計）に注意してください。運用環境では DB の取り扱い方針を定めてください。
- ニュース収集や外部 URL のアクセスは SSRF・XML リスクに対処していますが、追加のセキュリティポリシー（ネットワーク ACL、プロキシ経由のアクセス制御等）を推奨します。
- J-Quants の API レート制限を守るため、複数のワーカーを並列で回す場合は総リクエスト数に注意してください。

---

## ライセンス / 貢献

本 README はソースから自動生成された情報に基づいています。実際に利用・変更する際は、リポジトリのライセンスファイル（LICENSE）を確認してください。  
バグ報告や機能追加のプルリクエストは歓迎します。

---

以上。実行上の具体的な要件（Python バージョン、追加パッケージ、CI 設定など）はリポジトリの他ファイル（pyproject.toml / requirements.txt / docs）を参照してください。