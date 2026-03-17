# KabuSys

日本株自動売買システムの共通ライブラリ群（データ取得・ETL・スキーマ・監査・ニュース収集など）。

このリポジトリは、J-Quants API や RSS フィードからデータを取得して DuckDB に保存・品質チェックし、戦略層 / 実行層と連携するための基盤機能を提供します。

---

## 主な特徴（機能一覧）

- 環境変数ベースの設定管理
  - .env / .env.local 自動ロード（必要に応じて無効化可）
- J-Quants API クライアント（jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得
  - レート制限（120 req/min）遵守、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（news_collector）
  - RSS フィードから記事を取得・前処理・ID化（正規化URL の SHA-256）
  - SSRF対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
  - レスポンスサイズ上限・gzip 解凍抑制・XML パース安全化（defusedxml）
  - DuckDB へのバルク保存（INSERT ... RETURNING、トランザクション）
  - 記事 → 銘柄コード紐付け（テキストから4桁銘柄コード抽出）
- DuckDB スキーマ定義と初期化（schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義、冪等な初期化 API
- ETL パイプライン（pipeline）
  - 差分更新（最終取得日を参照）、バックフィル、品質チェックの統合
  - 日次 ETL 実行エントリ（run_daily_etl）
- マーケットカレンダー管理（calendar_management）
  - 営業日判定 / 前後営業日取得 / カレンダー夜間更新ジョブ
- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue データ構造で問題を集約
- 監査ログ（audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブル群と初期化 API
- 軽量なパッケージ構成で戦略・実行モジュールを独立（strategy/, execution/, monitoring/ の用意）

---

## 動作環境 / 依存

- Python 3.10+
- 必要な Python パッケージ（一部例）
  - duckdb
  - defusedxml
- OS 環境変数または .env ファイルにて設定を提供

（パッケージ管理・バージョンはプロジェクト側で requirements.txt / pyproject.toml を用意してください）

---

## 環境変数（主要なもの）

以下はコード内で必須/使用される主な環境変数例です。`.env.example` を参考に `.env` を作成してください。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化（テスト用）

設定をコードから取得する例:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

自動 .env ロードの挙動:
- プロジェクトルートは __file__ の親ディレクトリ群から `.git` または `pyproject.toml` を検索して判定します。
- 自動ロードを無効化したいテスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を用意
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   ```
   実際はプロジェクトの requirements.txt / pyproject.toml を参照してインストールしてください。

3. 環境変数を用意
   - `.env.example` を参考に `.env` をプロジェクトルートに作成
   - または環境変数としてエクスポート

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   - 監査ログ専用 DB を別に用意する場合:
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
# known_codes に取引対象の銘柄コードセットを渡すと銘柄紐付けを実行
res = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

- J-Quants から日足を直接取得して保存
```python
from kabusys.data import jquants_client as jq
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"Saved: {saved}")
```

- 監査スキーマの初期化（既存接続に追加）
```python
from kabusys.data import schema, audit
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

---

## 設計上の注意点 / 実装ノート

- J-Quants クライアントは 120 req/min のレート制限に合わせた固定間隔スロットリングを実装しています。複数スレッド/プロセスでの同時呼び出し時は注意が必要です（モジュールローカルの RateLimiter を使用）。
- HTTP エラー：408/429/5xx に対して指数バックオフで最大 3 回リトライします。429 の場合は Retry-After ヘッダを優先します。
- 401 エラー（トークン期限切れ）時は J-Quants の refresh token から id_token を再取得して 1 回リトライします。
- ニュース収集は SSRF、XML Bomb、巨大レスポンス等の攻撃に対する複数の防御を実装しています（defusedxml、最大受信バイト数、プライベートアドレス検査など）。
- DuckDB への保存は可能な限り冪等性を保つ（ON CONFLICT 句、INSERT ... RETURNING を活用）。
- スキーマ初期化関数は冪等（IF NOT EXISTS）であり、既存 DB に対して何度でも安全に実行できます。
- データ品質チェックは Fail-Fast ではなく、問題をすべて列挙して呼び出し元の方針で取り扱う設計です。

---

## ディレクトリ構成

（主要なファイル/モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS ニュース収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — マーケットカレンダー管理
    - audit.py                      — 監査ログスキーマ初期化
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略関連モジュール（将来的な実装）
  - execution/
    - __init__.py                   — 発注/実行関連モジュール（将来的な実装）
  - monitoring/
    - __init__.py                   — モニタリング用モジュール（将来的な実装）

---

## 開発者向けヒント

- テスト時に自動 .env ロードを無効にする:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定しておく
- ETL のデバッグや単体機能確認には DuckDB のインメモリ DB を利用:
  ```python
  conn = schema.init_schema(":memory:")
  ```
- ニュース収集の HTTP 周りやリダイレクトの挙動は `news_collector._urlopen` をモックしてテスト可能（ドメイン/ネットワークに依存しないテストが可能）。

---

必要に応じて README にサンプル .env.example や requirements ファイル、実行用スクリプトを追加すると導入がよりスムーズになります。追加で記載したい内容（例: CI / デプロイ手順、Slack 通知の例、kabuステーション API 連携サンプル等）があれば指示ください。