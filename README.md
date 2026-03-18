# KabuSys

日本株向けの自動売買システム用ライブラリ（内部モジュール群）のリポジトリ。  
データ取得（J-Quants）、DuckDBベースのデータスキーマ・ETL、ニュース収集、ファクター計算、品質チェック、監査ログなどを含むモジュール群を提供します。

## 概要
KabuSys は以下の目的で設計されています：
- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- RSS ベースのニュース収集と銘柄紐付け
- データ品質チェック（欠損、スパイク、重複、日付不整合など）
- 研究用途のファクター計算（モメンタム／ボラティリティ／バリュー等）および IC 計測
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 発注/監査のためのスキーマ（audit テーブル群）設計（監査ログの初期化ユーティリティあり）

設計上の特徴：
- DuckDB を中心としたローカル DB（:memory: も可）
- J-Quants のレート制限・リトライ・トークンリフレッシュを考慮したクライアント
- 外部依存を極力減らし標準ライブラリベースの実装（ただし duckdb, defusedxml 等は必須）
- 本番口座への発注処理は別モジュール（execution）に委ね、データ収集／解析は発注と独立

## 機能一覧（主要機能）
- 環境変数／設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）、必須環境変数取得ユーティリティ
- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミット、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB へ冪等保存する save_* 関数
- スキーマ初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) で DB を初期化
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー / 株価 / 財務 の差分取得と品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF対策、gzip処理、XML パースの防御）
  - 記事正規化・ID生成・raw_news への冪等保存・銘柄抽出と news_symbols への紐付け
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合を検出し QualityIssue を返す
  - run_all_checks でまとめて実行
- 研究用ファクター（kabusys.research）
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）で標準化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査スキーマと初期化ユーティリティ
- その他ユーティリティ
  - カレンダー管理（is_trading_day 等）
  - 統計ユーティリティ（zscore_normalize）

## 必須環境変数
（kabusys.config.Settings が参照します。未設定時は ValueError を送出します）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注連携時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意／デフォルトあり：
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env 自動ロード:
- プロジェクトルート（.git または pyproject.toml を親側に探索）を起点に .env を自動読み込みします。
- 読み込み順: OS env > .env.local > .env
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの | や他機能を使用）
- Git, インターネット接続（J-Quants などを利用する場合）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （開発時）pip install -e .

   必要に応じてその他ライブラリを追加してください（例えば requests 等は本コード内で使用していません）。

4. 環境変数設定
   - .env.example があればそれを参考にプロジェクトルートに .env を作成してください。
   - 必須トークン等を .env に記述（または OS 環境変数として設定）

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - メモリ DB を使う場合:
     conn = init_schema(":memory:")

6. 監査ログDB の初期化（必要な場合）
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

## 使い方（主要ユースケース例）

以下は最小限のサンプルコード例です。

- DuckDB を初期化して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
# または既存 DB へ
# conn = get_connection("data/kabusys.duckdb")

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- ファクター計算（モメンタム）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2025,1,31))
# 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- 将来リターン計算と IC（相関）計算
```python
from datetime import date
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2025,1,31), horizons=[1,5,21])
# factor_records は calc_momentum 等の出力
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- J-Quants から株価取得のみ行いたい場合
```python
from kabusys.data import jquants_client as jq
from datetime import date

rows = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
# DuckDB へ保存:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
jq.save_daily_quotes(conn, rows)
```

注意:
- run_daily_etl は各ステップで失敗しても他ステップを継続する設計です。結果の ETLResult.errors を確認してください。
- jquants_client は API レートや 401 エラーに対処しますが、実運用ではトークン管理や監視を行ってください。

## 開発者向けメモ
- .env 自動ロードの挙動は kabusys.config モジュール参照（プロジェクトルート検出・.env, .env.local 読込・OS 環境変数保護など）
- NewsCollector は SSRF 対策や受信サイズ制限、XML パースの防御（defusedxml）を行っています。テストでは fetch 関連の I/O をモック可能です（内部で _urlopen を使用）。
- DuckDB に対する INSERT は多くが ON CONFLICT DO UPDATE / DO NOTHING を使い冪等化されています。
- 監査ログ初期化時に TimeZone を UTC に固定します（init_audit_schema）。

## ディレクトリ構成（抜粋）
（リポジトリの src/kabusys 以下を示します）

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（取得 + 保存）
    - news_collector.py                 — RSS 収集・正規化・保存
    - schema.py                         — DuckDB スキーマ定義と init_schema
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - features.py                       — features エクスポート（zscore）
    - stats.py                          — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py            — market_calendar 管理・ユーティリティ
    - audit.py                          — 監査ログスキーマ初期化
    - etl.py                            — ETL インタフェース再エクスポート
    - quality.py                        — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py                — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py            — 将来リターン・IC・summary 等
  - strategy/
    - __init__.py                       — 戦略層（空のパッケージ・拡張想定）
  - execution/
    - __init__.py                       — 発注層（空のパッケージ・拡張想定）
  - monitoring/
    - __init__.py                       — 監視・アラート等（拡張想定）

（上記のうち空 __init__ はパッケージ構成用で、必要な実装は今後追加される想定です）

## 注意事項 / 安全性
- 本ライブラリの多くはデータ取得・解析に関するコードであり、発注（実際の売買）は別モジュールに委ねる設計です。発注系を実装する際は安全策（paper_trading フラグ、リスク管理、冪等キー、監査ログ）を必ず実装してください。
- ニュース収集は外部 URL を扱うため SSRF / XML Bomb / 大容量レスポンスに対する防御を実装済みですが、運用環境での追加制約（プロキシ、内部ネットワーク制限など）を検討してください。
- J-Quants API 利用時の利用規約・レート制限を必ず遵守してください。

---

README に記載したサンプルは最小限の例です。各モジュールの docstring に詳細な設計意図・引数仕様・戻り値の説明がありますので、実装や運用の際には該当ソースを参照してください。必要であれば README に追加の使い方（CLI 例、Docker 構成、CI 用フロー等）を追記します。