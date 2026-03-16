# KabuSys

日本株自動売買プラットフォーム用の共通ライブラリ群。データ取得・永続化・品質チェック・監査ログ定義など、取引システムの基盤となる機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けの内部ライブラリセットです。主に以下を目的としています。

- 外部データソース（例: J-Quants API）からのデータ取得と DuckDB への永続化
- DuckDB におけるデータスキーマ定義（Raw / Processed / Feature / Execution レイヤ）
- 監査ログ（シグナル→発注→約定のトレース）用テーブル定義
- データ品質チェック（欠損・異常値・重複・日付整合性）
- 環境変数・設定の集中管理

設計上のポイントとして、API のレート制限遵守、リトライ・トークンリフレッシュ、UTC タイムスタンプによるトレーサビリティ、冪等性（ON CONFLICT）などを考慮しています。

---

## 主な機能一覧

- config
  - .env / 環境変数の自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）
  - 必須キー取得ヘルパー、環境判定（development / paper_trading / live）とログレベル検証
- data.jquants_client
  - J-Quants API クライアント（株価日足・財務データ・マーケットカレンダー）
  - レート制御（120 req/min 固定間隔スロットリング）
  - 再試行（指数バックオフ、対象ステータス: 408/429/5xx）と 401 時のトークン自動リフレッシュ
  - 取得データの DuckDB への保存ユーティリティ（冪等）
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) による初期化（冪等）
- data.audit
  - 監査用テーブル（signal_events / order_requests / executions）とインデックス
  - init_audit_schema / init_audit_db による初期化
- data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - run_all_checks による一括チェックと QualityIssue レポート
- strategy / execution / monitoring
  - パッケージプレースホルダ（プロジェクト固有の戦略・発注・監視ロジックを配置）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の X | Y 構文やその他機能を利用）
- duckdb を使用（DuckDB Python バインディング）

1. リポジトリをクローン
   git clone <repo-url>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb

   （プロジェクト配布時に requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数設定
   プロジェクトルートに `.env`（および必要に応じて `.env.local`）を配置します。config モジュールはプロジェクトルートを .git または pyproject.toml から検出して自動読み込みします。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（Settings により取得／検証されます）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu ステーション API パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID

   任意／デフォルト:
   - KABUSYS_ENV           : development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
   - KABU_API_BASE_URL     : デフォルトは http://localhost:18080/kabusapi
   - DUCKDB_PATH           : デフォルト data/kabusys.duckdb
   - SQLITE_PATH           : デフォルト data/monitoring.db

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単なコード例）

以下は主要ユースケースのサンプルです。プロジェクト内で直接 Python スクリプト / モジュールから呼び出して利用します。

1) DuckDB スキーマ初期化
```
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) J-Quants から日足を取得して保存
```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

ポイント:
- fetch_ 系関数はページネーション対応。認証トークンは内部でキャッシュ・自動リフレッシュされます。
- API 呼び出しは固定間隔レートリミッタ（120 req/min）とリトライロジックを持ちます。

3) 監査テーブルの初期化（既存 conn に追加）
```
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

または監査専用 DB を作る:
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

4) データ品質チェック
```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print(row)
```

品質チェックはすべての問題を収集して返します。呼び出し側で重大度に応じて ETL 停止やアラート発行を行ってください。

---

## 設計に関する注意点

- 時間: すべての TIMESTAMP は UTC で扱う設計（監査テーブルは init_audit_schema で TimeZone='UTC' をセット）。
- 冪等性: データ保存関数は ON CONFLICT DO UPDATE を使って重複挿入を防止。
- レート制御: J-Quants は 120 req/min を想定。内部で固定間隔スロットリングを実装。
- リトライ: ネットワークエラーや 408/429/5xx に対する指数バックオフを実装。401 受信時はリフレッシュトークンで 1 回のみリトライ。
- .env 自動読み込み: プロジェクトルートを .git または pyproject.toml で探索し、そのディレクトリの `.env` / `.env.local` を順にロードします（OS 環境変数が優先され、`.env.local` は上書き）。テスト時などに無効化可能。

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境設定のロード / Settings クラス
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - schema.py                  — DuckDB スキーマ定義 / init_schema / get_connection
    - audit.py                   — 監査ログ（signal_events / order_requests / executions）
    - quality.py                 — データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - strategy/
    - __init__.py                — 戦略ロジックを配置するパッケージ（プレースホルダ）
  - execution/
    - __init__.py                — 発注実行ロジックを配置するパッケージ（プレースホルダ）
  - monitoring/
    - __init__.py                — 監視・アラートロジックを配置するパッケージ（プレースホルダ）

---

## 今後の拡張案（参考）

- strategy / execution / monitoring パッケージに具体的な戦略・ブローカー連携・通知機能を実装
- 単体テスト・統合テスト、CI 設定（自動で .env テスト用設定を読み替える等）
- metrics / Prometheus Exporter など運用監視用のエンドポイント追加
- マルチスレッド／マルチプロセスでのレート制御の強化（分散実行対応）

---

## ライセンス / 貢献

（ここにライセンス情報や貢献ガイドラインを追記してください）

---

質問や追加してほしい案内（例: サンプル ETL スクリプト、DB スキーマ図、.env.example のテンプレート）などがあれば教えてください。README を用途に合わせて調整します。