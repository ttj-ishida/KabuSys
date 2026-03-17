# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ用 README

概要、機能、セットアップ、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびそのデータ基盤を構成する Python モジュール群です。  
主に以下を目的としています。

- J-Quants API からの市場データ（株価日足、四半期財務、マーケットカレンダー）取得
- RSS からのニュース収集と銘柄紐付け
- DuckDB ベースのデータスキーマ定義・初期化
- ETL（差分取得、保存、品質チェック）のパイプライン
- マーケットカレンダーの管理ユーティリティ
- 監査ログ（シグナル→発注→約定を辿るトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合等）

設計上の特徴：
- API レート制限やリトライ、トークン自動リフレッシュに対応
- DuckDB へ冪等に保存（ON CONFLICT を利用）
- セキュリティ対策（RSS収集時の SSRF 対策・XML パースの安全化 等）
- テストしやすい設計（id_token 注入やモック可能な内部関数）

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local を自動読み込み（PROJECT_ROOT 判定）、必要変数の検証
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込み無効化
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL 設定

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（fetch_daily_quotes）
  - 財務データ（fetch_financial_statements）
  - 市場カレンダー（fetch_market_calendar）
  - API レート制御、リトライ、トークン自動リフレッシュ
  - DuckDB への保存関数（save_*）は冪等

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理（URL除去、空白正規化）
  - URL 正規化・記事ID を SHA-256 から生成（冪等）
  - defusedxml による安全な XML パース、SSRF 対策、受信上限バイト数制限
  - raw_news / news_symbols への一括保存（トランザクション・チャンク分割）

- データスキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) による DuckDB 初期化（冪等）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日を参照して未取得分のみ取得）
  - backfill による直近再取得（API の後出し修正吸収）
  - run_daily_etl による一括 ETL（カレンダー→株価→財務→品質チェック）

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日取得、期間の営業日リスト
  - calendar_update_job による夜間差分更新

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査用テーブル群
  - init_audit_schema / init_audit_db による初期化（UTC タイムゾーン固定）

- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - run_all_checks によるまとめ実行（QualityIssue を返す）

---

## セットアップ手順

以下は一般的なローカル開発用セットアップ手順です。実際の依存関係はプロジェクトの packaging / requirements に合わせてください。

1. Python 環境を用意
   - 推奨: Python 3.10+

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - duckdb, defusedxml などが必要です。
   - 例:
     pip install duckdb defusedxml

   （実際は requirements.txt や pyproject.toml に合わせてインストールしてください）

4. 環境変数の設定
   - プロジェクトルートに .env ファイルを配置すると自動読み込みされます（.env.local は上書き）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN : Slack 通知に使用する Bot トークン（必須）
     - SLACK_CHANNEL_ID : 通知先チャンネル ID（必須）
   - その他:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 に設定すると自動 .env ロードを無効化
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 sqlite パス（デフォルト data/monitoring.db）

5. データベース初期化
   - DuckDB スキーマを初期化します（例: デフォルト DUCKDB_PATH を使用）
   - Python 例:
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)

6. 監査ログ DB 初期化（任意）
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

---

## 使い方（基本的な例）

以降は Python スクリプトからの呼び出し例です。

- 環境設定・DB 初期化

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path オブジェクト（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())       # ETLResult として詳細が得られる
```

- 市場カレンダーの夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- RSS ニュース収集（既知銘柄コードのセットを渡して紐付け）

```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9432"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # ソース名 -> 新規保存数
```

- J-Quants から直接データを取得して保存（テストやバックフィル時）

```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# id_token を外部で取得して注入することも可能
id_token = jq.get_id_token()  # もしくは settings.jquants_refresh_token に基づき取得
records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェックの直接実行

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点：
- jquants_client は API レート（120 req/min）やリトライを内部で管理しますが、長時間・大量取得時は注意してください。
- news_collector は SSRF・XML Bomb 等の対策が組み込まれています。テスト時は _urlopen をモックすることができます。
- 多くの関数は外部トークンや DB 接続を引数で注入可能で、テスト容易性を配慮しています。

---

## ディレクトリ構成

主要なファイル・モジュール構成は以下のとおりです（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                     - 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（取得＋保存）
    - news_collector.py            - RSS ニュース収集・保存・銘柄抽出
    - schema.py                    - DuckDB スキーマ定義と初期化
    - pipeline.py                  - ETL パイプライン（差分取得 → 保存 → 品質チェック）
    - calendar_management.py       - マーケットカレンダー管理・営業日判定
    - audit.py                     - 監査ログ（signal/order/execution）初期化
    - quality.py                   - データ品質チェック
  - strategy/
    - __init__.py                  - 戦略関連モジュール（拡張想定）
  - execution/
    - __init__.py                  - 発注/ブローカー関連（拡張想定）
  - monitoring/
    - __init__.py                  - 監視・メトリクス用（拡張想定）

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（SQLite）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

.env.example を参考に .env を作成してください。

---

## 運用上の注意・設計上のポイント

- ETL は差分取得・冪等保存を前提としています。ON CONFLICT による更新で二重挿入を回避します。
- J-Quants API 呼び出しはレート制御（120 req/min）、リトライ（指数バックオフ、特定ステータスでリトライ）を備えています。
- news_collector では URL 正規化（トラッキングパラメータ除去）→ SHA-256 の先頭 32 文字を記事 ID に利用して冪等性を保証します。
- カレンダーが未取得のときは曜日ベースのフォールバック（平日を営業日とみなす）を行います。カレンダー取得後は DB の値を優先します。
- 監査ログは削除しない前提で設計され、すべて UTC で TIMESTAMP を扱います。

---

必要であれば、README に以下を追加できます：
- CI / テスト実行方法
- 具体的な .env.example のサンプル
- Docker / コンテナでの実行手順
- 詳細な API 使用例や CLI（存在する場合）の説明

追加の要望があれば教えてください。