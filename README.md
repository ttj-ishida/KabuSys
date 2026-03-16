# KabuSys — 日本株自動売買プラットフォーム

このリポジトリは、J-Quants / kabuステーション 等のデータ・ブローカー連携を想定した日本株向け自動売買システムの基盤ライブラリです。データ取得、ETL、データ品質チェック、監査ログ（発注〜約定のトレース）等の共通機能を提供します。

主な設計方針
- データ取得はレート制限・リトライ・トークン自動リフレッシュに対応
- DuckDB を用いた3層（Raw / Processed / Feature）＋Execution 層のスキーマ
- ETLは差分更新・バックフィル・品質チェックを備え冪等（ON CONFLICT DO UPDATE）
- 監査ログによりシグナル→発注→約定までUUIDチェーンで完全トレース可能
- 環境変数/.env による設定管理（自動ロード機能あり）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml で判定）
  - 必須環境変数の検査
  - KABUSYS_ENV / LOG_LEVEL 等の検証

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーの取得
  - レートリミット制御、リトライ（指数バックオフ）、401時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB へ冪等的に保存する save_* 関数

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のDDL定義と初期化
  - インデックス作成、init_schema/get_connection 提供

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）: カレンダー→株価→財務→品質チェック
  - 差分取得（最終取得日ベース）、バックフィル、品質チェックとの連携
  - ETL 結果を ETLResult オブジェクトで返却

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合（未来日・非営業日）検出
  - 各チェックは QualityIssue のリストを返す（エラー/警告区分あり）

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions など監査用テーブルを初期化
  - 発注の冪等キー、タイムスタンプは UTC 保存等の設計

---

## 必要条件 / 依存関係

- Python 3.9+（typing の表記や pathlib 型ヒントに依存）
- duckdb
- 標準ライブラリ（urllib, json, logging 等）

（実プロジェクトでは requests や Slack クライアント等が別途必要になる想定）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb
# パッケージとしてインストールする場合（セットアップがある前提）
pip install -e .
```

---

## 環境変数（.env）

kabusys.config.Settings で使用する主な環境変数（必須は明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視など）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

自動ロード挙動:
- プロジェクトルート（.git または pyproject.toml）を起点に `.env` を読み込み、続けて `.env.local` を上書きします。
- OS環境変数は上書きされません（ただし `.env.local` は override=True で上書き可）。
- 自動ロードを無効化するには環境変数で: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の書式は一般的な shell 形式をサポートします（export 〜、クォート、コメント等）。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / checkout
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env を作成して必須変数を設定
   - 例: .env
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
4. DuckDB スキーマ初期化
   - Python シェルまたはスクリプトで:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)  # デフォルトは data/kabusys.duckdb を作成
     ```
   - 監査ログを別DB/同一DBに初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)  # 既存 conn に監査テーブルを追加
     # または専用DB:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（例）

- 日次 ETL を実行する:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（初回のみ）
  conn = init_schema(settings.duckdb_path)

  # ETL 実行（今日を対象）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別ジョブを呼ぶ（例: 株価だけ差分取得）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- J-Quants から手動でトークンを得る:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  print(token)
  ```

- 品質チェックの直接実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意: 実際の「発注 / 実行」機能（ブローカ連携）の実装は本コードベースで想定されている構造を提供しますが、ブローカAPIとの接続実装や本番運用時の安全対策（リスク制御、監視、異常時のロールバック等）は別途実装・確認が必要です。特に KABUSYS_ENV を "live" にすると実発注を行う想定であるため、慎重に扱ってください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存ロジック）
    - schema.py               — DuckDB スキーマ定義 & init_schema/get_connection
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - audit.py                — 監査ログテーブル定義 / 初期化
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py             — 戦略モジュール用プレースホルダ
  - execution/
    - __init__.py             — 発注実行モジュール用プレースホルダ
  - monitoring/
    - __init__.py             — 監視/アラート用プレースホルダ

主要モジュールの役割:
- config: 設定取得や .env 自動ロードのロジック（プロジェクトルート検出、.env/.env.local の優先度）
- data.jquants_client: API コール、リトライ、レート制御、DuckDB への保存ユーティリティ
- data.schema: データベース DDL（Raw/Processed/Feature/Execution 層）
- data.pipeline: ETL 管理（差分・バックフィル・品質チェック）
- data.quality: 品質チェック（欠損・スパイク・重複・日付不整合）
- data.audit: 発注〜約定の監査ログ設計・初期化

---

## 運用上の注意 / ベストプラクティス

- 機密情報（API トークン等）は Git 管理しないこと。`.env` を `.gitignore` に追加してください。
- 自動ロードが便利な反面、テストやコンテナ環境で意図しない環境変数の読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自分で設定を注入してください。
- run_daily_etl 等はネットワークや API の障害を考慮してリトライ・ロギングを備えていますが、長期運用時は監視（Slack/Prometheus 等）を追加してください。
- live 環境では必ず sandbox/paper_trading で十分な検証を行ってから切り替えてください（KABUSYS_ENV を正しく設定）。

---

## ライセンス / 貢献

- 本 README にはライセンス情報が含まれていません。実プロジェクトでは LICENCE を明示してください。
- 貢献: バグ修正・機能追加は PR を用いて行ってください。大きな変更は事前に Issue で設計方針を議論してください。

---

README は以上です。README に追加したい具体的な運用手順（例: CI/CD、Docker、cron での日次実行、Slack 通知サンプル等）があれば、その内容に合わせて補足を作成します。