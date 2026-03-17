# KabuSys

日本株の自動売買・データ基盤ライブラリ（パイロット実装）

このリポジトリは日本株向けのデータパイプライン、データ品質チェック、監査ログ、ニュース収集などを含む内部ライブラリ群を提供します。J-Quants API や kabuステーション（発注系）は想定に合わせて組み合わせて使います。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤに沿ったデータ基盤／自動売買のためのコンポーネントを提供します。

- データ取得（J-Quants API）と DuckDB への永続化（Raw / Processed / Feature / Execution レイヤ）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS → raw_news、記事と銘柄の紐付け）
- マーケットカレンダー管理（営業日判定、夜間更新ジョブ）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 設定管理（.env / 環境変数の自動読み込み）

パッケージはモジュール単位で利用できるよう設計されており、ETL バッチや運用スクリプトから簡単に呼び出せます。

---

## 主な機能一覧

- 環境変数/設定読み込み（.env / .env.local をプロジェクトルートから自動読み込み、無効化フラグあり）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得
  - レート制限（120 req/min）対応、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集
  - RSS 取得、XML 安全パース（defusedxml）、URL 正規化、トラッキングパラメータ除去
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証 / プライベートホスト拒否）、受信サイズ上限
  - DuckDB への冪等保存（INSERT ... RETURNING を活用）
  - 記事と銘柄コード（4桁）紐付け機能
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit テーブル群の DDL を定義・初期化
  - インデックスや監査用テーブルの初期化関数を提供
- ETL パイプライン
  - 差分更新ロジック（最終取得日を確認して必要分のみ取得）
  - カレンダー先読み、バックフィル対応
  - 品質チェックを統合して結果を ETLResult として返却
- マーケットカレンダーヘルパー
  - 営業日判定、次/前営業日取得、営業日リスト取得、カレンダー更新ジョブ
- データ品質チェック
  - 欠損、重複、スパイク（前日比）や日付整合性チェック

---

## 前提条件（推奨）

- Python 3.10+
  - 型注釈で union 演算子（|）を使用しているため Python 3.10 以上を想定しています
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

例:
pip install duckdb defusedxml

（プロジェクトで requirements.txt/poetry を用意している場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. Python 仮想環境を作成して有効化（例）
- python -m venv .venv
- source .venv/bin/activate  # macOS / Linux
- .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
- pip install duckdb defusedxml

（プロジェクトに packaging ファイルがあれば pip install -e . 等を実行）

4. 環境変数を設定
- プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必要な環境変数（Settings クラスより）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live; デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL; デフォルト: INFO)

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（サンプル）

以下は代表的な操作の例です。実運用ではエラーハンドリングやログ設定を追加してください。

- DuckDB スキーマ初期化
```
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
```

- 既存 DB へ接続
```
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄コード集合（抽出に使用）
known_codes = {"7203", "6758", ...}
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)
```

- カレンダー夜間更新ジョブ
```
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 監査スキーマ初期化（audit 用）
```
from kabusys.data import schema
from kabusys.data import audit

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

- 設定の参照
```
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.env, settings.log_level)
```

---

## ディレクトリ構成

リポジトリ内の主要ファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動読み込み等）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得 + 保存関数）
    - news_collector.py           — RSS ニュース収集・保存・銘柄抽出
    - schema.py                   — DuckDB スキーマ定義・初期化
    - pipeline.py                 — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py      — 市場カレンダー周りのユーティリティ・更新ジョブ
    - audit.py                    — 監査ログ（シグナル・発注・約定の DDL / 初期化）
    - quality.py                  — データ品質チェック（欠損・重複・スパイク等）
  - strategy/
    - __init__.py                 — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py                 — 発注/ブローカー接続モジュール（拡張ポイント）
  - monitoring/
    - __init__.py                 — 監視・メトリクス系（拡張ポイント）

---

## 設計上のポイント / 注意事項

- DuckDB をメインの永続層として想定（軽量で SQL が使えるため ETL と解析に便利）
- J-Quants API のレート制限（120 req/min）対策とリトライ／トークンリフレッシュを組み込み済み
- ニュース収集は SSRF 対策・XML 安全パース・受信サイズ制限を設けて安全性に配慮
- ETL は「全体を止めない」設計（各ステップは独立して例外処理し、結果を集約して返す）
- 環境変数の自動読み込みはプロジェクトルート検出に依存（.git または pyproject.toml）
  - テスト時などに自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 貢献 / 拡張

- strategy/ や execution/ 、monitoring/ は拡張ポイントとして用意しています。戦略実装、ブローカー接続、監視ダッシュボードをここに実装してください。
- 新しいデータソースや品質チェックを追加する場合は data/ 配下にモジュールを追加し、schema.py に必要なテーブル定義を追記してください。

---

## ライセンス

本 README ではライセンスは明示していません。実プロジェクト化する際は適切なライセンスファイル（LICENSE）を追加してください。

---

必要であれば、README に実行例やより詳細な設定例、運用手順（systemd / cron / Docker コンテナ化 など）を追記します。どの項目を詳細化したいか教えてください。