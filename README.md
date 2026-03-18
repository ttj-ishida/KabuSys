# KabuSys

日本株自動売買プラットフォームのコアモジュール群です。データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、DuckDB スキーマおよび監査ログ（発注→約定のトレーサビリティ）を提供します。

---
目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（サンプル）
- 環境変数一覧
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な「データ取得 → ETL → 品質チェック → 戦略／発注」の基盤を実装するライブラリ群です。本コードベースは以下の役割を持つサブモジュールで構成されています。

- データ取得（J-Quants API 経由の日足・財務・マーケットカレンダー取得）
- ニュース（RSS）収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- DuckDB によるスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上の注意点：API レート制限、リトライ（指数バックオフ）、トークン自動リフレッシュ、Idempotent（ON CONFLICT）保存、Look-ahead バイアス回避（fetched_at）などを考慮しています。

---

## 主な機能一覧

- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）・財務（四半期）・マーケットカレンダー取得
  - レートリミット制御（120 req/min）、リトライ・トークン自動リフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS の取得・XML パース（defusedxml を使用）
  - URL 正規化（utm_* 等の除去）、SHA-256 による記事 ID 生成（先頭32文字）
  - SSRF 対策（スキーム検証、リダイレクト先の内部アドレス拒否）
  - 受信サイズ・Gzip 解凍制御、DuckDB へのバルク挿入（トランザクション / INSERT ... RETURNING）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義、init_schema() / get_connection()

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日を利用）、バックフィル日数の指定
  - カレンダー先読み（lookahead）、品質チェック呼び出し
  - run_daily_etl() により一括 ETL 実行（各ステップは独立してエラーハンドリング）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出、スパイク検出、重複検出、日付整合性チェック
  - QualityIssue 型で問題を集約

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルと初期化関数
  - UTC タイムゾーンの固定、冪等キー・ステータス管理

- 設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート判定）
  - 環境変数ラッパー settings（必須変数は _require() による検証）
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子、型ヒントを使用しているため）
- DuckDB を使用（ローカルファイル / :memory:）

推奨依存パッケージ（最低限）
- duckdb
- defusedxml

簡易インストール例（仮に pip で直接インストールする場合）:
```
pip install duckdb defusedxml
```

プロジェクトを開発モードでインストールする場合（pyproject/セットアップがある前提）:
```
pip install -e .
```

環境変数の準備
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config が自動ロード）。
- テストや特殊用途で自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必要な Python ライブラリやバージョンはプロジェクトの pyproject.toml / requirements.txt を参照してください（本コード断片には依存リストが含まれていないため、実環境に合わせて調整してください）。

---

## 環境変数一覧

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が ID トークンを取得するために使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: 動作環境（development / paper_trading / live）。デフォルトは development。
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト INFO。
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視用 SQLite パス（monitoring 用）。デフォルト `data/monitoring.db`

自動読み込みについて:
- `.env`（優先度低）と `.env.local`（優先度高）がプロジェクトルートにあれば自動読み込みされます。
- OS 環境変数がある場合は `.env` の値で上書きされません（`.env.local` は上書き可能）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

.env のパースはシェル風の簡易構文（export を許容、クォートやコメントも考慮）をサポートしています。

---

## 使い方（簡単なサンプル）

以下はライブラリ API を使う最小例です。実運用ではログ設定や例外処理を適切に行ってください。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

# file path は settings.duckdb_path を使うこともできます
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

- ニュース収集を実行（既知銘柄コード集合を渡すと銘柄紐付けも実行）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: 保存件数}
```

- 監査DB（監査専用）を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- J-Quants API から日足を直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

token = settings.jquants_refresh_token  # 必須
records = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 注意点 / 運用メモ

- J-Quants API はレート制限（120 req/min）を本クライアントで制御しています。大量データのループ呼び出しは考慮されていますが、他プロセスとの競合に注意してください。
- fetch 系関数はページネーション対応・トークン自動更新を行いますが、テスト時や特殊フローでは id_token を外部注入できます（引数で指定）。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）にしてあるため再実行耐性があります。
- news_collector は SSRF、XML Bomb、Gzip Bomb などの対策を実装しています。ただし外部の RSS ソースに依存するため、予期しないフォーマットや巨大レスポンスには注意が必要です。
- audit モジュールは UTC を前提とします（init_audit_schema で TimeZone を UTC に固定）。

---

## ディレクトリ構成

主要なファイル/モジュール構成（本コードベース断片に基づく）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得 & 保存）
    - news_collector.py      # RSS ニュース収集・前処理・DB 保存
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py # マーケットカレンダーの判定・更新ジョブ
    - audit.py               # 監査ログ（signal/order/execution）
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py            # 戦略関連モジュール配置想定
  - execution/
    - __init__.py            # 発注実行関連モジュール配置想定
  - monitoring/
    - __init__.py            # 監視・メトリクス関連（未実装の雛形）

---

## ライセンス・貢献

（本 README にはライセンス記載がありません。実プロジェクトでは LICENSE ファイルの追加と貢献ガイドを配置してください。）

---

README のサンプルコードや設定は、提供されたコードベースの抜粋に基づくものです。実際のリポジトリでは pyproject.toml / requirements.txt / .env.example 等を参照して環境を整えてください。必要であれば README の英語版や、より詳細な運用手順（デプロイ、Slack 通知設定、CI/CD 例など）も作成できます。必要な範囲を指示してください。