# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants や RSS を取り込み、DuckDB に冪等的に保存して品質チェックや ETL パイプライン、監査ログ（発注→約定トレーサビリティ）を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT を利用）で再実行可能
- API レート制限・リトライ・トークン自動更新を実装
- Look-ahead bias を防ぐため fetched_at / UTC タイムスタンプでトレース
- RSS 収集は SSRF・XML Bomb 等に配慮した堅牢な実装

---

## 機能一覧
- 環境設定読み込み（.env / 環境変数、自動ロード）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミット制御・指数バックオフリトライ・401 時トークン自動更新
- RSS ニュース収集器
  - URL 正規化・トラッキングパラメータ除去・記事ID は SHA-256 ハッシュ
  - SSRF 対策（スキーム検証、プライベート IP ブロック、リダイレクト検査）
  - 圧縮レスポンス・サイズ制限（メモリ DoS 対策）
  - DuckDB への冪等保存（INSERT ... RETURNING）
  - 記事と銘柄コードの紐付け（抽出ロジック）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン
  - 差分取得（最終取得日からの差分 or 初回全取得）
  - backfill 設定により過去数日を再取得して後出し修正を吸収
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリポイント `run_daily_etl`
- マーケットカレンダー管理（営業日判定、前後営業日の取得、夜間更新ジョブ）
- 監査ログ（シグナル → 発注要求 → 約定）テーブル群の初期化
- データ品質チェックモジュール（QualityIssue 型で詳細を返す）

---

## 必要要件
- Python 3.9+
- 主要依存ライブラリ（例）:
  - duckdb
  - defusedxml

任意 / 環境による:
- ネットワークアクセス（J-Quants API、RSS フィード）
- kabuステーション API（発注実装を行う場合）

例: 必要パッケージをインストールする
```bash
pip install duckdb defusedxml
# パッケージを開発モードでインストールする場合
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 依存パッケージをインストール
   - duckdb, defusedxml など（上記参照）

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

必須の環境変数（このパッケージの設定クラスで参照されます）:
- JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン
- KABU_API_PASSWORD … kabuステーション API のパスワード（発注を行う場合）
- SLACK_BOT_TOKEN … Slack 通知に使う Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID … Slack チャネル ID

その他（任意、デフォルトあり）:
- KABUSYS_ENV … development | paper_trading | live（デフォルト: development）
- LOG_LEVEL … DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH … 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方

以下は基本的な利用例です。コードスニペットは Python REPL やスクリプトで実行できます。

1) DuckDB スキーマの初期化
```python
from kabusys.data import schema

# ファイル DB に初期化
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) J-Quants から株価を取得して保存（個別実行）
```python
from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# 例: 2024-01-01 から今日までの株価を取得して保存
records = jq.fetch_daily_quotes(date_from="20240101", date_to="20240301")
jq.save_daily_quotes(conn, records)
```

3) 日次 ETL（推奨: pipeline を使う）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

4) RSS ニュース収集ジョブ（例）
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# 既定のソースを使うか、独自の sources 辞書を渡す
res = news_collector.run_news_collection(conn)
print(res)  # {source_name: saved_count, ...}
```

5) 監査ログスキーマの初期化（audit レイヤー）
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

設計上のテスト性:
- J-Quants の id_token は外部から注入可能（関数引数 id_token）でテストが容易
- news_collector._urlopen はテストでモック可能

---

## 主要モジュールの説明（簡易）

- kabusys.config
  - .env 自動読み込み（.git または pyproject.toml を基準にプロジェクトルートを探索）
  - 環境変数のパース（クォート・コメント処理）
  - Settings クラスで設定値を提供

- kabusys.data.jquants_client
  - API 呼び出し実装、レート制御（120 req/min）、リトライ、token refresh
  - fetch_* / save_* 系関数を提供（DuckDB へ冪等保存）

- kabusys.data.news_collector
  - RSS フィード取得、XML パース（defusedxml）、前処理、記事保存、銘柄抽出
  - SSRF・Gzip・サイズ制限等の保護処理

- kabusys.data.schema
  - DuckDB の DDL（Raw / Processed / Feature / Execution）と初期化関数

- kabusys.data.pipeline
  - ETL の差分ロジック、backfill、品質チェック（quality）との連携
  - run_daily_etl が主要なエントリポイント

- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job（夜間更新）

- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合のチェックを行い QualityIssue を返す

- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）の DDL と初期化

---

## ディレクトリ構成

（リポジトリのルートに src/ を置く構成を想定）

- src/
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
      - (戦略関連モジュールを配置)
    - execution/
      - __init__.py
      - (発注・ブローカー連携モジュールを配置)
    - monitoring/
      - __init__.py

---

## 運用上の注意 / 補足
- 環境変数自動読み込み:
  - 優先順: OS 環境変数 > .env.local > .env
  - OS 環境変数は protected として上書きされません
  - 自動ロードはルート判定（.git または pyproject.toml）を使うため、パッケージ配布後も安全に動作します
- セキュリティ:
  - news_collector は SSRF と XML 攻撃対策を実装していますが、追加の検査やフィードホワイトリスト運用を推奨します
- J-Quants のレート制限・リトライ:
  - 内部で固定間隔スロットリングと指数バックオフを組み合わせています
- ロギング:
  - LOG_LEVEL と KABUSYS_ENV により挙動やログ出力を切り替え可能
- 発注周り（kabu API）:
  - 本リポジトリには発注の基盤テーブル（orders/trades/positions/audit）や設定がありますが、
    実際のブローカー連携・リスク管理ロジックは別途実装が必要です

---

必要に応じて README を拡張して、セットアップ手順（システムサービス化 / cron / Airflow での運用例）、CI/CD やロギング／モニタリングの実例を追加できます。追加したい内容があれば教えてください。