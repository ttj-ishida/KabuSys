# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。データ取得（J‑Quants）、ETL、データ品質チェック、DuckDB スキーマ管理、監査ログ（発注→約定のトレーサビリティ）など、アルゴリズム取引基盤のデータ基盤と運用周りの共通機能を提供します。

バージョン: 0.1.0

---

## 概要

主な目的は「日本株の市場データを安全かつ再現可能に取得・保存し、上位レイヤ（特徴量生成・戦略・発注）へ橋渡しする」ことです。本ライブラリは以下を重視して実装されています。

- API レート制限遵守（固定間隔スロットリング）
- 再試行（指数バックオフ）とトークン自動リフレッシュ
- Look‑ahead bias の防止（取得時刻を UTC で記録）
- DuckDB への冪等（ON CONFLICT DO UPDATE）保存
- ETL の差分更新・バックフィル・品質チェックのフロー
- 発注～約定の監査ログ（UUID によるトレース）

---

## 機能一覧

- 環境設定管理（`.env` 自動読み込み、必須環境変数取得）
- J‑Quants API クライアント
  - 日足（OHLCV）/ 財務（四半期） / JPX カレンダーの取得
  - レート制限、リトライ、401 時のトークン再取得
  - ページネーション対応
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のスキーマ定義と初期化
  - インデックス作成
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）
  - バックフィル（デフォルト 3 日）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェックの実行
- 品質チェック
  - 欠損データ検出（OHLC）
  - スパイク（前日比）検出
  - 主キー重複検出
  - 日付不整合（未来日付・非営業日のデータ）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル
  - 発注の冪等キー（order_request_id）やタイムスタンプ（UTC）
- プレースホルダーパッケージ
  - strategy, execution, monitoring（各レイヤ実装のためのパッケージ構成）

---

## 必要条件

- Python 3.10 以上（型アノテーションに Python 3.10 の union 型構文を使用）
- 依存パッケージ:
  - duckdb

必要に応じてプロジェクトの setup/requirements に他ライブラリを追加してください（本コードでは HTTP は標準ライブラリ urllib を使用）。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成・有効化（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール
   ```
   pip install duckdb
   ```
   （パッケージ管理に requirements.txt や pyproject.toml を用意する場合はそちらを使用してください）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると、自動的に読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化可能）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API（kabuステーション）パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン（通知用）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - データベースパス（任意、デフォルト値あり）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
   - その他:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

5. DuckDB スキーマの初期化（サンプル）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   監査ログを別 DB または同一接続へ初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主要な API 例）

- J‑Quants トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を参照
  ```

- データ取得と保存（例: 日足取得 → DuckDB 保存）
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  ```

- ETL の日次実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=...)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 自動環境読み込みを無効化（テスト等で）
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してパッケージインポート時の `.env` 自動ロードを無効にできます。

---

## 実装上の注意点 / 動作仕様

- レート制限: J‑Quants は 120 req/min を想定。モジュール内で固定間隔スロットリングを行っています（RateLimiter）。
- リトライ: ネットワーク／HTTP 408/429/5xx に対して最大 3 回の指数バックオフリトライを行います。429 の場合は Retry‑After ヘッダを優先。
- トークン管理: ID トークンはモジュールレベルでキャッシュされ、401 を受けた場合はリフレッシュして 1 回リトライします。
- 保存の冪等性: DuckDB への保存処理は ON CONFLICT DO UPDATE を使用して重複を排除します。
- 時刻とタイムゾーン: 取得時刻（fetched_at）や監査タイムスタンプは UTC を使用する方針です（監査用 init で TimeZone='UTC' を設定）。

---

## ディレクトリ構成

主要なファイル / パッケージ（リポジトリの src/kabusys 配下）:

- src/kabusys/
  - __init__.py           - パッケージエントリ（バージョンなど）
  - config.py             - 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py   - J‑Quants API クライアント（取得・保存・認証）
    - schema.py           - DuckDB スキーマ定義と初期化関数
    - pipeline.py         - ETL パイプライン（run_daily_etl 等）
    - audit.py            - 監査ログ（signal/order/execution テーブル）
    - quality.py          - データ品質チェック
  - strategy/
    - __init__.py         - 戦略関連モジュール（拡張用）
  - execution/
    - __init__.py         - 発注／ブローカー連携（拡張用）
  - monitoring/
    - __init__.py         - 監視／アラート用（拡張用）

---

## よくあるユースケース

- 初回ロード: init_schema() で DB を作成 → run_daily_etl() を使用してデータを取得・保存。
- 運用: cron / Airflow 等から daily run を呼び出し、品質問題を監視してアラートを出す。
- 戦略開発: features テーブルや processed レイヤを作成し、strategy パッケージ内で特徴量を用いてシグナル生成。生成したシグナルは audit / order_requests へ記録し、execution レイヤでブローカー送信を行う。

---

## 今後の拡張案（例）

- kabu ステーション API 用の実際の発注クライアント実装（execution パッケージ）
- Slack 通知統合（monitoring）
- CI 用の自動テスト・モック HTTP サーバによる API シミュレーション
- メトリクス収集（Prometheus 等）

---

以上。README のテンプレートや使い方の例はプロジェクトの実際のワークフローに合わせて調整してください。必要であれば README の英語版やサンプルスクリプト（CLI や systemd / cron 用の例）も作成します。