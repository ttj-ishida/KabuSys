# KabuSys

KabuSys は日本株の自動売買・データ基盤向けライブラリです。J-Quants API などから市場データを取得して DuckDB に格納し、データ品質チェック・監査ログを備えた ETL / データレイヤーを提供します。戦略層や発注実行層との連携を前提に設計されています。

バージョン: 0.1.0

## 特徴 (概要)

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得日時（fetched_at）を UTC で記録し、Look-ahead Bias を防止
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマを定義・初期化
  - 冪等な INSERT（ON CONFLICT DO UPDATE）により重複排除
- ETL パイプライン
  - 差分更新、バックフィル、カレンダー先読み、品質チェックを包含した日次 ETL
  - 各ステップは独立してエラーハンドリング（1ステップ失敗でも他は継続）
- データ品質チェック
  - 欠損データ、スパイク（前日比）、主キー重複、日付不整合（未来日付・非営業日）検出
  - 問題は QualityIssue オブジェクトとして収集（Fail-Fast ではない）
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 まで UUID 連鎖でトレーサビリティを確保
  - order_request_id を冪等キーとして二重発注を防止
- 環境設定管理
  - .env / .env.local または環境変数から設定を自動読み込み
  - パッケージ配布後も動作するようにプロジェクトルート（.git / pyproject.toml）を探索して自動読み込み

## 主な機能一覧

- kabusys.config.Settings: 環境変数からの設定取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存）
- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)
  - Raw / Processed / Feature / Execution テーブルとインデックスを定義
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - ETLResult に結果をまとめて返す
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)（監査用テーブルの初期化）

（strategy、execution、monitoring モジュールは本コードベースでは空のプレースホルダです）

## セットアップ手順

前提:
- Python 3.9+（型ヒントで | 演算子を使用しているため、3.10 以上が望ましい）
- duckdb Python パッケージ

推奨手順:

1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb

   （将来的に requirements.txt を用意する場合はそちらを使用してください）

3. 環境変数を用意する
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を配置すると自動読み込みされます。
   - 自動読み込みを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して起動してください。

推奨 .env に含める主要なキー（例）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi (オプション)
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb (デフォルト)
- SQLITE_PATH=data/monitoring.db (デフォルト)
- KABUSYS_ENV=development | paper_trading | live
- LOG_LEVEL=INFO

注意:
- Settings は必須の環境変数が未設定の場合 ValueError を送出します（例: JQUANTS_REFRESH_TOKEN 等）。

## 使い方（簡易ガイド）

以下は主要な利用パターンの例です。

1) DuckDB スキーマの初期化（初回のみ）

Python スクリプト例:
```
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# 以降この conn を ETL やクエリで使えます
```

2) 日次 ETL の実行（市場カレンダー先読み + 差分更新 + 品質チェック）
```
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 個別ジョブを使う（株価のみ等）
```
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date(2026, 1, 31))
```

4) 監査ログスキーマを追加する
```
from kabusys.data import schema, audit

conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```
または監査専用 DB を初期化:
```
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

5) 直接 J-Quants API を呼ぶ（テスト等）
```
from kabusys.data import jquants_client as jq

# id_token は省略可能（モジュール内キャッシュを使って自動的にリフレッシュ）
daily = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

実運用での注意点:
- API のレート制限（120 req/min）をクライアント側で尊重します（内部でスロットリング）。
- ネットワーク障害や 5xx/429/408 に対し最大 3 回のリトライを行います（指数バックオフ）。
- 401 を受けた場合はリフレッシュトークンで自動再取得を試みます（1回のみ）。
- すべてのタイムスタンプは UTC を想定（fetched_at など）。

## ディレクトリ構成

以下は本リポジトリの主要ファイル / モジュール構成（src/kabusys 配下）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得・保存ロジック）
      - schema.py               # DuckDB スキーマ定義 & 初期化
      - pipeline.py             # ETL パイプライン
      - audit.py                # 監査ログ（トレーサビリティ）スキーマ
      - quality.py              # データ品質チェック
    - strategy/
      - __init__.py             # 戦略層プレースホルダ
    - execution/
      - __init__.py             # 実行層プレースホルダ
    - monitoring/
      - __init__.py             # 監視プレースホルダ

主要テーブル群（schema.py に定義）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 監査ログ: signal_events, order_requests, executions

## 実装上のポイント / 注意事項

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基に行われます。CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して無効化できます。
- ETL は差分更新を基本とし、バックフィル（デフォルト 3 日）を行うことで API の後出し修正を吸収します。
- DuckDB への挿入は ON CONFLICT DO UPDATE を使った冪等性を保証しています。
- 品質チェックは重大度 ("error" / "warning") を付与して検出結果を返します。呼び出し側は結果に基づき処理停止などを判断してください。
- 監査ログは削除しない前提で設計され、すべてのテーブルに created_at を保持します。タイムゾーンは UTC を使用します。

## 今後の拡張案（参考）

- strategy / execution / monitoring の具現化（戦略実行ループ、証券会社 API 連携、アラート）
- Slack 連携による ETL 結果・品質警告の通知（設定は config でトークン・チャンネルを持つ）
- テスト用の fixtures / CI ワークフロー
- requirements.txt / setup.py / pyproject.toml によるパッケージ管理・配布

---

問題や追加したいドキュメント（API サンプル、DataSchema.md、DataPlatform.md への参照）があれば知らせてください。README を要件に合わせて拡張できます。