# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注→約定トレーサビリティ）用のユーティリティを提供します。

> 現在の実装では、strategy / execution / monitoring パッケージは骨組みのみで、主要な機能は data パッケージに実装されています。

## 主な特徴（機能一覧）

- 環境変数管理
  - .env / .env.local をプロジェクトルートから自動読み込み（自動ロードを無効化可）
  - 必須値チェック（Settings クラス）
- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、408/429/5xx 対象）、401 受信時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）の記録により Look-ahead バイアス抑制
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- ニュース収集（RSS）
  - RSS フィードから記事を収集し raw_news テーブルへ保存
  - URL 正規化（トラッキングパラメータ除去）、記事 ID を SHA-256(先頭32文字) で生成して冪等性を確保
  - SSRF / XML Bomb / Gzip Bomb 等の防御（defusedxml、ホスト検査、最大受信バイト制限等）
  - 銘柄コード抽出（4桁の既知銘柄コードと照合）
- データベーススキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層を含むスキーマ初期化
  - init_schema(), init_audit_db() による冪等初期化
- ETL パイプライン
  - 差分更新（最終取得日を基に差分のみ取得）
  - バックフィル（後出し修正吸収のための再取得）
  - 日次 ETL（run_daily_etl）でカレンダー→株価→財務→品質チェックを実行
- データ品質チェック
  - 欠損、重複、日付不整合（未来日付 / 非営業日データ）、スパイク検出
  - QualityIssue オブジェクトとして問題を集約
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティ
  - calendar_update_job による差分更新ジョブ
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルによる発注→約定のトレーサビリティ
  - order_request_id を冪等キーとして扱う設計

## 必要条件

- Python 3.10 以上（PEP 604 の型表記（X | Y）を使用）
- 主要依存ライブラリ
  - duckdb
  - defusedxml

（プロジェクト全体で追加の依存がある場合は requirements.txt を参照してください）

例:
```
python3 -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くことで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - .env.example（サンプル）を作成して必要な値を設定してください。

5. データベース初期化
   - DuckDB スキーマを作成:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

## 使い方（主要 API の例）

- 設定値へアクセス:
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- 日次 ETL を実行:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- RSS ニュース収集ジョブ:
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 既知銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- マーケットカレンダー差分更新（夜間バッチ）:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- DuckDB 接続取得のみ（初期化しない）:
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- 監査スキーマを既存接続に追加:
  ```python
  from kabusys.data.audit import init_audit_schema
  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数・アプリ設定管理（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py     — RSS ニュース収集・保存・銘柄紐付け
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン（差分更新、日次 ETL 実体）
    - calendar_management.py— カレンダー管理・営業日ユーティリティ・更新ジョブ
    - audit.py              — 監査ログテーブル初期化・監査用DDL
    - quality.py            — データ品質チェック
  - strategy/
    - __init__.py           — 戦略層（拡張ポイント）
  - execution/
    - __init__.py           — 発注実装（拡張ポイント）
  - monitoring/
    - __init__.py           — 監視関連（拡張ポイント）

## 知っておくべき実装上のポイント / 注意事項

- 環境変数自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われます。テスト等で自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）に合わせた固定間隔スロットリングとリトライ実装が含まれます。
- DuckDB への保存は可能な限り冪等性（ON CONFLICT）を担保しています。
- news_collector は SSRF 対策、XML/Bomb 対策、受信サイズ制限などセキュリティに配慮した実装です。
- strategy / execution / monitoring モジュールは骨組みのみで、具体的な戦略ロジックやブローカー連携は実装済みではありません（拡張ポイントとして利用してください）。
- すべての時刻は設計上 UTC を基準に扱う箇所が多くあります（例: fetched_at、監査ログ等）。

## 開発 / 貢献

- コードは可読性を重視した設計で、ユニットテストの追加や機能拡張が容易な構造になっています。
- 新しい戦略や発注実装を追加する場合は strategy/ または execution/ 以下にモジュールを追加してください。
- DB スキーマ変更や追加カラムの導入は schema.py を更新し、既存データのマイグレーション方針を明確にしてください。

## ライセンス・その他

- 本リポジトリにライセンスファイルが含まれている場合はそちらに従ってください。

---
この README はコードベースの現状（data パッケージ中心の実装）に基づいて作成しています。strategy / execution や外部ブローカー連携、Slack 通知等は別途実装が必要です。必要があれば「運用手順」「サンプル .env.example」「詳細な ETL 運用フロー」「単体テスト例」などの追補ドキュメントを作成します。必要な項目があれば教えてください。