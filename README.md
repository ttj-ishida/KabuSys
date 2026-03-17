# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けユーティリティ群です。本リポジトリはデータ収集・ETL、データ品質チェック、マーケットカレンダー管理、ニュース収集、監査ログ（発注/約定のトレーサビリティ）など、戦略・発注層の基盤となる機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

- 目的: J-Quants 等の外部 API から日本株データ（株価日足、四半期財務、マーケットカレンダー等）を安全かつ冪等に取得・保存し、戦略や発注層へ供給する基盤機能を提供します。また、RSS からニュースを収集して銘柄との紐付けを行い、監査ログによりシグナル→発注→約定のトレースを可能にします。
- 設計ポイント:
  - API レート制限の遵守（J-Quants: 120 req/min）とリトライ（指数バックオフ、401 時のトークン自動リフレッシュ対応）
  - データ取得時刻（fetched_at）を UTC で記録し Look-ahead bias を抑制
  - DuckDB を用いた永続化（DDL・インデックス・冪等保存）
  - ニュース収集の SSRF / XML 攻撃対策、トラッキングパラメータ削除、SHA-256 ベースの記事 ID による冪等化
  - 品質チェック（欠損、重複、スパイク、日付不整合）を ETL 後に実行可能

---

## 主な機能一覧

- 環境設定読み込み
  - .env / .env.local / OS 環境変数の読み込み（自動読み込みを無効化可能）
  - 必須設定は Settings クラス経由で取得（JQUANTS_REFRESH_TOKEN など）

- データ取得（kabusys.data.jquants_client）
  - daily quotes（OHLCV）
  - financial statements（四半期 BS/PL）
  - market calendar（JPX）
  - API レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB へ冪等に保存する save_* 関数

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、XML パース（defusedxml）、URL 正規化、トラッキングパラメータ除去
  - 記事 ID を SHA-256（先頭32文字）で作成し raw_news に保存、news_symbols で銘柄紐付け
  - SSRF / Gzip バッファ制限 / コンテンツサイズ制限 等の保護

- スキーマ管理（kabusys.data.schema）
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema() による初期化、接続取得

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日を参照して差分のみ取得）
  - backfill を含む差分更新設計
  - run_daily_etl() によりカレンダー→株価→財務→品質チェックを実行

- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新（バックフィル含む）

- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合（未来日・非営業日のデータ）を検出
  - QualityIssue オブジェクトで結果を返す

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化
  - init_audit_db() で監査専用 DB の初期化（UTC タイムゾーン固定）

- パッケージ分割
  - kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（strategy/execution/monitoring はインターフェース用のサブパッケージ）

---

## 必要条件 / 依存パッケージ

少なくとも以下のパッケージが必要です（バージョンは適宜指定してください）。

- Python 3.10+（型ヒントに Path | None などを使用）
- duckdb
- defusedxml

インストール例（仮）:
```bash
python -m pip install duckdb defusedxml
```

プロジェクトをローカルで開発する場合は setup/pyproject を用意して pip editable install を推奨します。

---

## 環境変数（主なもの）

設定は .env / .env.local（プロジェクトルート）または OS 環境変数で行います。自動読み込みはデフォルトで有効です（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD - kabu ステーション API のパスワード
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID - Slack チャンネル ID

任意／デフォルト:
- KABUSYS_ENV - development / paper_trading / live（デフォルト: development）
- LOG_LEVEL - DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD - 自動 .env ロードを無効化する場合に 1 を設定
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

.env 例（.env.example を作成して参照してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをチェックアウト
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 必要パッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   # requirements.txt が無ければ最小で:
   python -m pip install duckdb defusedxml
   ```

3. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を作成して必須変数を設定するか、OS 環境変数で設定してください。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。

4. DuckDB スキーマ初期化
   - デフォルトパスは `data/kabusys.duckdb`（settings.duckdb_path）
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡単な例）

以下は代表的な用途のサンプルコードです。

- ETL（日次パイプライン）を実行する:
```python
from kabusys.data import schema, pipeline
from datetime import date

# DB 初期化（既に初期化済みならスキップ可）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（省略時 target_date=今日、id_token は内部で取得）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブを実行する:
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コードのセットを渡すと紐付け処理を行う
known_codes = {"7203", "6758", "9984"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ:
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

- 監査 DB 初期化:
```python
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

- 設定取得:
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

メソッド引数（id_token など）を注入できる実装になっているため、テスト時に外部 API 呼び出しをモックしやすくなっています。

---

## 運用上の注意 / 実装詳細のポイント

- jquants_client:
  - レートリミット: 120 req/min を固定間隔スロットリングで守ります。
  - リトライ: 408/429/5xx に対して指数バックオフで最大 3 回リトライ。429 の場合は Retry-After ヘッダを尊重。
  - 401 応答時はリフレッシュトークンから id_token を自動取得して 1 回だけ再試行。
  - ページネーション対応。fetched_at を UTC タイムスタンプで記録。

- news_collector:
  - XML パースは defusedxml を使用して XML Bomb 等の攻撃を防止。
  - レスポンスサイズは MAX_RESPONSE_BYTES（デフォルト 10 MB）で制限。gzip 解凍後も検査。
  - SSRF 対策: リダイレクト先も含めスキーム検査、プライベートアドレスへのアクセスをブロック。
  - 記事 ID は URL 正規化（トラッキング除去）後の SHA-256 先頭 32 文字。

- ETL:
  - 差分処理（DB の最終取得日を参照）＋ backfill（デフォルト 3 日）で API 側の後出し訂正を吸収。
  - 品質チェックは Fail-Fast ではなく問題を収集して呼び出し元が判断する方式。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - news_collector.py           — RSS ニュース収集・DB 保存・銘柄抽出
    - schema.py                   — DuckDB スキーマ定義・初期化
    - pipeline.py                 — ETL パイプライン（差分更新 / 品質チェック）
    - calendar_management.py      — マーケットカレンダー管理・判定ユーティリティ
    - audit.py                    — 監査ログ（signal/order/execution 用テーブル）
    - quality.py                  — データ品質チェック（欠損・スパイク等）
  - strategy/
    - __init__.py                 — 戦略層の置き場（実装はここに追加）
  - execution/
    - __init__.py                 — 発注・ブローカー連携の置き場（実装はここに追加）
  - monitoring/
    - __init__.py                 — 監視・メトリクスの置き場（実装はここに追加）

---

## 貢献 / 拡張案

- strategy / execution / monitoring パッケージに具体的な戦略実装やブローカープラグイン（kabuステーション・他ブローカー）を追加することで、実運用に近いシステムへ拡張可能です。
- テストカバレッジを追加（特にネットワーク周り、RSS 解析、SQL クエリ）し、CI での品質を担保してください。
- モニタリング・アラート（Slack 統合・Prometheus メトリクス）を監視パッケージへ実装することを推奨します。

---

## ライセンス・その他

（この README にはライセンス情報は含まれていません。配布・使用にあたってはプロジェクトの LICENSE を参照してください。）

---

必要に応じて README に追記します。例えば具体的な .env.example のテンプレート、requirements.txt、実行用スクリプトや systemd / cron の起動例などを追加できます。どの情報を優先して追加しますか？