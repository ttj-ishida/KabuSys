# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants API や RSS フィード等からデータを収集・保存し、ETL、データ品質チェック、マーケットカレンダー管理、監査ログなどを提供します。戦略・実行・監視層と連携するための基盤コンポーネント群を含みます。

## 特徴（概要 / 機能一覧）
- J-Quants API クライアント（jquants_client）
  - 株価日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）に準拠する RateLimiter
  - 再試行（指数バックオフ、最大3回）、401 の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアス対策
  - DuckDB へ冪等的に保存（ON CONFLICT ... DO UPDATE）
- ニュース収集（news_collector）
  - RSS フィードから記事収集、前処理、DuckDB への冪等保存
  - URL 正規化、トラッキングパラメータ除去、記事ID は正規化 URL の SHA-256（先頭32文字）
  - defusedxml を使った安全な XML パース、SSRF 対策、レスポンスサイズ制限
  - 記事と銘柄コードの紐付け機能（news_symbols）
- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義、外部キーを考慮した作成順
- ETL パイプライン（data.pipeline）
  - 差分更新（最終取得日から不足分のみ取得）、バックフィルオプション
  - カレンダー取得 → 株価取得 → 財務取得 → 品質チェック（quality）
  - ETL 結果の集約（ETLResult）
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - 夜間バッチでのカレンダー差分更新ジョブ（calendar_update_job）
- データ品質チェック（data.quality）
  - 欠損、スパイク（前日比）、主キー重複、日付不整合の検出
  - 各チェックは QualityIssue を返す（error / warning）
- 監査ログ（data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル群
  - 発注要求は冪等キー（order_request_id）を持ち、履歴を完全に記録

## 必要条件
- Python 3.10 以上（型注釈の | 演算子を使用）
- 依存パッケージ（一例）
  - duckdb
  - defusedxml

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# その他、プロジェクトで必要なライブラリを追加してください
```

※ このリポジトリに setup.py / pyproject.toml がある場合は pip install -e . してください。

## 環境変数（主な設定項目）
KabuSys は .env / .env.local または環境変数から設定を読み込みます（自動ロード）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings クラスで _require() されるもの）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API パスワード
- SLACK_BOT_TOKEN : Slack ボットトークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意（デフォルトあり）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : environment（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

## セットアップ手順（手順例）
1. リポジトリをクローン、仮想環境を作成して依存をインストール
2. .env をプロジェクトルートに作成（.env.example を参照。存在しない場合は上記の必須項目を設定）
3. DuckDB スキーマ初期化
   - Python スクリプト / REPL で以下を実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # デフォルトのパスと同じ
     ```
   - 監査ログ用（別 DB を使う場合）:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```
4. （任意）監視 DB（SQLite）が必要なら設定に従って作成

## 使い方（主要 API の例）
以下はライブラリを直接使う最小例です。実際の運用ではスクリプトやジョブに組み込んでください。

- 設定参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- J-Quants トークン取得
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
```

- DuckDB スキーマ初期化（再掲）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得＋品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は既知の銘柄コード集合（抽出フィルタ）
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

- 監査スキーマの追加（既存接続へ）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)  # conn は schema.init_schema の戻り値
```

## ディレクトリ構成（主要ファイル）
プロジェクトのルートに src/ を置く構成になっています。主要モジュールを抜粋すると:

- src/kabusys/
  - __init__.py
  - config.py                   # 環境変数・設定読み込み
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py         # RSS ニュース収集・保存（SSRF 対策等）
    - schema.py                 # DuckDB スキーマ定義・初期化
    - pipeline.py               # ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py    # カレンダー管理 / 営業日ロジック
    - audit.py                  # 監査ログスキーマ（シグナル→発注→約定の追跡）
    - quality.py                # データ品質チェック
  - strategy/
    - __init__.py               # 戦略層（拡張ポイント）
  - execution/
    - __init__.py               # 発注・約定処理（拡張ポイント）
  - monitoring/
    - __init__.py               # 監視用コンポーネント（拡張ポイント）

この README では主要なデータ収集・ETL・品質・監査機能に焦点を当てています。strategy / execution / monitoring パッケージは拡張ポイントとして用意されており、プロジェクトの運用に合わせて実装を追加してください。

## 設計上の留意点（短く）
- J-Quants API はレート制限とリトライロジックを備えていますが、運用スクリプト側でも呼び出し頻度に注意してください。
- ニュース取得では SSRF・XML Bomb・大容量レスポンス対策が組み込まれています。外部フィードを追加する際も安全性を考慮してください。
- DuckDB の初期化は冪等（既存テーブルはスキップ）です。監査テーブルは init_audit_schema() で追加できます。

---

追加で README に書きたい内容（例: CI、テスト、デプロイ方法、.env.example、サンプルジョブスケジューラ設定）があれば、その情報を教えてください。README をその内容で拡張して作成します。