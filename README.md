# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ収集、ETL、品質チェック、監査ログ、ニュース収集など自動売買システムの基盤機能を提供します。

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からのマーケットデータ（株価・財務・カレンダー）取得と DuckDB への冪等保存
- RSS ベースのニュース収集と記事の正規化・銘柄紐付け
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定、前後営業日計算）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ用テーブル定義）
- 環境変数設定管理（.env の自動読み込み、検証）

設計上の特徴：
- API レート制御（J-Quants: 120 req/min）
- リトライ（指数バックオフ）・トークン自動更新
- DuckDB を用いたローカル軽量永続化（DDL は冪等）
- ニュース収集での SSRF 防御・XML 安全パーシング・レスポンスサイズ制限

---

## 主な機能一覧

- kabusys.config
  - 環境変数の読み込み（.env / .env.local、自動ロード）とキー必須チェック
  - settings オブジェクト経由で設定取得

- kabusys.data.jquants_client
  - get_id_token、fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar
  - save_daily_quotes、save_financial_statements、save_market_calendar（DuckDB に冪等保存）
  - RateLimiter / retry / token キャッシュ

- kabusys.data.news_collector
  - RSS フィード取得（gzip 対応）、XML パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事 ID 生成（SHA-256 の先頭 32 文字）
  - SSRF 対策、最大受信バイト数制限、DuckDB へのバルク挿入（INSERT ... RETURNING）
  - 銘柄コード抽出と news_symbols への紐付け

- kabusys.data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution）と初期化関数 init_schema, get_connection

- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェックの順で差分取得・保存
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult クラスで結果と品質問題を返す

- kabusys.data.calendar_management
  - 営業日判定、前後営業日取得、期間内営業日リスト、夜間 calendar_update_job

- kabusys.data.audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）と初期化関数 init_audit_schema / init_audit_db

- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

---

## 動作要件

- Python 3.10 以上（PEP 604 の型表記などを使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- （任意）J-Quants API 用のネットワーク接続

インストール例（適宜仮想環境を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージとして開発インストールする場合（repo に setup/pyproject がある前提）
pip install -e .
```

---

## 環境変数（重要）

主に以下の環境変数が利用されます（必須は README にて明示）:

必須:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD - kabuステーション等の API パスワード
- SLACK_BOT_TOKEN - Slack 通知用（必要な場合）
- SLACK_CHANNEL_ID - Slack チャンネル ID（必要な場合）

任意/デフォルト付き:
- KABU_API_BASE_URL - デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH - デフォルト: data/kabusys.duckdb
- SQLITE_PATH - デフォルト: data/monitoring.db
- KABUSYS_ENV - development / paper_trading / live（デフォルト development）
- LOG_LEVEL - DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml）を基に
  `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効にするには環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェル風の書式（export を許容、クォート・エスケープ・コメント対応）です。
不足している必須変数を参照すると ValueError が発生します。

例 (.env):
```text
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # もし pyproject.toml を用意しているなら:
   # pip install -e .[dev]
   ```

3. 環境変数を準備
   - プロジェクトルートに `.env` を作成するか、OS の環境変数に設定してください。
   - 必須トークンを必ず設定します（JQUANTS_REFRESH_TOKEN 等）。

4. DuckDB スキーマの初期化
   - Python REPL やスクリプトから以下を実行して DB を作成します。

---

## 使い方（サンプル）

以下は主要な操作の使用例です。エラー処理は省略して簡潔に示します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = init_schema(":memory:")
```

2) 監査ログスキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn, transactional=True)
```

3) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
if result.has_errors:
    # エラー処理
    print("ETL 中にエラーが発生しました:", result.errors)
```

4) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効コード集合（省略可）
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count, ...}
```

5) calendar_update_job（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"保存件数: {saved}")
```

6) J-Quants クライアントの直接利用（トークン取得 / データ取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings から refresh token を使って取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

例: 保存（save_*）関数は DuckDB コネクションと組み合わせて冪等に保存します。

---

## エラーハンドリングとログ

- logger を使って情報・警告・エラーを出力します。LOG_LEVEL 環境変数で制御可能です。
- ETL は「1 ステップ失敗でも他ステップは継続する」設計です。run_daily_etl は ETLResult に errors を蓄積します。
- ニュース収集や API 呼び出しは個別に例外を上げることがあります。運用コード側で try/except を推奨します。

---

## セキュリティ設計（主なポイント）

- news_collector:
  - defusedxml を使った安全な XML パース
  - リダイレクト先・ホスト名の検査でプライベートIPへの到達を防ぐ（SSRF 対策）
  - URL スキームは http/https のみ許可
  - 受信バイト数を上限（10MB）に制限しメモリ DoS を抑止
  - トラッキングパラメータを除去して記事 ID を一意決定

- jquants_client:
  - API レート制限の順守（固定インターバルによるスロットリング）
  - リトライ（408/429/5xx）と指数バックオフ、401 受信時はトークン自動刷新

- DB 側:
  - DDL にチェック制約（CHECK）や NOT NULL、主キーを定義して不正データ混入を抑制

---

## ディレクトリ構成

リポジトリ内の主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント + 保存関数
    - news_collector.py             -- RSS ニュース収集・保存
    - schema.py                     -- DuckDB スキーマ定義・初期化
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        -- カレンダー管理・営業日ロジック
    - audit.py                      -- 監査ログスキーマ / 初期化
    - quality.py                    -- データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は現状の実装ファイル群の一覧です。strategy / execution / monitoring は今後拡張を想定したモジュールです。）

---

## 開発メモ / 注意点

- 型注釈と datetime の扱い:
  - fetch_* で取得する fetched_at は UTC タイムスタンプ（"Z"）として記録されます。
  - DuckDB の日付/時刻は適切に変換されるよう設計されていますが、タイムゾーンの混入に注意してください。

- トランザクション:
  - news_collector の一括挿入や audit.init_audit_schema の transactional オプションなど、一部処理はトランザクションを使います。DuckDB のトランザクションの特性（ネスト不可）を意識してください。

- テスト:
  - コンポーネントは id_token の注入や _urlopen の差し替え等が可能で、単体テストを容易にする設計です。

---

## まとめ

KabuSys は J-Quants を中心とした日本株データ基盤のコア機能群を提供します。  
まずは .env を整備して DuckDB スキーマを初期化し、run_daily_etl / run_news_collection を用いてデータ収集パイプラインを動かすことから始めてください。拡張ポイント（戦略・発注・監視）は strategy / execution / monitoring モジュールを通じて追加していく設計です。

不明点や追加したい操作があれば、どの機能の README を拡充するか具体的に教えてください。