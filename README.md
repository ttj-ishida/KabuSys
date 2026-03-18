# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants API や RSS ニュースを取り込み、DuckDB に保存する ETL・品質チェック・監査用スキーマなどを提供します。

主な用途
- J-Quants から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存
- RSS フィードからニュースを収集して正規化・保存・銘柄紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ用スキーマ（シグナル → 発注 → 約定のトレーサビリティ）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API 例）
- 環境変数
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は、日本株の自動売買プラットフォーム向けに設計されたデータ収集・処理基盤のライブラリ群です。  
主要コンポーネントは次のとおりです。

- data: J-Quants クライアント、RSS ニュース収集、ETL パイプライン、スキーマ初期化、品質チェック、カレンダー管理、監査ログ
- strategy: 戦略モジュール（骨格）
- execution: 発注/ブローカー連携（骨格）
- monitoring: 監視機能（骨格）
- config: 環境変数 / 設定管理（.env の自動ロード機能を含む）

設計のポイント
- J-Quants API のレート制限（120 req/min）やリトライ、トークン自動更新に対応
- DuckDB を用いた冪等なデータ保存（ON CONFLICT を利用）
- RSS 収集は SSRF・XML Bomb 等のセキュリティ対策を実装
- ETL は差分更新・バックフィル・品質チェックを備え監査可能な設計

---

## 機能一覧

主な機能（実装済み）
- J-Quants API クライアント（jquants_client）
  - get_id_token（リフレッシュトークンから id_token を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - rate limiting（120 req/min）、リトライ、401 時の自動リフレッシュ
  - DuckDB に対する冪等保存 save_* 関数
- ニュース収集（news_collector）
  - RSS フィード取得（gzip 対応、最大サイズ制限）
  - URL 正規化、トラッキングパラメータ除去、記事ID（SHA-256先頭32文字）生成
  - SSRF対策（スキーム検証、プライベートIP除外、リダイレクト検査）
  - raw_news / news_symbols への冪等保存（トランザクション、チャンク挿入）
- データスキーマ（schema）
  - Raw / Processed / Feature / Execution / Audit 用の DuckDB テーブル定義
  - init_schema(db_path) で全テーブルとインデックスを作成
- ETL パイプライン（pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl：日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得、backfill、品質チェック統合
- 品質チェック（quality）
  - 欠損データ、スパイク（前日比）、重複、日付不整合検出
  - QualityIssue データクラスで詳細を返却
- カレンダー管理（calendar_management）
  - 営業日判定、前後営業日取得、期間内営業日リスト
  - calendar_update_job による夜間差分更新
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル
  - init_audit_schema / init_audit_db を提供

未実装（スケルトン）
- strategy.*（戦略の具体実装）
- execution.*（ブローカー連携実装）
- monitoring.*（外部監視統合）

---

## セットアップ手順

Python 環境（例）
1. 仮想環境作成・有効化
   - Unix/macOS:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール
   - 最低限必要なパッケージ:
     pip install duckdb defusedxml
   - 他に urllib は標準ライブラリとして利用しています。

   （プロジェクトに requirements.txt があればそれを利用してください。）

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（config モジュールによる自動ロード）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで schema.init_schema() を呼び出してください（後述の使い方参照）。

注意点
- config.Settings で必須となる環境変数が未設定だと ValueError を送出します。
- .env の自動読み込みは .git または pyproject.toml を基準にプロジェクトルートを探索して行われます（カレントディレクトリ依存ではありません）。

---

## 環境変数

重要な環境変数（Settings 経由で参照されます）

必須（ValueError となる）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- KABUSYS uses DB path defaults:
  - DUCKDB_PATH: data/kabusys.duckdb（Settings.duckdb_path）
  - SQLITE_PATH: data/monitoring.db（Settings.sqlite_path）
- KABUSYS (kabuステーション) / API ベース URL:
  - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi

.env サンプル（最低限必要なキーの例）
（実運用では秘密情報を直接コミットしないでください）
KABUSYS_ENV=development
LOG_LEVEL=INFO
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

---

## 使い方（主要 API 例）

以下は基本的な利用例です。適宜 try/except / ログを付与してください。

1) スキーマ初期化（DuckDB）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可
```

2) J-Quants トークン取得 / 株価取得（low-level）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes

id_token = get_id_token()  # settings.jquants_refresh_token を使う
records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,3,31))
saved = save_daily_quotes(conn, records)
```

設計上の注意
- fetch_* 関数は内部でレート制御・リトライ・401 リフレッシュを行います。
- get_id_token は POST でリフレッシュトークンを使って idToken を取得します。

3) ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コード抽出に使うセット（例: DB から取得）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
# results は {source_name: saved_count} の辞書
```

4) 日次 ETL を一括実行
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # デフォルトで今日をターゲットに ETL 実行
print(result.to_dict())
```

run_daily_etl のオプション
- target_date: date オブジェクトで ETL 対象日を指定（省略は今日）
- id_token: テスト用に id_token を注入可能
- run_quality_checks: 品質チェック実行の有無
- spike_threshold, backfill_days, calendar_lookahead_days：挙動調整パラメータ

5) 監査スキーマ初期化（audit）
```python
from kabusys.data.audit import init_audit_db, init_audit_schema

# 独立した監査DBを作る場合:
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

# 既存の conn に監査スキーマだけ追加する場合:
init_audit_schema(conn, transactional=True)
```

---

## 注意事項 / 実装上の詳細

- J-Quants クライアントは 120 req/min のレート制限を守るために固定間隔スロットリングを採用。
- リトライは指数バックオフ（最大 3 回）で実装。HTTP 429 の Retry-After を優先。
- 401 が返ってきた場合は id_token を自動リフレッシュして 1 回リトライする設計。
- news_collector は XML のセキュリティ対策（defusedxml）や SSRF 対策（スキーム検証・プライベートIPチェック）を実施。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）を保つ。
- quality モジュールは ETL 後のデータ品質を検査し、問題を QualityIssue のリストで返す（fail-fast ではなく一覧収集）。

---

## ディレクトリ構成

リポジトリの主要ファイル / ディレクトリ（抜粋）

src/
  kabusys/
    __init__.py
    config.py                      # 環境設定・.env 自動ロード
    data/
      __init__.py
      jquants_client.py            # J-Quants API クライアント（取得・保存）
      news_collector.py            # RSS ニュース収集・正規化・保存
      pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      calendar_management.py       # マーケットカレンダー関連ユーティリティ
      schema.py                    # DuckDB スキーマ定義・初期化
      audit.py                     # 監査ログスキーマ
      quality.py                   # データ品質チェック
    strategy/
      __init__.py                  # 戦略用モジュール（拡張ポイント）
    execution/
      __init__.py                  # 発注/ブローカー連携（拡張ポイント）
    monitoring/
      __init__.py                  # 監視用（拡張ポイント）

---

この README はコードベースの主要機能と利用方法をまとめたものです。  
プロジェクトの拡張点（strategy / execution / monitoring）や運用上のルール（.env の取り扱い、機密情報の管理、DB バックアップなど）は、実環境導入時に社内運用手順に合わせて追記してください。質問やサンプルスクリプトが必要であればお知らせください。