# KabuSys — 日本株 自動売買プラットフォーム（README）

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。本リポジトリはデータ取得・保存（Data）、ETL パイプライン、データ品質チェック、監査ログ（Audit）など、取引戦略の実行基盤に必要な低レイヤー機能群を提供します。

主な設計方針：
- データの冪等性（ON CONFLICT DO UPDATE）を重視
- API レート制限とリトライを考慮した堅牢なクライアント実装
- 監査可能なトレーサビリティ（UUID ベースの連鎖）
- ETL 実行後にデータ品質チェックを実施し、問題を検出して通知可能にする

---

## 機能一覧
- 環境変数 / .env の自動読み込み（プロジェクトルートの `.env` / `.env.local`、必要に応じて無効化可能）
- 設定ラッパ（`kabusys.config.Settings`）:
  - J-Quants リフレッシュトークン取得
  - kabuステーション API 設定
  - Slack 関連設定
  - DB パスや実行環境（development/paper_trading/live）管理
- J-Quants API クライアント（`kabusys.data.jquants_client`）:
  - 日次株価（OHLCV）、財務（四半期）、JPX カレンダー取得
  - 固定間隔レートリミッタ（120 req/min）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - フェッチ時刻（fetched_at）を UTC で記録（Look-ahead bias 対策）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義・初期化（`kabusys.data.schema`）:
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義、外部キーを考慮した作成順序
- ETL パイプライン（`kabusys.data.pipeline`）:
  - 差分取得（最終取得日からの差分、自動バックフィル）
  - 市場カレンダーの先読み
  - ETL 実行結果を表す `ETLResult`
  - 品質チェック呼び出しとの統合
- データ品質チェック（`kabusys.data.quality`）:
  - 欠損データ、スパイク（前日比閾値）、主キー重複、日付整合性（未来日・非営業日）検出
  - 各チェックは `QualityIssue` を返し、重大度（error/warning）を付与
- 監査ログ（`kabusys.data.audit`）:
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル群
  - 冪等キー（order_request_id）、UTC タイムスタンプ、ステータス管理
- パッケージ構造は Strategy / Execution / Monitoring 用の拡張ポイントを想定（空の __init__ を配置）

---

## 必要条件（推奨）
- Python 3.10 以上（型ヒントに `X | None` 構文を使用）
- pip（パッケージ管理）

依存例（最低限）:
- duckdb

（実際の運用では Slack 通知や証券会社 API クライアントなど追加依存が必要になる可能性があります）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限（DuckDB を使用する場合）:
     ```
     pip install duckdb
     ```
   - 開発・CI 用の requirements.txt / pyproject があればそれに従ってください。
   - 将来的に Slack や kabu API クライアントを組み合わせる場合は追加パッケージをインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 例（`.env`）:
     ```
     JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
     KABU_API_PASSWORD=あなたの_kabu_api_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - `.env.example` を用意している場合はそれを参考に作成してください。

---

## 使い方（基本例）

以下は簡単な Python REPL / スクリプト例です。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH のデフォルト値を参照
conn = schema.init_schema(settings.duckdb_path)
```

- 日次 ETL を実行（当日分）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を明示することも可能
print(result.to_dict())
```

- J-Quants ID トークンを明示的に取得して ETL に渡す
```python
from kabusys.data import jquants_client as jq
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
id_token = jq.get_id_token()  # settings.jquants_refresh_token が使われる
result = run_daily_etl(conn, id_token=id_token)
```

- 個別ジョブの実行（例：株価 ETL）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- 品質チェックを単独で実行
```python
from kabusys.data import quality
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
issues = quality.run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 環境変数（主要なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabu API パスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- 任意 / デフォルトあり
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 実行環境（development, paper_trading, live） デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL） デフォルト: INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 を設定）

環境変数に足りない必須キーがあると `kabusys.config.Settings` のプロパティアクセス時に `ValueError` が発生します。

---

## 注意点 / 実運用メモ
- J-Quants API はレート制限（120 req/min）があります。クライアントは固定間隔の RateLimiter を実装していますが、運用時は別途メトリクス監視や分散実行時の調整が必要です。
- HTTP エラー時はリトライ（最大 3 回）を行い、429 (Retry-After ヘッダ) を尊重します。401 が来た場合はリフレッシュトークンで自動更新を試みます。
- ETL は基本的に差分更新（バックフィル）方式です。backfill_days により過去数日分を再取得して API 後出し修正に対応します。
- 品質チェックは Fail-Fast ではなく全チェックを実行して結果を返します。呼び出し側でエラー閾値に応じた対応を実施してください。
- 監査ログ（audit）スキーマは削除しない前提になっています。履歴を常に保持する設計です。
- すべてのタイムスタンプの保存は UTC を原則としています（監査 DB 初期化時に TimeZone を UTC に設定）。

---

## ディレクトリ構成（概要）
プロジェクト内ファイル（主なもの）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み / Settings
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得 + 保存）
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（差分更新・品質チェック統合）
    - quality.py             # データ品質チェック
    - audit.py               # 監査ログ（トレーサビリティ）定義・初期化
    - audit.py               # 監査用 DB 初期化（audit schema）
  - strategy/
    - __init__.py            # 戦略モジュールのエントリ（拡張点）
  - execution/
    - __init__.py            # 発注 / 約定処理のエントリ（拡張点）
  - monitoring/
    - __init__.py            # 監視・メトリクス用（拡張点）

（上記はリポジトリ内の主要ファイル抜粋です）

---

## 今後の拡張ポイント（例）
- kabu ステーション / 証券会社 API への発注実装（execution 層）
- 戦略モジュール（strategy）にアルゴリズムやポートフォリオ最適化の実装
- Slack / PagerDuty 等によるアラート連携（monitoring）
- より詳細なテストケース、CI、ドキュメント（DataPlatform.md 等）

---

必要であれば、README に実行例（cron や Airflow でのスケジューリング例）、`.env.example` のテンプレート、開発向けセットアップ（pre-commit, linters, テスト実行方法）などの追加項目も作成します。どの情報を優先して追加しますか？