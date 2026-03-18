# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
このリポジトリはデータ取得・ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログなどを備えた日本株向け自動売買基盤のコアモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は J-Quants API や RSS を用いて市場データ（株価・財務・カレンダー）やニュースを取得し、DuckDB を中心としたデータレイヤーに保存・整備するためのライブラリです。ETL の差分取得、品質チェック、カレンダーの営業日判定、ニュースから銘柄抽出してデータベースに保存する機能、監査ログ（発注 → 約定のトレーサビリティ）などを備え、戦略・実行・モニタリングモジュールと組み合わせて自動売買システムを構築できます。

主な設計方針（抜粋）:
- J-Quants API のレート制限とリトライを考慮した堅牢なクライアント実装
- データの冪等保存（ON CONFLICT を利用）により安全な更新
- Look-ahead Bias 対策として取得時刻（UTC）を記録
- RSS の収集では SSRF 対策、XML の安全パース、サイズ制限などを実装
- DuckDB スキーマは Raw / Processed / Feature / Execution の層で構成

---

## 機能一覧

- 環境設定管理（.env / 環境変数の自動読み込み）
  - 自動ロード順序: OS環境 > .env.local > .env
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- J-Quants クライアント
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - マーケットカレンダー取得
  - トークン自動リフレッシュ、リトライ、レート制御
- DuckDB スキーマ管理
  - init_schema() で必要テーブルとインデックスを作成
  - 監査ログ用の init_audit_schema / init_audit_db を提供
- ETL パイプライン
  - 差分更新（最後に取得した日付を基準に差分取得）
  - backfill による直近再取得で API の訂正を吸収
  - run_daily_etl() による日次バッチ（カレンダー → 価格 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複検出、日付不整合チェック
  - QualityIssue 型で詳細を返す
- ニュース収集（RSS）
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、記事ID の SHA-256 ベース生成
  - SSRF 対策、gzip 制限、XML の安全パース
  - raw_news への冪等保存、news_symbols で銘柄紐付け
- マーケットカレンダー管理
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - calendar_update_job() による差分更新ジョブ
- 監査ログ（オーダー/約定のトレーサビリティ）
  - signal_events, order_requests, executions テーブルなど

---

## 必要条件 / 依存

- Python 3.10 以上（型記法で | を使用）
- 主な Python パッケージ:
  - duckdb
  - defusedxml

（実プロジェクトでは requirements.txt / Poetry で正確な依存管理を行ってください）

---

## セットアップ手順

1. リポジトリをクローンして開発環境に入る
   - 例:
     git clone <repo-url>
     cd <repo-dir>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install duckdb defusedxml

   （パッケージ化されている場合は pip install -e . などでインストール）

4. 環境変数を設定
   - .env または .env.local をプロジェクトルートに作成します。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト値あり
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|...) — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
   - 自動ロード:
     - パッケージをインポートすると、プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。
     - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（概要・サンプル）

以下は代表的な API の使い方例です。実環境ではロギングやエラーハンドリングを併用してください。

1) DuckDB スキーマ初期化

Python から DuckDB のファイルを初期化して接続を取得します。

```python
from kabusys.data.schema import init_schema, get_connection

# ファイルベース DB を作成して全テーブルを初期化
conn = init_schema("data/kabusys.duckdb")

# 既存 DB に接続するだけなら
conn2 = get_connection("data/kabusys.duckdb")
```

2) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 今日分を処理（id_token を省略すると内部キャッシュ / 自動取得を使用）
result = run_daily_etl(conn, target_date=date.today())

# ETL 実行結果の確認
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS ソースから収集して DB 保存、銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes は抽出対象の有効な銘柄コード集合（例: {'7203', '6758', ...}）
known_codes = {"7203", "6758"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # 各ソースごとの新規保存件数
```

4) カレンダー更新ジョブ（夜間バッチ例）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

5) J-Quants クライアントを直接使う（トークン注入可能）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
token = get_id_token()  # settings.jquants_refresh_token を使って id token を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存
from kabusys.data.jquants_client import save_daily_quotes
save_daily_quotes(conn, records)
```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

settings オブジェクトは kabusys.config.settings 経由で参照できます。

---

## ディレクトリ構成

概略:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py         — RSS 収集、URL 正規化、raw_news 保存、銘柄抽出
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - schema.py                 — DuckDB スキーマ定義 / init_schema / get_connection
    - calendar_management.py    — マーケットカレンダー管理、営業日判定、更新ジョブ
    - audit.py                  — 監査ログ（signal_events / order_requests / executions）
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py               — 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py               — 発注/ブローカー連携モジュール（拡張ポイント）
  - monitoring/
    - __init__.py               — 監視・メトリクス関連（拡張ポイント）

各モジュールは拡張を想定して設計されており、strategy / execution / monitoring はプロジェクト固有のロジックを実装して組み合わせてください。

---

## 注意事項 / 運用上のヒント

- DuckDB のファイルは適切にバックアップしてください。init_schema は冪等に振る舞いますがデータ保全は別途必要です。
- J-Quants の API レート制限（120 req/min）に配慮して実行してください。クライアントは固定間隔スロットリングで制御しますが、運用負荷に注意。
- ETL は差分設計ですが、初回は大量データ取得になるため実行時間と API コストに注意してください。
- ニュース収集では外部の RSS を定期取得するため、RSS ソースの運用ポリシーに従ってください。
- 品質チェックは警告・エラーを返します。自動停止するかどうかは上位のオーケストレーションで判断してください。

---

## さらに

- 戦略（strategy）・発注（execution）・監視（monitoring）の具体実装はこのコアライブラリを基に各プロジェクトで実装します。
- 追加のユーティリティ（Slack 通知、メトリクス、Kubernetes CronJob など）を組み合わせると本番運用に必要な運用性が向上します。

---

ライセンス、貢献方法、より詳細な設計ドキュメント（DataPlatform.md など）はリポジトリのルートに別途用意してください。ご不明点があれば、どの部分の利用例・詳細が必要か教えてください。