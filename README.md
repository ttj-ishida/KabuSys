# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のリポジトリ向け README.md（日本語）。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件・セットアップ手順
- 環境変数（.env）と設定
- 使い方（代表的な操作例）
  - DuckDB スキーマ初期化
  - 日次 ETL 実行
  - RSS ニュース収集
  - 監査ログ（Audit DB）初期化
  - 研究用ファクター計算
  - カレンダー関連ユーティリティ
- ディレクトリ構成
- ライセンス・注意事項

---

プロジェクト概要
----------------
KabuSys は日本株の自動売買システム構築を支援する Python モジュール群です。
主に以下の機能を提供します。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB を用いたデータスキーマ定義・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース（RSS）収集・前処理・銘柄紐付け
- ファクター計算（Momentum / Volatility / Value 等）と研究ユーティリティ（IC, forward returns, summary）
- 監査ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計方針の一部：
- 外部依存を最小化（標準ライブラリと必要な数ライブラリに留める）
- DuckDB を中心とした冪等な保存（ON CONFLICT を活用）
- API レート制御・リトライ・トークン自動更新（J-Quants クライアント）
- Look-ahead bias を防ぐため fetched_at を記録

主な機能一覧
-------------
- data.jquants_client: J-Quants API 統合クライアント（ページネーション、リトライ、レート制御、保存ユーティリティ）
- data.schema: DuckDB のテーブル定義と初期化（Raw / Processed / Feature / Execution）
- data.pipeline: 日次 ETL（差分取得、バックフィル、品質チェック）
- data.news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
- data.calendar_management: 市場カレンダーの取得・営業日判定ユーティリティ
- data.quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
- data.audit: 監査ログ用スキーマ（signal_events, order_requests, executions 等）
- data.stats / research.*: ファクター計算、IC 計算、Z スコア正規化等の研究ユーティリティ

必要条件・セットアップ手順
------------------------
前提
- Python 3.9+（型ヒントに Union 並びに | が多く使用されています）
- pip

推奨パッケージ（最低限）
- duckdb
- defusedxml

インストール（開発環境向け例）
1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

3. （任意）パッケージとしてローカルインストール
   - pip install -e .

（注意）requirements.txt は本リポジトリに含まれていない想定のため、上記の必要パッケージを手動でインストールしてください。

環境変数（.env）と設定
---------------------
KabuSys は .env ファイルまたは OS 環境変数から設定を読み込みます（プロジェクトルートに .env/.env.local があれば自動ロード）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用）。

必須環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード（発注モジュール用）
- SLACK_BOT_TOKEN: Slack 通知用 bot token
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.example (.env.example) の例
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

使い方（代表例）
----------------

基本：設定を読み込んで DuckDB を初期化し、ETL を実行する簡単な流れを示します。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data import schema

# settings.duckdb_path は Path を返します
conn = schema.init_schema(settings.duckdb_path)
# 以降 conn を ETL や各種ユーティリティに渡して使用します
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日を基準に実行
print(result.to_dict())
```
run_daily_etl は market_calendar / prices / financials の差分取得と品質チェックを順に実行し、ETLResult を返します。

3) RSS ニュース収集（run_news_collection）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes がある場合は銘柄抽出して news_symbols を作成する
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

4) 監査ログ（Audit DB）初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または ":memory:" でインメモリDB
```

5) 研究用ファクター計算（例）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize

d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# 将来リターン計算（翌日/翌週等）
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])

# IC（スピアマンランク相関）
# factor_records と forward_records を code ベースで join して使用
ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")

# Z スコア正規化
normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

6) カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

d = date(2024, 02, 01)
is_trading = is_trading_day(conn, d)
next_td = next_trading_day(conn, d)
days = get_trading_days(conn, date(2024,1,1), date(2024,1,31))
```

主要 API 説明（抜粋）
- kabusys.config.settings: 環境変数ベースの設定アクセス（例: settings.jquants_refresh_token）
- kabusys.data.jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（トークン更新）
- kabusys.data.schema:
  - init_schema(db_path): DuckDB スキーマの初期化と接続返却
  - get_connection(db_path): 既存 DB への接続
- kabusys.data.pipeline:
  - run_daily_etl(conn, target_date=None, ...): 日次 ETL 実行
- kabusys.data.news_collector:
  - fetch_rss(url, source, timeout)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.research:
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- kabusys.data.quality:
  - run_all_checks(conn, target_date=None, reference_date=None)

ディレクトリ構成
----------------
主要ファイル・パッケージ（src/kabusys 以下の抜粋）

- kabusys/
  - __init__.py (パッケージメタ: __version__ = "0.1.0")
  - config.py (環境変数 / 設定読み込みロジック)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント)
    - news_collector.py (RSS ニュース収集)
    - schema.py (DuckDB スキーマ定義・init_schema)
    - pipeline.py (ETL パイプライン)
    - features.py (特徴量ユーティリティ公開)
    - calendar_management.py (マーケットカレンダー管理)
    - audit.py (監査ログスキーマ)
    - etl.py (公開型再エクスポート: ETLResult)
    - quality.py (データ品質チェック)
    - stats.py (zscore_normalize 等)
  - research/
    - __init__.py (公開 API)
    - feature_exploration.py (forward returns / IC / summary 等)
    - factor_research.py (momentum/value/volatility 計算)
  - strategy/ (戦略実装用パッケージ：空の __init__.py から拡張)
  - execution/ (発注・ブローカー連携用パッケージ：空の __init__.py から拡張)
  - monitoring/ (監視用コード等：空の __init__.py から拡張)

開発上の注意・ベストプラクティス
-------------------------------
- 実際の発注（live）モードでは十分な安全策（手動レビュー、paper_trading での検証、通知）を行ってください。
- 環境変数やシークレットは CI/CD で安全に管理してください（.env ファイルをリポジトリに含めないこと）。
- DuckDB のファイルはバックアップや移行に注意（:memory: は一時用途のみ）。
- J-Quants API 使用時はレート制限やトークン管理に注意（ライブラリ側で対応済みですが、運用量に応じた監視推奨）。
- news_collector は外部 URL を取得するため SSRF/サイズ/圧縮など複数の防御を実装していますが、運用時のネットワークポリシーも検討してください。

ライセンス・免責
----------------
本 README はコードベースの説明資料です。実運用に際しては各自の責任において十分なテストとレビューを行ってください。外部 API 利用規約（J-Quants など）を遵守してください。

---

追加で必要な情報（例）
- requirements.txt を用意する場合は最低限 duckdb, defusedxml を含めると良いでしょう。
- CI における DB ファイルや .env の取り扱い方（モック・テスト用変数）についてガイドを書き加えることを推奨します。

質問や README に追加したい具体的な項目（例: サンプル .env.example ファイルをプロジェクトルートに置く、CLI ラッパーの使い方等）があれば教えてください。README をその要件に合わせて追記します。