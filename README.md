# KabuSys

日本株向け自動売買基盤（KabuSys）のリポジトリ概要ドキュメントです。  
この README ではプロジェクトの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめています。

補足：
- 本リポジトリは Python パッケージ（src/kabusys）として構成されています。
- 永続化には DuckDB を利用します。ニュース処理には defusedxml を用いた安全な XML パースを行います。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム基盤です。  
J-Quants（株価・財務・マーケットカレンダー）や RSS（ニュース）を取り込み、DuckDB に蓄積・整形し、品質チェックや監査ログを備えた堅牢なデータレイヤーと ETL を提供します。将来、戦略（strategy）、実行（execution）、監視（monitoring）モジュールと連携して運用できる設計です。

設計上のポイント：
- J-Quants API のレート制限順守（120 req/min）・リトライ・トークン自動リフレッシュ
- DuckDB への冪等的保存（ON CONFLICT）
- ニュース収集での SSRF・XML Bomb 対策、トラッキングパラメータ除去、記事ID のハッシュ化
- ETL の差分更新（バックフィル）・品質チェック（欠損・スパイク等）
- 監査ログ（signal → order → execution のトレーサビリティ）

---

## 主な機能一覧

- 環境設定管理
  - `.env` ファイルと OS 環境変数から設定を自動読込（必要に応じて自動読込を無効化可）
  - 必須／省略可能な設定をラップした `Settings` インターフェイス

- データ取得・保存（data パッケージ）
  - J-Quants クライアント（株価日足 / 財務 / マーケットカレンダー）
    - レート制御、リトライ、401 時のトークンリフレッシュ、ページネーション対応
  - ニュース収集（RSS）と前処理
    - URL 正規化、トラッキングパラメータ除去、ID は SHA-256 トランケート
    - SSRF / gzip / XML の安全対策
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - ETL パイプライン（差分取得、バックフィル、品質チェックの統合）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログテーブル（signal/order_request/execution）の初期化
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- 基盤（将来的に）
  - strategy, execution, monitoring 各モジュールのプレースホルダ（パッケージとして用意）

---

## 必要条件（推奨）

- Python 3.10+
- ライブラリ（主要）
  - duckdb
  - defusedxml

（実際の requirements.txt／pyproject.toml に依存します。ローカルで管理ファイルがある場合はそちらをご参照ください。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限以下を入れてください:
     - pip install duckdb defusedxml

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（パッケージ import 時に自動ロードされます）。
   - 自動ロードを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する

5. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabuAPI のベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: 通知用 Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: 通知先チャンネルID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 環境（development / paper_trading / live）デフォルトは development
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   注意: Settings のプロパティは未設定の場合 ValueError を投げます（必須項目）。

---

## 使い方（基本例）

以下は Python REPL やスクリプトでの簡単な利用例です。

1) DuckDB スキーマ初期化と接続
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行（株価・財務・カレンダーの差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())  # ETLResult の概要を出力
```

3) ニュース収集ジョブ（RSS 収集と保存）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は記事中の4桁コード抽出に用いる既知コード集合（省略可）
res = run_news_collection(conn, known_codes=set(['7203','6758']))
print(res)  # {source_name: 新規保存数}
```

4) 監査ログ（audit）スキーマ初期化（必要に応じて専用 DB）
```python
from kabusys.data.audit import init_audit_schema, init_audit_db

# 既存 conn に追加したい場合
init_audit_schema(conn)

# 監査専用 DB を別ファイルで作る場合
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

5) カレンダーバッチ更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

注意点：
- J-Quants API へのリクエストはレート制御・リトライが組み込まれていますが、API 使用量には注意してください。
- ETL の差分計算は DB の最終取得日を基に行われます。初回ロード時はデフォルトで 2017-01-01 から取得します。
- ログやエラー内容は設定した LOG_LEVEL に従って出力されます。

---

## よくあるトラブルと対処

- 環境変数が見つからない（ValueError）
  - `.env` の記述やシェルの export を確認してください。自動ロードが働かない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認。

- DuckDB へ接続できない／ファイルが作れない
  - DUCKDB_PATH の親ディレクトリが自動作成されますが、権限問題を確認してください。

- J-Quants API の 401 が頻発する
  - JQUANTS_REFRESH_TOKEN が正しいか、許可・有効期限を確認してください。トークンは自動リフレッシュされる設計です。

- RSS 取得で不正な URL が来る、または外部アクセス拒否
  - news_collector は SSRF 対策として private IP やスキーム不正を拒否します。ソース URL を見直してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なファイル・パッケージ（src/kabusys を起点）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（自動 .env 読込、Settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・トークン管理・レートリミット）
    - news_collector.py
      - RSS 取得、前処理、DuckDB への保存、銘柄紐付け
    - schema.py
      - DuckDB の全スキーマ定義・初期化
    - pipeline.py
      - ETL パイプライン（差分更新・バックフィル・品質チェック統合）
    - calendar_management.py
      - マーケットカレンダーの管理、営業日判定、夜間更新ジョブ
    - audit.py
      - 監査ログ（signal / order_request / executions）の DDL と初期化
    - quality.py
      - データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py (将来的な戦略関連コード)
  - execution/
    - __init__.py (将来的な発注・ブローカー連携)
  - monitoring/
    - __init__.py (将来的な監視・通知機能)

補足：
- コード内には設計ノート（DataPlatform.md 等を参照する想定）がコメントとして埋め込まれています。
- 各モジュールは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取り、トランザクションや例外処理を適切に扱います。

---

## 今後の拡張ポイント（参考）

- strategy モジュールに具体的な戦略実装（特徴量・スコア算出）
- execution モジュールで kabuステーション等への実際の注文送信ロジック
- モニタリング（Slack 通知やメトリクス収集）との統合
- Web UI やダッシュボードで監査ログ・品質レポート表示

---

この README はリポジトリのコードベース（src/kabusys/*）をもとに作成しています。実運用・デプロイ時はセキュリティ（API トークン管理）、監視、バックアップ方針を別途確立してください。質問やサンプルスクリプトの追加が必要であれば教えてください。