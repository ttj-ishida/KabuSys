# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J-Quants や kabuステーション 等からマーケットデータを取得し、DuckDB に保存・管理するための ETL、データ品質チェック、監査ログスキーマなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的で設計された小規模なライブラリ群です。

- J-Quants API から株価日足・財務データ・市場カレンダーを取得するクライアント
- DuckDB を用いたデータスキーマ定義・初期化
- 日次の差分 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ

設計方針のハイライト:
- J-Quants のレート制限（120 req/min）を守る RateLimiter を内蔵
- リトライ（指数バックオフ）、401 時のトークン自動リフレッシュを実装
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装
- 品質チェックは Fail-Fast しない（問題をすべて収集）

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API からの日足・財務データ・マーケットカレンダー取得
  - レート制御・リトライ・トークン自動更新
  - DuckDB へ idempotent に保存する save_* 関数
- data/schema.py
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ定義と初期化
  - インデックス定義、init_schema / get_connection 提供
- data/pipeline.py
  - 日次 ETL パイプライン（run_daily_etl）
  - 差分取得ロジック、バックフィル、品質チェック呼び出し
- data/quality.py
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue データクラスで問題を返す
- data/audit.py
  - 監査ログ用テーブル（signal_events / order_requests / executions）と初期化関数
- config.py
  - .env / 環境変数の読み込みロジック（プロジェクトルート自動検出）
  - 必須環境変数のラッパ（settings オブジェクト）
  - 自動 .env ロードの無効化フラグ有り

---

## 要件

- Python 3.10 以上（型ヒントに `|` 演算子を使用）
- 依存パッケージ:
  - duckdb

インストール例:
- pip:
  - pip install duckdb

（現状、外部 HTTP は urllib を使用しているため追加の HTTP ライブラリは不要です）

---

## セットアップ手順

1. リポジトリをクローン / 配布ファイルを配置

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb

4. 環境変数を設定
   - プロジェクトルートに `.env`（必要なら `.env.local`）を配置すると自動で読み込まれます。
   - 自動ロードは、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数としてセットすると無効化されます（テスト用途など）。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API パスワード
- SLACK_BOT_TOKEN : Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

その他（任意 / デフォルトあり）
- KABU_API_BASE_URL : kabu API のベース URL （デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境 ("development" | "paper_trading" | "live")。デフォルト: development
- LOG_LEVEL : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"。デフォルト: INFO

例: .env の最小例
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

※リポジトリルートは .git または pyproject.toml を基準に自動検出されます。

---

## 使い方（簡単な例）

以下はインタラクティブまたはスクリプトでの基本的な使い方例です。

1. DuckDB スキーマ初期化（ファイルベース）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path には .env の DUCKDB_PATH が反映される
conn = init_schema(settings.duckdb_path)
```

2. 監査ログスキーマの初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

3. 日次 ETL の実行（デフォルトは今日）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

run_daily_etl のポイント:
- 市場カレンダー → 株価 → 財務 の順に差分取得・保存を行う
- デフォルトでバックフィル days = 3（最終取得日の過去数日を再取得）
- 品質チェック（quality.run_all_checks）を標準で実行し、QualityIssue のリストを返す

4. J-Quants の個別データ取得
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を用いて取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

5. DuckDB に保存（jquants_client の save_* を利用）
```python
from kabusys.data.jquants_client import save_daily_quotes

n_saved = save_daily_quotes(conn, quotes)
```

品質チェックの実行（個別）
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 注意点 / 実装上の挙動

- 自動 .env 読み込み
  - ローカル環境変数 > .env.local > .env の順でマージされます。
  - プロジェクトルートの特定は .git または pyproject.toml を基準とするため、カレントワーキングディレクトリに依存しません。
  - テスト等で自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

- J-Quants クライアント
  - レート制限 120 req/min に対して固定間隔スロットリングを実行
  - 408/429/5xx 系へのリトライ（最大 3 回、指数バックオフ）
  - 401 受信時はリフレッシュトークンで id_token を再取得して 1 回リトライ

- DuckDB 保存
  - raw テーブルへの挿入は ON CONFLICT DO UPDATE を利用して冪等性を確保しています
  - init_schema は存在するテーブルをスキップするため安全に何度でも呼べます

- 品質チェック
  - 各チェックは問題を全て収集して返す（Fail-Fast ではない）
  - 重大度 ("error"/"warning") に応じて呼び出し元で処理を決定してください

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル／ディレクトリ構成の抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + 保存）
    - schema.py              — DuckDB スキーマ定義と初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ（signal / order / execution）
  - strategy/
    - __init__.py
    — （戦略用モジュールは今後拡張予定）
  - execution/
    - __init__.py
    — （発注・ブローカー連携用モジュールは今後拡張予定）
  - monitoring/
    - __init__.py
    — （監視・メトリクス用モジュールは今後拡張予定）

---

## 今後の拡張案（参考）

- kabu API と実際の発注フロー実装（execution 層）
- Slack 通知や監視ダッシュボード連携（monitoring）
- 戦略モジュール群（strategy）とバックテスト基盤の追加
- CI 用のインメモリ DB テストスイート

---

## ライセンス / 貢献

（この README にはライセンス情報は含まれていません。実際のプロジェクトでは LICENSE ファイルを追加してください。）

貢献や Issue、PR は歓迎します。テストしやすい形で小さな変更から始めてください。

---

この README はコードベースの現状に基づいて作成しています。実際の運用時は .env.example、LICENSE、CHANGELOG 等の整備と、運用手順（cron / Airflow / GitHub Actions などでの ETL スケジューリング）の追加を推奨します。