# KabuSys — 日本株自動売買システム (README)

## 概要
KabuSys は日本株のデータ収集、品質チェック、特徴量作成、監査ログまでを備えた自動売買プラットフォームのコアライブラリです。本リポジトリは主にデータ層（J-Quants APIクライアント、DuckDBスキーマ、ETLパイプライン、データ品質チェック）と監査ログ（発注〜約定のトレーサビリティ）を実装しています。戦略や実際の発注層は拡張可能な設計になっています。

主な設計方針：
- APIレート制限・リトライ・トークンリフレッシュに対応した堅牢なデータ取得
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）と実行（Execution）レイヤ
- ETL は差分更新（バックフィル対応）で冪等性を維持
- データ品質チェックを集中的に行い、問題を収集して呼び出し元で対処可能にする
- 発注〜約定までの監査ログ（UUIDチェーン）を保存して完全なトレーサビリティを実現

## 機能一覧
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPXマーケットカレンダーの取得
  - APIレート制限（120 req/min）制御
  - 再試行（指数バックオフ）、401時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）をUTCで記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義・初期化関数（init_schema）
- ETL パイプライン
  - 差分更新（最終取得日基準）、バックフィル、先読み（カレンダー）
  - run_daily_etl による一括処理（カレンダー→株価→財務→品質チェック）
- データ品質チェック
  - 欠損データ、主キー重複、スパイク（前日比閾値）、日付不整合（未来日付/非営業日）
  - QualityIssue オブジェクトの一覧を返す
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを初期化する init_audit_schema
  - 発注フローを UUID で追跡可能にするモデル

## 必要条件
- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
- ネットワーク接続（J-Quants API）
- 環境変数（必須項目は下記参照）

※実行環境に合わせて必要な追加パッケージ（Slack API クライアント等）を導入してください。

## セットアップ手順（開発環境）
1. リポジトリをクローンしてルートに移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   最低限 DuckDB を使います：
   ```
   pip install duckdb
   ```
   プロジェクトのパッケージ化がある場合は開発インストール：
   ```
   pip install -e .
   ```

4. 環境変数の設定
   プロジェクトルートの `.env` / `.env.local`（自動読み込み）またはOS環境変数として設定してください。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL — (DEBUG|INFO|WARNING|ERROR|CRITICAL)。デフォルト: INFO

.env の自動読み込みについて
- パッケージ起点のファイルからプロジェクトルートを .git または pyproject.toml で検出し、`.env` → `.env.local` の順で読み込みます（OS 環境変数は上書きされません）。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

## 使い方（簡単なコード例）

以下は最小限の例です。DuckDB スキーマを初期化し、日次ETLを実行します。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリは自動作成されます）
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（デフォルトは今日）
```python
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存DB接続
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- J-Quants のトークン注入（テスト用）
```python
# テストで事前に取得した id_token を渡すことで外部API呼び出しの差し替えが可能
result = pipeline.run_daily_etl(conn, id_token="テスト用トークン")
```

- 監査ログテーブルの初期化
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

## ETL の挙動（ポイント）
- run_daily_etl は次の順に処理：
  1. 市場カレンダー ETL（先読み days = 90、デフォルト）
  2. 株価日足 ETL（差分取得＋backfill、backfill_days=3 デフォルト）
  3. 財務データ ETL（差分取得＋backfill）
  4. 品質チェック（run_quality_checks=True の場合）
- 各ステップは個別に例外処理され、1ステップ失敗でも他ステップは継続します。戻り値は ETLResult（取得件数、保存件数、品質問題、エラー一覧など）です。

## データ品質チェック
提供されるチェック：
- 欠損データ（OHLC 欄の NULL）
- 主キー重複（date, code）
- スパイク検出（前日比絶対値 > threshold、デフォルト 50%）
- 日付不整合（未来データ、非営業日の存在）

各チェックは QualityIssue のリストを返します。severity は "error" または "warning"。

## ディレクトリ構成
主要ファイル・モジュールを抜粋すると：

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理（.env 自動読み込み等）
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント（取得・保存ロジック）
      - schema.py                  — DuckDB スキーマ定義・初期化
      - pipeline.py                — ETL パイプライン（差分更新・品質チェック）
      - quality.py                 — データ品質チェック
      - audit.py                   — 監査ログ（発注〜約定のトレーサビリティ）
      - pipeline.py                — ETL orchestration
    - strategy/
      - __init__.py                — 戦略関連（拡張ポイント）
    - execution/
      - __init__.py                — 発注／実行層（拡張ポイント）
    - monitoring/
      - __init__.py                — 監視用コード（未実装箇所あり）

（README にない追加ファイル・ドキュメントがあればプロジェクトルートにあるはずです）

## 開発・運用上の注意
- .env ファイルをリポジトリに含めないでください（シークレットのため）。`.env.example` を作成して共有する運用を推奨します。
- J-Quants のレート制限（120 req/min）を超えないように設計済みですが、大規模バッチや並列実行時は注意してください。
- DuckDB のスキーマは冪等に作成されます。初回は schema.init_schema() を呼んでください。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読込を無効にし、テスト用の環境変数を注入してください。
- 監査ログは削除されない前提で設計されています。FK は ON DELETE RESTRICT 等を用いて履歴保持を保証します。
- すべての TIMESTAMP は UTC で扱うことを想定しています（audit.init_audit_schema は TimeZone='UTC' を設定します）。

## 付録：よく使う関数一覧（抜粋）
- kabusys.config.settings — 環境設定アクセス
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.fetch_financial_statements(...)
- kabusys.data.jquants_client.fetch_market_calendar(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- kabusys.data.quality.run_all_checks(conn, ... )
- kabusys.data.audit.init_audit_schema(conn)
- kabusys.data.audit.init_audit_db(db_path)

---

必要であれば、README にCLIコマンド例、.env.example のテンプレート、より詳細な API 使用例（pagination の扱い、id_token の使い方など）を追加します。どの情報を優先して追加しますか？