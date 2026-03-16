KabuSys
=======

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
主に J-Quants API から市場データ・財務データ・市場カレンダーを取得し、DuckDB に保存・品質チェック・ETL を行うための機能を提供します。さらに、監査ログ（発注 → 約定のトレーサビリティ）やデータスキーマ定義も含みます。

主な目的
- J-Quants からの株価・財務・カレンダー取得（ページネーション・再試行・トークン自動更新対応）
- DuckDB 上のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ用スキーマ（シグナル → 発注 → 約定のトレーサビリティ）

機能一覧
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動ロード（プロジェクトルートを自動検出）
  - 必須環境変数の取得と検証
  - KABUSYS_ENV（development / paper_trading / live）やLOG_LEVEL の検証
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから idToken を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - RateLimiter（120 req/min 固定間隔スロットリング）
  - 自動リトライ（指数バックオフ、408/429/5xx 再試行、401 時はトークン自動更新）
  - DuckDB へ冪等保存する save_* 関数（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema / get_connection
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl（市場カレンダー→株価→財務→品質チェックの一括実行）
  - 差分取得／バックフィルロジック／品質チェック結果を集約した ETLResult
- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合（未来日・非営業日）検出
  - 各チェックは QualityIssue のリストを返す（error / warning）
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブルと初期化関数
  - トレーサビリティ（UUID 連鎖）と UTC タイムスタンプポリシー

前提条件 / 推奨環境
- Python >= 3.10 （型注釈に PEP 604 の構文を使用）
- duckdb パッケージ（DuckDB 用 Python バインディング）
- ネットワークアクセス（J-Quants API への接続）
- 必要な環境変数（下記参照）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb

   ※プロジェクトに pyproject.toml / setup.py があれば:
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env ファイルを作成してください（.env.example を参考に）。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須 / 推奨環境変数
- 必須（実運用で必須）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API のパスワード
  - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID      : 通知先チャンネル ID

- 任意 / デフォルトあり
  - KABU_API_BASE_URL     : デフォルト "http://localhost:18080/kabusapi"
  - DUCKDB_PATH           : デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH           : デフォルト "data/monitoring.db"
  - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
  - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

使い方（簡単な例）
- パッケージを import できる状態（src を PYTHONPATH に含めるか、pip install -e . を行う）を想定しています。

1) DuckDB スキーマの初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行（市場カレンダー・株価・財務の取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると本日
print(result.to_dict())
```

3) J-Quants API を直接呼ぶ（手動で取得して保存する）
```python
from datetime import date
from kabusys.data import jquants_client as jq

token = jq.get_id_token()  # settings.jquants_refresh_token を利用して取得
recs = jq.fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, recs)
```

4) 監査ログ（order/audit）スキーマ初期化
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存の DuckDB 接続に監査テーブルを追加
```

重要な挙動・設計ポイント
- .env 自動ロード: プロジェクトルートを .git か pyproject.toml で検出して .env/.env.local を読み込みます。テストで自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- J-Quants クライアント:
  - レート制限: 120 req/min（固定間隔スロットリング）
  - リトライ: 最大 3 回、408/429/5xx は指数バックオフ。429 の場合は Retry-After を優先。
  - 401 が来た場合、トークンを自動でリフレッシュして 1 回リトライ。
  - ページネーション対応（pagination_key）
  - 取得時刻は fetched_at に UTC (Z) で記録し、Look-ahead bias を防止
- 保存処理は冪等（ON CONFLICT DO UPDATE）になっており、再実行しても重複しません。
- ETL は Fail-Fast ではなく、各ステップでエラーを集約して ETLResult に格納します。品質チェックもすべて走らせてから結果を返します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                       - パッケージ定義（version 等）
  - config.py                         - 環境変数 / 設定管理（.env 自動ロード、settings オブジェクト）
  - execution/                         - 発注・実行関連モジュール（未実装プレースホルダ）
  - strategy/                          - 戦略関連（未実装プレースホルダ）
  - monitoring/                        - 監視関連（未実装プレースホルダ）
  - data/
    - __init__.py
    - jquants_client.py               - J-Quants API クライアント（取得 / 保存 / 認証 / リトライ）
    - schema.py                       - DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution）
    - pipeline.py                     - ETL パイプライン（差分更新・バックフィル・品質チェック）
    - audit.py                        - 監査ログ用スキーマと初期化
    - quality.py                      - データ品質チェック（欠損・重複・スパイク・日付不整合）

テスト / 開発メモ
- Python バージョンは 3.10 以上を推奨（型注釈に | を使用）。
- DuckDB を使っているため、データベースファイル（デフォルト data/kabusys.duckdb）が作成されます。必要に応じて環境変数 DUCKDB_PATH を設定してください。
- ETL の初回実行時は J-Quants の全データ取得（2017-01-01 以降）となるため時間がかかる可能性があります。run_prices_etl 等は date_from を指定して部分的に取得できます。
- ロギングは設定ファイルや LOG_LEVEL 環境変数で調整してください。

付録：よく使う API（抜粋）
- config
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level, settings.is_live / is_paper / is_dev
- jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token, code, date_from, date_to) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int
- data.schema
  - init_schema(db_path) -> duckdb.Connection
  - get_connection(db_path) -> duckdb.Connection
- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]
- data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

お問い合わせ / 貢献
- バグ報告や機能提案は Issue を立ててください。プルリク歓迎です。コードスタイルやテストの追加で貢献いただけると助かります。

以上を参考に、環境変数を準備して DuckDB を初期化し、run_daily_etl で日次 ETL を実行してください。必要であれば、README に実行用のスクリプト例や .env.example を追加できます。必要なら追記します。