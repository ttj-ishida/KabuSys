# KabuSys

日本株自動売買システムのコアライブラリ（データ取得・ETL・スキーマ・品質チェック・監査ログなど）

このリポジトリは、J-Quants API から市場データを取得して DuckDB に保存・管理し、戦略層／実行層で利用可能なデータ基盤を提供します。発注監査ログやデータ品質検査も組み込まれており、運用・検証に適した設計になっています。

バージョン: 0.1.0

---

## 主要な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）を考慮した固定間隔スロットリング
  - 再試行（指数バックオフ、最大 3 回）、HTTP 401 の自動リフレッシュ（1回）
  - フェッチ時刻（UTC）を記録して look-ahead bias を防止
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution 層に分けたテーブル設計
  - インデックスや制約を定義し、検索性能・整合性を確保
  - 監査ログ用スキーマ（signal / order_request / execution）を別途初期化可能

- ETL パイプライン
  - 差分取得（最終取得日からの差分）・バックフィル対応
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 各ステップは独立してハンドリング → 一部失敗しても全体処理は継続

- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複、将来日付・非営業日データを検出
  - QualityIssue 型で問題を収集し、呼び出し元が重大度に応じて対処可能

- 監査 & トレーサビリティ
  - 戦略→シグナル→発注要求→約定 の UUID 連鎖で完全トレーサビリティ
  - 発注要求は冪等キー（order_request_id）をサポート

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法などを使用）
- 必要な Python パッケージ（例）
  - duckdb
  - （ネットワーク呼び出しのため標準ライブラリ urllib を使用しています）
- J-Quants API のアクセストークン等の設定（環境変数）

実際の運用では、kabu ステーションや Slack 連携などの外部アクセスポイントに応じたライブラリやクライアントが必要になります。

---

## 環境変数（主要なもの）

以下はコード内で参照される主要な環境変数です。`.env.example` を参考に `.env` を作成してください（本リポジトリには .env.example がある想定のメッセージがあります）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意・デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env ロードの挙動:
- パッケージ初期化時に、プロジェクトルート（.git または pyproject.toml を基準）から
  1. `.env`（上書きしない）
  2. `.env.local`（上書き）
  を順に読み出します。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ...; cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb
   - （実運用で必要なパッケージは別途追加）

4. 環境変数を準備
   - プロジェクトルートに `.env` を作成して必要な値を設定
   - 例: JQUANTS_REFRESH_TOKEN=xxx
   - 自動読み込みはデフォルトで有効

5. DuckDB スキーマ初期化（次節の使用例を参照）

---

## 使い方（簡易ガイド）

以下は主要な利用例です。Python REPL やスクリプトから利用できます。

- DuckDB スキーマを初期化して接続を取得する
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env 等で指定可能（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 監査ログテーブルを既存の接続に追加する
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- J-Quants のトークン取得・データ取得（クライアント直接利用）
```python
from kabusys.data import jquants_client as jq

# id_token を明示的に取得する
id_tok = jq.get_id_token()

# 日足を取得（ページネーション対応）
records = jq.fetch_daily_quotes(id_token=id_tok, date_from=date(2023,1,1), date_to=date(2023,12,31))

# DuckDB に保存（保存は冪等）
saved = jq.save_daily_quotes(conn, records)
```

- 日次 ETL の実行（推奨: スケジューラや Cron から起動）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ本日（ただしカレンダーで営業日に調整）
print(result.to_dict())
```

- 品質チェックだけを実行する
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # target_date=None で全件チェック
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

ログ出力や Slack 通知などは、プロジェクトの上位モジュール（monitoring / execution / strategy）から組み合わせて実装します。

---

## API の設計ポイント（実装上の振る舞い）

- J-Quants クライアント
  - レート制限: 120 req/min に合わせ最小間隔を挟む（_RateLimiter）
  - リトライ: 最大 3 回、408/429/5xx 等を対象に指数バックオフ。429 の場合は Retry-After を優先
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を再取得して 1 回リトライ
  - ページネーション: pagination_key を追跡して全ページ取得
  - 取得時刻は UTC で fetched_at に保存し、Look-ahead 防止を支援

- ETL（data.pipeline）
  - 差分更新を基本とし、最終取得日から backfill（日数指定：デフォルト 3 日）して後出し修正を吸収
  - 市場カレンダーを先に取得（デフォルトで先読み 90 日）して、ターゲット日を営業日に調整
  - 各処理は例外を捕捉して他の処理を継続。最終結果は ETLResult に集約

- データ品質（data.quality）
  - チェックは失敗を集約して返す（Fail-Fast ではない）
  - SQL を用いて DuckDB 上で効率的に検査
  - QualityIssue オブジェクトに検出サンプル（最大 10 件）を含める

- スキーマ（data.schema / data.audit）
  - 制約・PRIMARY KEY・CHECK を多数定義してデータ整合性を担保
  - 監査テーブルは削除しない前提（ON DELETE RESTRICT 等）
  - 監査側の timestamp は UTC を前提に運用

---

## ディレクトリ構成

主要なファイル・モジュール構成（抜粋）
```
src/
  kabusys/
    __init__.py               # パッケージのエクスポート（version 等）
    config.py                 # 環境変数・設定読み込みロジック
    data/
      __init__.py
      jquants_client.py       # J-Quants API クライアント（取得/保存ロジック）
      schema.py               # DuckDB スキーマ定義と init/get_connection
      pipeline.py             # ETL パイプライン（run_daily_etl 等）
      audit.py                # 監査ログスキーマの定義・初期化
      quality.py              # データ品質チェック
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

---

## 開発・運用における注意点

- 環境変数やシークレットは `.env` または運用環境のセキュアな方法で管理してください。
- DuckDB ファイルは単一ファイル DB なのでバックアップ・バージョン管理を検討してください。
- J-Quants のレート制限・API 仕様変更に注意し、必要に応じて _MIN_INTERVAL_SEC やリトライ方針を調整してください。
- ETL のスケジューリングは、本日分を定時で取得する形（営業日判定を含む）が一般的です。paper_trading/live 環境フラグを用いて発注ロジックを切り替えてください（settings.is_live 等）。

---

## 参考 / よく使う関数・クラス

- settings（kabusys.config.Settings）
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id / duckdb_path / env / log_level / is_live / is_paper / is_dev

- jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records) / save_financial_statements(...) / save_market_calendar(...)

- data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path)

- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- data.audit
  - init_audit_schema(conn) / init_audit_db(db_path)

---

必要であれば、この README をベースにサンプルスクリプト（ETL 実行スクリプト、初期化スクリプト、監視スクリプト）や、`.env.example`、requirements.txt を追加することを推奨します。必要ならそれらのサンプルも作成します。