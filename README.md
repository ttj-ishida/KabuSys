# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。J-Quants API から市場データを取得し、DuckDB に保存・加工・品質チェックを行い、戦略層・発注層と連携するための基盤機能（データプラットフォーム、ETL、監査ログ）を提供します。

主な設計方針:
- データ取得はレート制限・リトライ・トークン自動更新に対応
- DuckDB を用いた3層（Raw / Processed / Feature）データスキーマ
- ETL は差分更新・バックフィルをサポートし、品質チェックを実行
- 発注から約定までの監査ログ（トレーサビリティ）を整備

---

## 機能一覧

- 環境変数／設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定に対するエラーチェック

- J-Quants API クライアント（data.jquants_client）
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大3回）、401 発生時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層を含むテーブル定義
  - インデックス、外部キー制約、型チェックなどの DDL を提供
  - init_schema() による冪等な初期化

- ETL パイプライン（data.pipeline）
  - 差分更新（DB の最終取得日をもとに未取得分のみ取得）
  - backfill による過去数日分の再取得（API の後出し修正に対応）
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェックの統合実行（data.quality）

- データ品質チェック（data.quality）
  - 欠損データ検出（OHLC 欄など）
  - 異常値（スパイク）検出（前日比）
  - 主キー重複チェック
  - 日付不整合（未来日付、非営業日のデータ）チェック
  - 各チェックは QualityIssue オブジェクトを返す（error / warning）

- 監査ログ（data.audit）
  - シグナル→発注要求→約定までを UUID ベースで追跡するテーブル群
  - 発注の冪等キー（order_request_id）による二重発注防止
  - init_audit_schema / init_audit_db による冪等初期化

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 のユニオン型記法などを使用）
- duckdb（DuckDB Python パッケージ）
- 標準ライブラリの urllib 等

インストール例（プロジェクト配布パッケージがある前提）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# またはパッケージ配布があれば: pip install .
```

---

## 環境変数（必須・任意）

KabuSys は環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml）を起点に `.env` → `.env.local` を自動読み込みします。OS 環境変数が優先されます。

主要な環境変数（Settings に定義）:
- 必須
  - JQUANTS_REFRESH_TOKEN      : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD         : kabuステーション API のパスワード
  - SLACK_BOT_TOKEN           : Slack Bot トークン（通知等）
  - SLACK_CHANNEL_ID          : Slack チャンネル ID
- 任意（デフォルトあり）
  - KABU_API_BASE_URL         : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH               : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH               : SQLite 用パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV               : environment（development / paper_trading / live、デフォルト: development）
  - LOG_LEVEL                 : ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- テスト用
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化する（値を 1 に）

サンプル .env（例）
```
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
KABU_API_PASSWORD=あなたの_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: .env のパースはクォート・コメント・export プレフィックスに対応します。

---

## セットアップ手順

1. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール
   ```
   pip install duckdb
   ```

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

3. 環境変数の用意
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください。
   - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから schema.init_schema() を呼び出してください（デフォルトパスは settings.duckdb_path）。
   - 例（簡易スクリプト）:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     print("initialized:", settings.duckdb_path)
     conn.close()
     ```

5. （任意）監査ログ専用スキーマ初期化
   ```python
   from kabusys.data import audit, schema
   conn = schema.init_schema("data/kabusys.duckdb")
   audit.init_audit_schema(conn)
   conn.close()
   ```

---

## 使い方（基本的な例）

- J-Quants の ID トークンを取得する:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- 日次 ETL を実行する（market calendar → prices → financials → 品質チェック）:
  ```python
  from datetime import date
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

  オプション:
  - id_token を外部で取得して注入可能（テストや専用トークン使用時）
  - backfill_days や spike_threshold を調整可能

- 品質チェックだけを実行する:
  ```python
  from kabusys.data import quality, schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=date(2025, 1, 1))
  for i in issues:
      print(i)
  conn.close()
  ```

- 監査ログを初期化（専用 DB を使う場合）:
  ```python
  from kabusys.data import audit
  conn = audit.init_audit_db("data/audit.duckdb")
  conn.close()
  ```

---

## 実装上のポイント（運用情報）

- jquants_client:
  - レート制御は固定間隔のスロットリング（120 req/min）を実装
  - HTTP 408/429/5xx はリトライ（指数バックオフ）、429 の場合は Retry-After を尊重
  - 401 レスポンス時はリフレッシュトークンから ID トークンを再取得して 1 回だけリトライ
  - 取得したデータには fetched_at を UTC ISO8601 で保存（Look-ahead bias 対策）

- DuckDB スキーマ:
  - 各テーブルは CREATE IF NOT EXISTS で冪等に作成
  - raw テーブルへの挿入は ON CONFLICT DO UPDATE を用いることで冪等性を確保
  - audit テーブルでは TIMESTAMP を UTC で保存するように SET TimeZone='UTC' を実行

- ETL:
  - デフォルトでは差分更新単位は営業日単位
  - backfill_days により数日前から再取得して API 後出し修正を吸収
  - 品質チェックはエラーでも ETL を継続し、呼び出し元が停止判断を行う設計

---

## ディレクトリ構成

（プロジェクトの主要ファイル構成。src 配下にパッケージを配置する構成を想定）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存ロジック）
    - schema.py                      — DuckDB スキーマ定義・初期化
    - pipeline.py                    — ETL パイプライン（差分取得・保存・品質チェック）
    - audit.py                       — 監査ログ（シグナル→発注→約定のトレース）
    - quality.py                     — データ品質チェック
  - strategy/
    - __init__.py                    — 戦略関連（未実装のプレースホルダ）
  - execution/
    - __init__.py                    — 発注・ブローカー連携（未実装のプレースホルダ）
  - monitoring/
    - __init__.py                    — 監視／アラート（未実装のプレースホルダ）

その他トップレベル（リポジトリルート）:
- .env, .env.local                    — 環境変数（プロジェクトルートに置くと自動読み込み）
- pyproject.toml / setup.cfg 等      — パッケージ設定（存在する場合）

---

## 開発・運用上の注意

- 環境変数の自動読み込みはプロジェクトルートを .git / pyproject.toml で検出します。テスト実行などで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB ファイルはローカルファイル（デフォルト data/kabusys.duckdb）に保存されます。バックアップやパーミッションに注意してください。
- 本パッケージでは kabuステーション API （KABU_API_BASE_URL）や Slack 連携のためのトークンを要求します。これらの連携は実運用で機密情報を含むため、適切に管理してください。
- 監査ログは削除しない前提で設計されています。サイズ管理やアーカイブ方針を運用ルールとして策定してください。

---

必要に応じて README を拡張して、戦略実装例、発注モジュール利用法、CI/CD、開発用の Docker イメージやテスト手順などを追加できます。追加項目の希望があれば教えてください。