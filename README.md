# KabuSys

日本株自動売買システムのライブラリ（コアモジュール群）

概要
- KabuSys は日本株向けのデータ取得、データベーススキーマ管理、監査ログ（トレーサビリティ）など、アルゴリズム売買の基盤となる機能を提供する Python パッケージです。
- 主に以下を提供します:
  - J-Quants API からの市場データ取得クライアント（レート制御・リトライ・トークン自動更新付き）
  - DuckDB による階層的なスキーマ（Raw / Processed / Feature / Execution）
  - 監査ログ用テーブル群（信号→発注→約定のトレース）
  - 環境変数管理（.env の自動ロード、必須値チェック）
- 現在のバージョン: 0.1.0

主な機能一覧
- 環境設定
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で判定）
  - 必須環境変数の取得 API（settings オブジェクト）
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー等の取得
  - API レート制限対応（120 req/min 固定スロットリング）
  - 再試行（指数バックオフ、最大 3 回。対象: 408/429/5xx）
  - 401 受信時は自動でリフレッシュトークンによるトークン更新を行い1回リトライ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE を使用）
- DuckDB スキーマ（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックスの作成、テーブル作成は冪等
  - DB 初期化用 API: init_schema(db_path)、get_connection(db_path)
- 監査（Audit）スキーマ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions のテーブル定義
  - order_request_id による冪等性、すべて UTC タイムスタンプ
  - 初期化 API: init_audit_schema(conn)、init_audit_db(db_path)

前提・要求環境
- Python 3.10 以上（PEP604 の「|」型ヒントを使用）
- 必要パッケージ（最低限）:
  - duckdb
- 推奨:
  - 仮想環境（venv, pyenv など）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb
   - （将来的に requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。自動読み込みはデフォルトで有効です。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

環境変数（主なキー）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意: development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (任意: DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト: INFO)

.env の例（簡易）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_slack_channel
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

基本的な使い方（コード例）
- settings の利用
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.is_live)
```

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化して接続を取得
conn = schema.init_schema("data/kabusys.duckdb")
# 既存 DB に接続する場合は
# conn = schema.get_connection("data/kabusys.duckdb")
```

- J-Quants からデータ取得して保存する（株価日足の例）
```python
import duckdb
from kabusys.data import jquants_client
from kabusys.data import schema
from datetime import date

# DB 初期化（初回）
conn = schema.init_schema("data/kabusys.duckdb")

# データ取得（例: 銘柄コード 6501、期間指定）
records = jquants_client.fetch_daily_quotes(code="6501", date_from=date(2023,1,1), date_to=date(2023,12,31))

# 保存
inserted = jquants_client.save_daily_quotes(conn, records)
print(f"{inserted} 件保存しました")
```

- 監査ログ（Audit）テーブルの初期化
```python
from kabusys.data import audit
from kabusys.data import schema

# 既存 conn に監査スキーマを追加
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)

# または監査専用 DB を別ファイルで作る
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

設計上の注意点（重要）
- J-Quants API のレート制限は 120 req/min。jquants_client は内部でスロットリングを行いますが、外部での大量呼び出しに注意してください。
- ネットワーク障害や 429/408/5xx に対してリトライを実装しています（指数バックオフ、最大 3 回）。
- 401 エラー（認証切れ）は自動的にリフレッシュトークンを使って ID トークンを再取得し、1 回だけリトライします。
- データ保存は基本的に冪等です（ON CONFLICT DO UPDATE を利用）。しかし、アプリケーション実装側でも重複・競合に注意してください。
- すべての監査テーブルの TIMESTAMP は UTC に固定して保存します（init_audit_schema は SET TimeZone='UTC' を実行します）。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得・保存ロジック）
      - schema.py                # DuckDB スキーマ定義・初期化
      - audit.py                 # 監査ログ（signal/order/execution）
      - audit.py
      - monitoring/ (パッケージ入口)
    - strategy/                  # 戦略モジュール（将来的な置き場）
      - __init__.py
    - execution/                 # 発注実行モジュール（将来的な置き場）
      - __init__.py
    - monitoring/                # 監視用モジュール（将来的な置き場）
      - __init__.py

拡張 / 今後の実装予定（ヒント）
- strategy パッケージ内に戦略のサンプル、特徴量生成パイプラインを追加
- execution パッケージに kabuステーション等のブローカー接続・注文ロジックを実装
- Slack 通知や監視ダッシュボードの統合（monitoring）
- テスト、CI、型チェック（mypy/pytest/ruff 等）

ライセンス / コントリビューション
- （このテンプレートには記載がありません。リポジトリに LICENSE や CONTRIBUTING を追加してください）

お問い合わせ
- 実装に関する質問やバグ報告はリポジトリの Issue を作成してください。

以上。README の内容をプロジェクトの実態に合わせて適宜調整してください。