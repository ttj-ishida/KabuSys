# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
Data 層（DuckDB ベース）、Research 層（ファクター計算・IC 評価）、ETL / ニュース収集、監査ログなどを含む汎用コンポーネント群を提供します。

---

## 特徴（概要）

- J-Quants API からのデータ取得（株価日足・財務データ・市場カレンダー）をサポート
  - レート制限対応、リトライ、トークン自動リフレッシュ、ページネーション対応
- DuckDB を用いた三層データモデル（Raw / Processed / Feature）とスキーマ初期化機能
- 日次 ETL パイプライン（差分取得・バックフィル、品質チェック）
- ニュース収集（RSS）と記事→銘柄紐付け（正規化・SSRF 対策・Gzip 制限等）
- Research 用のファクター計算（Momentum / Volatility / Value）と特徴量解析ツール
  - 将来リターン算出、IC（Spearman）計算、統計サマリー、Z スコア正規化
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ
- 環境変数ベースの設定（.env 自動ロード機能、優先順位: OS 環境 > .env.local > .env）

---

## 機能一覧（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート判定）
  - settings（J-Quants / kabuステーション / Slack / DB パス / 環境等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存ユーティリティ）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline / etl: ETL 実装（run_daily_etl 等）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - quality: 品質チェック（missing / spike / duplicates / date consistency）
  - calendar_management: market_calendar 管理・営業日判定ロジック
  - audit: 監査ログ用テーブル群と初期化ユーティリティ
  - stats / features: Z スコア正規化などの統計ユーティリティ
- kabusys.research
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
  - factor_research: Momentum / Volatility / Value の計算関数
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - パッケージ初期化済み（実装はプロジェクト固有で拡張）

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションで | Union 構文を使用）
- OS により DuckDB のビルドに依存する追加パッケージが必要になる場合があります（通常は不要）

1. リポジトリをクローン
   git clone <repository-url>
   cd <repository-root>

2. 仮想環境の作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb defusedxml

   ※プロジェクト内に requirements.txt があればそれを使用してください。

4. 環境変数の設定
   必須:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注等で使用）
   - SLACK_BOT_TOKEN       : Slack ボットトークン（通知用）
   - SLACK_CHANNEL_ID      : Slack チャネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV           : development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite 監視DBパス（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化する場合に 1 を設定

   例 (.env):
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development

   自動ロードの挙動:
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に .env/.env.local を自動読み込みします。
   - 優先順位: OS 環境 > .env.local > .env
   - テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（基本例）

以下はライブラリをインポートして実行する最小例です。実際の運用ではログ設定やエラーハンドリングを追加してください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数から取得される（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 市場カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

4) ニュース収集（RSS を既定ソースで実行）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes に銘柄コード集合を渡すと記事と銘柄の紐付けを行う
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

5) ファクター計算 / 研究系ユーティリティ
```python
from kabusys.research import (
    calc_momentum, calc_volatility, calc_value,
    calc_forward_returns, calc_ic, factor_summary, rank
)
from kabusys.data.stats import zscore_normalize
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)

# 将来リターンを計算して IC を求める例
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

6) J-Quants API の直接利用（トークン取得・データ取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使用
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ディレクトリ構成（概要）

プロジェクト主要ファイル（src/kabusys）:
- kabusys/
  - __init__.py
  - config.py                        -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py               -- RSS 取得・前処理・DB 保存
    - schema.py                       -- DuckDB スキーマ定義と init_schema
    - pipeline.py                     -- ETL パイプライン（差分取得等）
    - etl.py                          -- ETL 結果型の公開インターフェース
    - features.py                     -- features インターフェース（zscore 再エクスポート）
    - stats.py                        -- 統計ユーティリティ（zscore_normalize）
    - quality.py                      -- データ品質チェック
    - calendar_management.py          -- カレンダー管理（営業日判定等）
    - audit.py                         -- 監査ログテーブルの初期化
    - audit (関連機能等)
  - research/
    - __init__.py
    - feature_exploration.py          -- 将来リターン / IC / summary
    - factor_research.py              -- Momentum / Volatility / Value
  - strategy/
    - __init__.py                     -- 戦略層（拡張ポイント）
  - execution/
    - __init__.py                     -- 実行 / 発注層（拡張ポイント）
  - monitoring/
    - __init__.py                     -- 監視（拡張ポイント）

---

## 注意事項 / 運用上のポイント

- 環境（KABUSYS_ENV）は production（live）・paper_trading・development を切り替え可能。live 環境での発注は十分注意して運用してください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に保存されます。バックアップや権限管理を行ってください。
- J-Quants API のレート制限（120 req/min）に従って実装されていますが、大量の並列リクエストは避けてください。
- news_collector は外部 RSS を扱うため、SSRF 対策とレスポンスサイズ制限を実装しています。設定変更する場合はセキュリティに注意してください。
- ETL の品質チェックは fail-fast ではなく、検出した問題を返して呼び出し側で判断する設計です。自動停止/アラート運用を行う場合は result.has_quality_errors を参照してください。
- この README はコードベースの主要機能をまとめたものです。個別の API（関数）の詳細は該当モジュールの docstring を参照してください。

---

貢献・拡張
- Strategy / Execution / Monitoring 層はプロジェクト毎に拡張して利用してください。  
- バグ報告・機能要望はリポジトリの issue をご利用ください。