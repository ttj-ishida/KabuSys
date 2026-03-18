# KabuSys

日本株向けの自動売買／データ基盤用ライブラリ群です。  
J-Quants API や RSS フィードからマーケットデータ・ニュースを収集し、DuckDB を用いて冪等に保存・品質チェック・カレンダー管理・監査ログを行うためのモジュール群を含みます。

---

## 主要機能（抜粋）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）スロットリング
  - リトライ（指数バックオフ、最大 3 回。408/429/5xx 対象）
  - 401 受信時にリフレッシュトークンで自動トークン再取得（1 回）
  - 取得時刻（fetched_at）を UTC で記録し look-ahead bias を防止

- ETL パイプライン
  - 差分更新（DB の最終取得日を参照）
  - backfill による後出し修正吸収
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit レイヤーのスキーマ定義・初期化
  - 冪等なテーブル作成（CREATE TABLE IF NOT EXISTS）
  - 監査ログ（signal_events / order_requests / executions）を別 DB または同一DBに初期化可能

- ニュース収集（RSS）
  - RSS フィードから記事収集・前処理・DB 保存（raw_news、news_symbols）
  - URL 正規化（トラッキングパラメータ除去）、記事 ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証・プライベートアドレスブロック・リダイレクト検査）
  - レスポンスサイズ上限・gzip 解凍上限による DoS 対策
  - defusedxml による XML 攻撃対策

- マーケットカレンダー管理
  - JPX カレンダーのバッチ更新ジョブ
  - 営業日判定 / 前後営業日検索 / 期間内営業日抽出（DB 優先、未取得時は曜日フォールバック）

- データ品質チェック
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比で閾値超過）
  - 主キー重複検出
  - 日付不整合（未来日・非営業日のデータなど）
  - QualityIssue オブジェクトで問題を集約

---

## 必要条件

- Python 3.10+
- 主な依存パッケージ（最低限）
  - duckdb
  - defusedxml

（プロジェクトに合わせて requirements.txt を用意してください。Slack 連携などを実装する場合は追加パッケージが必要です）

pip の例:
```
python -m pip install duckdb defusedxml
```

---

## セットアップ手順（ローカル実行の流れ）

1. リポジトリをクローン／配置
2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. 依存パッケージをインストール
   ```
   python -m pip install -U pip
   python -m pip install duckdb defusedxml
   ```
4. 環境変数を準備
   - プロジェクトルートに `.env` / `.env.local` を用意（自動読込対象）。例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動読み込みを無効にする場合：
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. データベース初期化（DuckDB）
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ（audit）を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     # あるいは既存 conn に対して init_audit_schema(conn)
     ```

---

## 使い方（主要 API の例）

- J-Quants 認証トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.JQUANTS_REFRESH_TOKEN を使用
  ```

- 株価日足を取得して保存
  ```python
  import duckdb
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- 日次 ETL の実行（カレンダー取得 → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- RSS ニュースの収集と保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # 各ソースごとの新規保存件数
  ```

- カレンダー系ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2024,1,1)))
  print(next_trading_day(conn, date(2024,1,1)))
  ```

- 品質チェック手動実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 環境変数（主なもの）

Settings クラスで参照される環境変数（必須は _require() により例外になる）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

注意: J-Quants 用のリフレッシュトークンなど機密情報は .env.local 等で管理し、バージョン管理には含めないでください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得・保存）
      - news_collector.py            -- RSS ニュース収集 / 前処理 / DB 保存
      - schema.py                    -- DuckDB スキーマ定義・初期化
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       -- 市場カレンダー管理・判定ユーティリティ
      - audit.py                     -- 監査ログ（signal/order/execution）初期化
      - quality.py                   -- データ品質チェック
    - strategy/
      - __init__.py                  -- 戦略層（拡張ポイント）
    - execution/
      - __init__.py                  -- 発注・約定管理（拡張ポイント）
    - monitoring/
      - __init__.py                  -- モニタリング用（拡張ポイント）

（README 生成元のコードベースに基づく抜粋です。実際のプロジェクトでは tests/ や scripts/ 等が追加で存在する場合があります）

---

## 開発上の注意点 / 設計方針（要約）

- 冪等性：外部 API から取得したデータは DB 保存時に ON CONFLICT（DO UPDATE / DO NOTHING）を用い重複を排除。
- トレーサビリティ：監査ログ（audit）で signal → order → execution の流れを UUID で追跡可能にする。
- セキュリティ：RSS パーサーは defusedxml、SSRF 対策、レスポンスサイズの上限などを実装。
- 耐障害性：API 通信はレートリミット管理、リトライ、トークン自動更新を備える。
- フォールバック：market_calendar 未取得時は曜日ベースの判定を用いる。

---

## よくある操作例・デバッグ

- 自動 .env ロードを無効にして単体テストなどを実行：
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  pytest
  ```

- ログレベルを DEBUG にして詳しい動作ログを確認：
  ```
  export LOG_LEVEL=DEBUG
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
  ```

---

もし README に追加したい内容（CI / テスト手順、実運用での cron 設定例、Slack 通知連携の実装方針、依存関係の具体的なバージョンなど）があれば教えてください。必要に応じてサンプル .env.example や簡単なデプロイ手順も作成します。