# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。J‑Quants API からマーケットデータ・財務データ・カレンダーを取得し、DuckDB に蓄積、品質チェック、ニュース収集、監査（発注→約定トレーサビリティ）までを想定したモジュール群を提供します。

主な設計方針:
- API レート制御とリトライ（指数バックオフ）を備えた堅牢なデータ取得
- Look‑ahead bias を防ぐための fetched_at（UTC）記録
- DuckDB への冪等保存（ON CONFLICT 対応）
- RSS ニュース収集における SSRF / XML 攻撃対策
- データ品質チェック・監査ログ用スキーマの提供

---

## 機能一覧

- 環境変数管理
  - .env / .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
  - 必須設定の検証（settings オブジェクト経由）

- J‑Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミット（120 req/min）、リトライ、401 時の自動トークンリフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数群

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日からの再取得、backfill 対応）
  - 日次 ETL 実行エントリ（run_daily_etl）
  - 品質チェック呼び出し連携

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、期間内営業日の列挙
  - 夜間カレンダー更新ジョブ（calendar_update_job）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・パース（defusedxml 使用）
  - トラッキングパラメータ除去・URL 正規化・SHA‑256 による冪等 ID 生成
  - SSRF / Gzip Bomb / レスポンスサイズ制限対策
  - DuckDB への冪等保存と銘柄紐付け（news_symbols）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を定義する DDL
  - init_schema / get_connection による DB 初期化と接続

- 監査（kabusys.data.audit）
  - signal / order_request / execution を追跡する監査スキーマ
  - init_audit_db / init_audit_schema による初期化（UTC タイムゾーン固定）

- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比）、将来日付／非営業日データ検出
  - QualityIssue オブジェクトで問題を集約

---

## 前提条件

- Python 3.10 以上（PEP 604 の型注釈 | を使用）
- 主要依存パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例:
```
python -m pip install duckdb defusedxml
```
（プロジェクト化されている場合は pip install -e . を推奨）

---

## 環境変数（必須/任意）

以下はコード内 Settings により参照される主な環境変数です。`.env` または OS 環境変数で設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack Bot トークン（通知用途）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml がある階層）を探索して `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトを配置
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール
   ```
   python -m pip install duckdb defusedxml
   ```
   （プロジェクトごとに requirements.txt があればそれを使ってください）

4. 必要な環境変数を設定（.env 推奨）
   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマを初期化
   - Python から直接:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - コマンドライン例:
     ```
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
     ```

6. 監査 DB を初期化（オプション・監査専用 DB を使う場合）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要 API と実行例）

以下は代表的な処理の呼び出し例です。実運用ではロガー設定や例外管理を適切に実装してください。

- 設定を参照する:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```

- DuckDB スキーマ初期化:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 戻り値は ETLResult
  print(result.to_dict())
  ```

- 市場カレンダー更新ジョブ:
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集（既存 conn に保存）:
  ```python
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn)  # sources を渡して上書き可能
  print(results)
  ```

- J‑Quants から直接データを取得（テスト・デバッグ向け）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェックの実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意:
- jquants_client は API レート制限やリトライを自身で処理します。
- run_daily_etl は内部でカレンダー → 株価 → 財務 → 品質チェック の順に実行します。各ステップは独立してエラーハンドリングされます。

---

## ディレクトリ構成

プロジェクトは以下の主要モジュールで構成されています（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py           — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py         — DuckDB スキーマ定義と初期化
    - jquants_client.py — J‑Quants API クライアント（取得 + 保存）
    - pipeline.py       — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・ジョブ
    - news_collector.py — RSS ニュース収集・保存
    - quality.py        — データ品質チェック
    - audit.py          — 監査ログスキーマ初期化
  - strategy/
    - __init__.py       — 戦略層モジュール（将来的な拡張用）
  - execution/
    - __init__.py       — 発注/約定 管理（将来的な拡張用）
  - monitoring/
    - __init__.py       — 監視関連（将来的な拡張用）

主なファイル:
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- src/kabusys/data/calendar_management.py
- src/kabusys/data/audit.py
- src/kabusys/data/quality.py
- src/kabusys/config.py

---

## 運用上の注意 / ベストプラクティス

- 本コードは実際の発注を行うモジュール（execution 層）の具体実装を含みません。実運用で証券会社 API に接続する場合は、必ずペーパー取引モードで十分にテストしてください。
- 環境変数に秘密情報（トークン、パスワード）を保存する際は適切なアクセス制御を行ってください。
- DuckDB ファイルは定期的なバックアップを推奨します。監査ログは削除しない運用を前提としています。
- ニュース収集や外部 URL 取得では SSRF・XML 攻撃対策を実装していますが、追加のセキュリティ要件があれば運用環境に応じた制限を検討してください。
- ログレベルは LOG_LEVEL で調整可能です。運用時は INFO 〜 WARNING を推奨します。

---

## 参考 / 補足

- 自動 .env 読み込みはプロジェクトルートの探索に基づき行われます（.git または pyproject.toml があるディレクトリがルート）。パッケージ配布後もカレントワーキングディレクトリに依存しないよう設計されています。
- news_collector の RSS フィードは DEFAULT_RSS_SOURCES で定義されています。独自のソースを渡して収集を行えます。
- データベース初期化は冪等（既存テーブルはスキップ）です。監査スキーマは init_audit_schema / init_audit_db で追加できます。

---

問題や追加で載せたい使い方（例: サンプルスクリプト、cron の設定例、運用チェックリスト）があれば教えてください。README に追記して整備します。