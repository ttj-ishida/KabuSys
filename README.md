# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants や kabuステーション等の外部 API から市場データを取得し、DuckDB ベースで永続化・品質チェック・監査ログを行うためのモジュール群を提供します。

主な設計方針・特徴
- API レート制限遵守（J-Quants: 120 req/min 固定スロットリング）
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ対応
- DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（シグナル→発注→約定のトレースを UUID で保証）
- 環境変数 / .env の自動ロード機能（プロジェクトルート検出ベース）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local を自動でロード（必要に応じて無効化可）
  - 必須環境変数の検証
  - KABUSYS_ENV（development / paper_trading / live）やログレベルの検証

- J-Quants クライアント（kabusys.data.jquants_client）
  - ID トークン取得（リフレッシュ）
  - 株価日足（OHLCV）・四半期財務・マーケットカレンダー取得（ページネーション対応）
  - 取得データを DuckDB に冪等保存する関数（raw_prices / raw_financials / market_calendar）

- データスキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL 定義
  - テーブル・インデックスの初期化（init_schema, get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL：run_prices_etl, run_financials_etl, run_calendar_etl
  - 差分取得ロジック（最終取得日ベース、backfill オプション）
  - 品質チェック結果の集約（ETLResult）

- 品質チェック（kabusys.data.quality）
  - 欠損値検出、スパイク検知（前日比）、重複チェック、日付整合性チェック
  - QualityIssue による問題記録（severity: error / warning）

- 監査ログ（kabusys.data.audit）
  - シグナル / 発注要求 / 約定の監査テーブル定義
  - 監査テーブル初期化（init_audit_schema, init_audit_db）
  - UTC タイムスタンプ、冪等キー、FK 制約等の設計に準拠

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型表記などを使用）
- DuckDB を使用（Python パッケージ：duckdb）

推奨手順（ローカル開発環境）
1. 仮想環境作成・有効化
   - macOS/Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 依存パッケージのインストール
   - 最低限: duckdb
     - pip install duckdb
   - 他に必要なパッケージがあればプロジェクトの requirements.txt / pyproject.toml に従ってください。

3. 環境変数の用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

その他（任意またはデフォルトあり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB 保存パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 .env（必要な値のみ）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数経由で設定されます（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants トークンは settings から自動使用）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())  # ETLResult の内容を確認
```

3) 監査テーブル初期化（監査専用 or 既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存の conn に監査テーブルを追加
# または init_audit_db("data/audit.duckdb") で監査専用 DB を作る
```

4) 直接 J-Quants クライアントを利用
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を用いて id_token を取得
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
# 保存:
from kabusys.data.jquants_client import save_daily_quotes
saved = save_daily_quotes(conn, records)
```

5) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点
- run_daily_etl は内部で市場カレンダーを先に取得し、target_date を営業日に調整してから株価・財務を取得します。
- ETL はステップ単位でエラーハンドリングされ、1 ステップ失敗でも他は継続します。戻り値の ETLResult に errors / quality_issues が格納されます。

---

## 主要モジュール API（抜粋）

- kabusys.config
  - settings: Settings オブジェクト（プロパティで各種環境値へアクセス）
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token: str | None, code: str | None, date_from: date | None, date_to: date | None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date: date|None, id_token: str|None, run_quality_checks: bool = True, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - get_last_price_date(conn), get_last_financial_date(conn), get_last_calendar_date(conn)

- kabusys.data.quality
  - run_all_checks(conn, target_date: date|None, reference_date: date|None, spike_threshold: float = 0.5) -> list[QualityIssue]
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

以下はリポジトリ内の主要ファイルとサブパッケージの一覧（今回提示されたコードベースに基づく）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - pipeline.py
      - audit.py
      - quality.py

各モジュールの役割
- config.py: 環境変数のロード・検証
- data/: データ取得・保存・ETL・品質・監査に関する実装群
- execution/, strategy/, monitoring/: 将来的な発注ロジックや戦略、監視用コードを配置する想定のプレースホルダ

---

## 運用上の注意 / ベストプラクティス

- 環境変数を誤って公開しないよう `.env` はリポジトリにコミットしないこと（.gitignore に追加）。
- J-Quants の API レート上限（120 req/min）を厳守するよう設計済みですが、呼び出しパターンによっては別途調整が必要になることがあります。
- DuckDB ファイルは定期的なバックアップを推奨します。
- 本ライブラリは ETL 中に品質チェックでエラーが検出されても自動停止しない設計です（呼び出し側で結果を評価して必要な対応を行ってください）。
- 本番運用（is_live）の際は SLACK 等での通知や監視プロセスを整備してください。

---

必要があれば次の内容も追加で作成できます
- 実行スクリプト（CLI）や systemd / cron 用の起動例
- 詳細な .env.example
- ユニットテストの書き方とテストカバレッジ例
- strategy / execution 層の具体的なサンプル（発注ワークフローの実装例）

ご希望があれば、特定の操作例（ETL の cron 化、監査ログの検索クエリ、品質チェックレポート出力など）を追加で作成します。