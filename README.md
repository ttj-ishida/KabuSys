# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ取得・ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注／約定トレーサビリティ）など、自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴（ハイライト）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX カレンダーを取得
  - API レート制御（120 req/min）、指数バックオフリトライ、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を抑制
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層を定義するスキーマ
  - 初期化用 API（init_schema / get_connection）

- ETL パイプライン
  - 差分取得（最終取得日からの差分 + バックフィル）で効率的にデータ更新
  - 日次 ETL エントリ（run_daily_etl）でカレンダー → 株価 → 財務 → 品質チェックを実行

- ニュース収集（RSS）
  - RSS 取得・XML パース（defusedxml）による安全なパース
  - URL 正規化・追跡パラメータ除去、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP排除、リダイレクト検査）
  - DuckDB への冪等保存と銘柄コード紐付け

- マーケットカレンダー管理
  - 営業日判定 / 前後営業日検索 / 期間内営業日 などのユーティリティ
  - カレンダーの夜間差分更新ジョブ

- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティを保存する監査テーブル群
  - 発注の冪等キー、UTC タイムスタンプ設定等の設計

- データ品質チェック
  - 欠損、重複、前日比スパイク、将来日付／非営業日の検出
  - QualityIssue 型で検出結果を集約（警告/エラー判定）

---

## 必要要件

- Python 3.10 以上を想定（typing | None union 表記など使用）
- 必要な主要パッケージ（例）
  - duckdb
  - defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ

1. リポジトリをチェックアウト／コピー
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト配布用に pyproject.toml / requirements.txt がある場合はそちらを使用）

4. パッケージのインストール（開発モード）
   - pip install -e .

5. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および使う場合は `.env.local`）を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。
   - 必須（少なくともこれらを設定する）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: Settings API は .env.example を参照する旨のメッセージを出します。自動読み込みはプロジェクトルート (.git または pyproject.toml を基準) を検出して行います。

---

## 使い方（基本例）

以下はライブラリを使った典型的なワークフローの例です。

- DuckDB スキーマ初期化（ファイル DB）
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
```

- インメモリ DB（テスト用）
```python
conn = schema.init_schema(":memory:")
```

- 日次 ETL を実行する
```python
from kabusys.data import pipeline

result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- 個別 ETL ジョブ（価格・財務・カレンダー）
```python
from datetime import date
from kabusys.data import pipeline

# 価格差分ETL
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

# 財務差分ETL
fetched_f, saved_f = pipeline.run_financials_etl(conn, target_date=date.today())

# カレンダーETL
fetched_c, saved_c = pipeline.run_calendar_etl(conn, target_date=date.today())
```

- ニュース収集ジョブ
```python
from kabusys.data import news_collector

# known_codes は既知銘柄コードのセット（例: {"7203", "6758", ...}）
results = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: 新規保存数, ...}
```

- 監査ログ（別DBに監査スキーマを初期化）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して監査関連の書き込み操作を行う
```

---

## 主要モジュールと API（抜粋）

- kabusys.config
  - settings: 環境変数ラッパー（各種必須キーの取得・検証）
  - 自動 .env ロード（プロジェクトルート検出）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## 実運用向けの注意点

- J-Quants のレート制限（120 req/min）を遵守する設計が入っていますが、運用時にも注意して下さい。大量の並列処理を行う際はさらに制御が必要です。
- 秘密情報（API トークン等）は .env ファイルや環境変数で安全に管理してください。`.env` をリポジトリに含めないでください。
- DuckDB ファイルはディスク上に保存されるため、バックアップやローテーション設計を行ってください。
- run_daily_etl は品質チェックで検出した問題を戻しますが、問題の対応（停止・通知など）は呼び出し側で判断してください（Fail-Fast にはしていません）。
- NewsCollector は外部 URL を取得するため、ネットワークアクセスのセキュリティポリシー（プロキシ、VPC 内ルーティング等）に注意してください。SSRF 対策は組み込まれていますが、運用環境に合わせた設定を推奨します。

---

## ディレクトリ構成

（ソースルートは `src/kabusys` です。主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py                 -- パッケージ情報（version）
    - config.py                   -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py         -- J-Quants API クライアント（取得・保存ロジック）
      - news_collector.py         -- RSS ニュース収集・保存
      - schema.py                 -- DuckDB スキーマ定義・初期化
      - pipeline.py               -- ETL パイプライン（差分取得／日次バッチ）
      - calendar_management.py    -- マーケットカレンダー管理
      - audit.py                  -- 監査ログ（発注／約定トレーサ）
      - quality.py                -- データ品質チェック
    - strategy/
      - __init__.py               -- 戦略関連（将来的な拡張ポイント）
    - execution/
      - __init__.py               -- 発注／証券会社連携（将来的な拡張ポイント）
    - monitoring/
      - __init__.py               -- 監視関連（将来的な拡張ポイント）

---

## 開発・拡張ポイント

- strategy / execution / monitoring パッケージは骨格のみです。ここにバックテスト・実運用戦略・ブローカー連携を実装します。
- 監査ログには注文の冪等キーや状態遷移を記録する設計が組み込まれているため、外部ブローカーAPIのコールと密に連携できます。
- ニュースの銘柄抽出は単純な正規表現（4桁）で行っています。精度を高めるには NLP / 辞書ベースのエンリッチメントを検討してください。
- 品質チェックは SQL ベースで効率よく実行できます。新しいチェックの追加も容易です。

---

README の補足・改善要望があれば教えてください。使用例や運用フロー（cron / Airflow などでの定期実行例）も必要であれば追加します。