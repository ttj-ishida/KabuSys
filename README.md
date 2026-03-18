# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J-Quants や kabuステーション などの外部 API から市場データ・財務データ・ニュースを取得して DuckDB に保存し、ETL、品質チェック、マーケットカレンダー管理、監査ログなどを提供します。

> パッケージ名: kabusys  
> バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を備えたデータ基盤＆自動売買補助ライブラリです。

- J-Quants API から株価（OHLCV）・財務データ・マーケットカレンダーを安全に取得
- RSS からニュースを収集して記事と銘柄紐付けを保存
- DuckDB ベースのスキーマ定義と初期化
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev/trading days）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 各種安全対策（API レート制御、リトライ、トークン自動更新、SSRF 対策、XML インジェクション対策）

設計方針として「冪等性」「トレーサビリティ」「外部攻撃（SSRF/XML Bomb など）対策」「品質チェックの可視化」を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - RateLimiter（120 req/min）、指数バックオフ、401 の場合はリフレッシュ（1 回）
  - DuckDB へ idempotent に保存する save_* 関数（ON CONFLICT を使用）
  - fetched_at に UTC タイムスタンプを記録（Look-ahead bias 対策）
- data.news_collector
  - RSS 取得・前処理（URL 除去・空白正規化）
  - defusedxml を用いた XML パース、安全なリダイレクト検査（SSRF 緩和）
  - レスポンスサイズ上限（デフォルト 10MB）や gzip 解凍後の検査
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - raw_news / news_symbols への冪等保存（トランザクション・チャンク挿入）
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema() によりファイル生成・テーブル作成（冪等）
- data.pipeline
  - 日次 ETL（market calendar → prices → financials → 品質チェック）
  - 差分更新 / backfill 機能、品質チェック統合
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job: 夜間バッチで JPX カレンダーを差分更新
- data.quality
  - 欠損、スパイク（前日比）、重複、日付不整合の検出。QualityIssue を返す
- data.audit
  - signal_events / order_requests / executions テーブルでトレーサビリティ確保
  - init_audit_schema / init_audit_db 提供

- config
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - Settings クラス経由で環境変数を型的に参照
  - 自動読み込み無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

前提
- Python 3.10 以上（コード内で PEP 604 の型記法（A | B）を使用しています）
- DuckDB と defusedxml などのライブラリが必要です

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / setup.cfg 等があれば）
   - pip install -e .

3. 環境変数設定
   - プロジェクトルートに `.env` や `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化可能）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. スキーマ初期化
   - Python から init_schema を呼び出して DuckDB を準備します（下記 使用例 参照）。

---

## 使い方（簡単な例）

以下は主要な操作のサンプルです。実行前に必須環境変数を設定してください。

- DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # data/ を自動作成
```

- 日次 ETL の実行
```
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn)  # デフォルト: 今日を対象に ETL を実行
print(res.to_dict())
```

- 市場カレンダーの夜間更新ジョブ
```
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved:", saved)
```

- ニュース収集ジョブ（known_codes を渡すと銘柄抽出を行う）
```
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758"}  # 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- J-Quants の生 API 呼び出し例
```
from kabusys.data.jquants_client import fetch_daily_quotes

quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
```

- 監査ログ用 DB 初期化
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- 設定参照
```
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path  # pathlib.Path
```

注意点
- jquants_client は内部でレート制御と再試行を行います。大量の連続リクエストを投げる場合は間隔を考慮してください。
- fetch_* 系 API はページネーション対応です。id_token は自動キャッシュ・リフレッシュされます。
- news_collector は SSRF や XML 攻撃への対策が実装されていますが、外部 URL 取得のためネットワークポリシーに注意してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル構成（src ディレクトリ基準）:

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得/保存/再試行/レート制御）
    - news_collector.py     — RSS ニュース収集・前処理・DB 保存（SSRF/サイズ制限）
    - schema.py             — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py           — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py— 市場カレンダー管理（営業日判定、update job）
    - audit.py              — 監査ログ（signal→order→execution トレーサビリティ）
    - quality.py            — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py           — 戦略モジュールのエントリ（拡張想定）
  - execution/
    - __init__.py           — 発注実行関連（拡張想定）
  - monitoring/
    - __init__.py           — 監視用（拡張想定）

その他:
- .env, .env.local (任意) — 起動時に自動ロード（プロジェクトルートを .git または pyproject.toml から検出）
- data/ — デフォルトの DuckDB 等の保存先（存在しなければ自動作成）

---

## 実装上の注意 / 設計のポイント

- 冪等性: データベース保存は ON CONFLICT を使って同一キーの重複を防ぎます。ETL を複数回安全に実行できます。
- トレーサビリティ: audit モジュールによりシグナルから約定までの追跡が可能です（UUID 系列で管理）。
- レート制御・再試行: J-Quants API は 120 req/min 制限を想定しており、固定間隔スロットリングと指数バックオフを組み合わせています。401 を検出したら refresh token で id_token を再取得して 1 回リトライします。
- セキュリティ: NewsCollector は defusedxml、SSRF 回避のためのリダイレクト検査、受信サイズ制限、HTTP スキーム検証を実施しています。
- 品質管理: quality モジュールでデータの欠損やスパイク等を検出し、ETL 実行結果に品質問題を含めて返します。重大度（error/warning）に応じて呼び出し元で処理を決めてください。

---

## よくある操作例（コマンドラインでの一連処理）

簡易的な daily job の流れ:
1. 仮想環境を有効化、環境変数を設定
2. Python スクリプトで:
   - init_schema() で DB を初期化
   - run_daily_etl() を呼ぶ
   - 必要なら calendar_update_job() を cron/スケジューラで夜間実行

---

## 付記

- 本 README はソースコードのコメント・ docstring に基づいて生成しています。実際の運用では API トークンやパスワードの管理、ネットワークアクセス権限、証券会社 API の仕様（kabu API）に従った追加実装が必要です。
- 追加の機能（戦略実行、注文送信、Slack 通知など）は strategy/ execution/ monitoring 配下で拡張する想定です。

ご不明点や README に追記したい利用シナリオがあれば教えてください。README を具体的なセットアップ手順（CI/CD、systemd サービス、cron など）向けに拡張できます。