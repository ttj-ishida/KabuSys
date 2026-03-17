# KabuSys

日本株自動売買システム（ライブラリ・プラットフォーム）

KabuSys は日本株を対象としたデータ取得、ETL、品質チェック、ニュース収集、監査ログ、および戦略／発注レイヤーの基盤を提供する Python パッケージです。J-Quants API や kabuステーション API と連携してデータを収集し、DuckDB を用いて冪等に保存・管理します。

---

## 主な特徴（機能一覧）

- 環境変数ベースの設定管理（自動でプロジェクトルートの `.env` / `.env.local` を読み込み可能）
- J-Quants API クライアント
  - 日足（OHLCV）・財務データ（四半期 BS/PL）・JPX カレンダーの取得
  - レート制限（120 req/min）・リトライ（指数バックオフ）・401 時のトークン自動リフレッシュ
  - 取得タイムスタンプ（fetched_at）で Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去・記事 ID は SHA-256（先頭32文字）
  - defusedxml による XML 攻撃対策、SSRF 対策、受信サイズ制限（デフォルト 10MB）
  - DuckDB へのバルク保存（INSERT … RETURNING）および銘柄コード紐付け
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義（冪等で初期化可能）
  - 監査ログ用スキーマ（signal / order_request / executions）を別途初期化可能
- ETL パイプライン
  - 差分更新（最終取得日ベース）・backfill オプション・市場カレンダー先読み
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理ユーティリティ
  - 営業日判定、前後営業日の取得、期間内営業日リスト取得、夜間更新ジョブ
- データ品質チェック（QualityIssue を返す）
  - 欠損、スパイク、重複、日付不整合の検出
- 将来的に戦略層、発注実行層、監視（monitoring）との統合を想定したモジュール構成

---

## 必要条件

- Python 3.10 以降（PEP 604 の型表記（`|`）を使用）
- 必要な Python パッケージ（例）:
  - duckdb
  - defusedxml

インストール例:
```
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトで requirements.txt を用意する場合はそちらを参照してください）

---

## 環境変数（主要な設定）

KabuSys は環境変数から設定を読み込みます。プロジェクトルートにある `.env` / `.env.local` を自動で読み込む仕組みを搭載（CWD ではなくパッケージ位置からプロジェクトルートを特定）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（Settings により _require() されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack Bot トークン（通知用途など）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルトあり:
- KABU_API_BASE_URL — デフォルト: `http://localhost:18080/kabusapi`
- DUCKDB_PATH — デフォルト: `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト: `data/monitoring.db`
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: `development`）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: `INFO`）

例（.env の簡易サンプル）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   python -m pip install duckdb defusedxml
   ```
4. 環境変数を設定（`.env` / `.env.local` をプロジェクトルートに置くか、環境変数経由で設定）
5. DuckDB スキーマを初期化（初回のみ）
   - Python REPL もしくはスクリプト内で:
     ```
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
6. （監査ログ専用 DB を使う場合）
   ```
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/audit_kabusys.duckdb")
   ```

---

## 使い方（主な API と例）

以下はライブラリとしての基本的な使い方例です。実運用ではエラーハンドリングやログ出力、監視、スケジューラ（cron / Airflow / Prefect など）との併用を推奨します。

- DuckDB スキーマ初期化:
  ```
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- J-Quants トークンの取得（内部で settings.jquants_refresh_token を使用）:
  ```
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # refresh_token を渡して指定することも可能
  ```

- ETL（日次パイプライン）の実行:
  ```
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 個別の ETL ジョブ呼び出し:
  ```
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

  fetched_prices, saved_prices = run_prices_etl(conn, date.today())
  ```

- ニュース収集:
  ```
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  ```

- 市場カレンダー操作:
  ```
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_trade = is_trading_day(conn, date(2024, 1, 4))
  next_day = next_trading_day(conn, date(2024, 1, 4))
  ```

- 品質チェック:
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 監査スキーマ初期化（既存接続に追加）:
  ```
  from kabusys.data import audit
  audit.init_audit_schema(conn, transactional=True)
  ```

---

## セキュリティと設計上の注意点

- J-Quants クライアントは API レート上限（120 req/min）とリトライ制御を実装しています。大量リクエスト時は設定を確認してください。
- news_collector は SSRF を防ぐためにスキームチェック、DNS 解決後のプライベートアドレスチェック、リダイレクト先検証を行います。また XML のパースは defusedxml を使い安全を確保しています。
- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml を上位に持つディレクトリ）を基準に行われます。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の INSERT は冪等性を考慮した ON CONFLICT を活用していますが、外部からのデータ挿入や手動編集を行う際は注意してください。
- すべてのタイムスタンプは UTC を原則として扱う設計です（監査 DB 初期化時に TimeZone を UTC に固定します）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得 + 保存）
    - news_collector.py         — RSS ニュース収集・保存・銘柄抽出
    - schema.py                 — DuckDB スキーマ定義と init_schema()
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — マーケットカレンダー管理ユーティリティ
    - audit.py                  — 監査ログスキーマ初期化（signal/order/execution）
    - quality.py                — データ品質チェック（欠損/重複/スパイク/日付不整合）
  - strategy/
    - __init__.py               — 戦略層（拡張ポイント）
  - execution/
    - __init__.py               — 発注／ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py               — 監視・メトリクス（拡張ポイント）

（プロジェクトルートに .env / .env.local / pyproject.toml / .git などを置くことを想定）

---

## 開発／拡張のヒント

- strategy/ と execution/ は各種戦略実装／ブローカー接続を追加するための拡張ポイントです。戦略は signal_events / signal_queue / orders / executions などの監査テーブルと連携して設計してください。
- ETL は id_token の注入が可能な設計になっているため、テストでは get_id_token をモックして固定トークンを渡すことで再現性のあるテストが行えます。
- news_collector._urlopen はテストで差し替え可能（SSRF 検証を回避してモックする等）。
- DuckDB 接続は軽量で多用途に使えますが、複数スレッドやプロセスで同一ファイルを扱う際の注意（ロック等）を払う必要があります。

---

## ライセンス・貢献

本 README はコードベースの説明用テンプレートです。ライセンスやコントリビューションガイドラインはプロジェクトルートに LICENSE / CONTRIBUTING.md を追加して管理してください。

---

必要であれば README に追加したい内容（例: CI 設定、より詳しい .env.example、モジュール別の API ドキュメント生成例、ユニットテストの書き方など）を教えてください。