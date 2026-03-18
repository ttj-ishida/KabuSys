# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータ層に用い、J-Quants からの時系列・財務データ取得、RSS ニュース収集、データ品質チェック、特徴量計算、ETL パイプライン、監査ログ（発注トレーサビリティ）などを提供します。

## 主要な目的
- J-Quants API から株価・財務・カレンダーを取得して DuckDB に蓄積する
- RSS からニュースを収集し記事と銘柄の紐付けを行う
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量探索（将来リターン・IC など）
- 発注・監査ログ周りのスキーマ（audit）を提供

---

## 機能一覧（主なモジュール）
- kabusys.config
  - .env / 環境変数管理、自動読み込み（.env, .env.local）
  - 必須設定の取得（J-Quants トークン等）
- kabusys.data.jquants_client
  - J-Quants API クライアント（ページネーション、リトライ、RateLimiter、token refresh）
  - fetch/save 系：日足（daily_quotes）、財務（statements）、market_calendar
- kabusys.data.news_collector
  - RSS 取得（SSRF 対策、gzip 制限、XML 安全パース）、記事正規化、DuckDB への冪等保存
  - 銘柄コード抽出と news_symbols への紐付け
- kabusys.data.schema / audit
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_schema, init_audit_db 等の初期化関数
- kabusys.data.pipeline / etl
  - 差分 ETL（prices / financials / market calendar）と日次統合 run_daily_etl
  - バックフィル、quality チェック統合
- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合のチェック（QualityIssue を返す）
- kabusys.data.stats, data.features
  - z-score 正規化等の統計ユーティリティ
- kabusys.research.factor_research / feature_exploration
  - ファクター計算（mom, volatility, value など）
  - 将来リターン計算、IC（Spearman）算出、ファクター統計サマリ
- kabusys.data.calendar_management
  - market_calendar 管理、営業日判定、next/prev_trading_day 等のユーティリティ

---

## セットアップ手順（開発用）

1. リポジトリをクローン
   - 例: git clone <リポジトリ>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 必須（本コード参照）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

4. 環境変数 / .env を準備
   - プロジェクトルートの .env または .env.local を作成すると、自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限設定すべき変数（使用する機能に応じて）:
     - JQUANTS_REFRESH_TOKEN (必須：J-Quants リフレッシュトークン)
     - SLACK_BOT_TOKEN (Slack 通知を使う場合)
     - SLACK_CHANNEL_ID
     - KABU_API_PASSWORD (kabu ステーション API を使う場合)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルトは development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

---

## 使い方（代表的な操作例）

以下はライブラリ関数を直接呼ぶ Python スクリプト例です。実行前に環境変数と依存ライブラリを整えてください。

1) DuckDB スキーマ初期化（データベース作成）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
# 必要に応じて監査スキーマを追加
from kabusys.data import audit
audit.init_audit_schema(conn)
```

2) 監査専用 DB 初期化
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

3) 日次 ETL を実行する（J-Quants から差分取得して保存、品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使用する有効コードの集合（任意）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

5) ファクター計算 / 研究用関数の呼び出し
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
# 特徴量正規化
from kabusys.data.stats import zscore_normalize
features = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

6) 将来リターン・IC 計算
```python
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
# factor_records は calc_momentum 等の結果
ic = calc_ic(factor_records=some_factors, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
```

---

## 注意点 / 設計上の重要事項
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml の存在）を基に .env/.env.local を自動ロードします。
  - テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境モード:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかで、運用モードの判断に使用されます。
- J-Quants API:
  - Rate limit（120 req/min）を踏まえたクライアント実装が含まれています。ID トークンは自動更新されます。
- DuckDB の接続管理:
  - init_schema は必要なテーブルをすべて作成します（冪等）。既存接続には init_audit_schema で監査スキーマを追加可能です。
- セキュリティ / 安全対策:
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml を用いた安全な XML パースを行っています。
  - jquants_client は 401 時の自動トークンリフレッシュ・リトライロジックを備えています。

---

## ディレクトリ構成（主要ファイル）
（実際の repo と若干差異があるかもしれませんが、本コードベースに基づく概観）

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
      - news_collector.py
      - schema.py
      - pipeline.py
      - etl.py
      - quality.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py

---

## よくある運用ワークフロー例
- 夜間バッチ（Cron / Airflow 等）
  1. 仮想環境へ入る
  2. Python スクリプトで schema.init_schema を呼んで DB を準備（初回のみ）
  3. daily ETL を run_daily_etl（market_calendar → prices → financials → quality）
  4. news_collector.run_news_collection を実行
  5. 研究用に features を計算・保存、戦略に渡してシグナル生成
  6. 発注処理（実運用時は監査テーブルへ書き込む流れを実装）

---

## 開発・拡張のヒント
- strategy / execution モジュールは拡張ポイントです。signal → order_request → executions のフローに沿って実装してください。
- DuckDB のスキーマは DataPlatform.md / StrategyModel.md を想定して設計されています。マイグレーションは既存テーブルとの互換性に注意してください。
- テスト容易性のため、多くの関数は id_token 注入や接続注入が可能です（ユニットテストで外部 API をモックしやすい設計）。

---

もし README に追加したい「サンプルスクリプト」「CI 実行手順」「より詳細な環境変数一覧（.env.example）」などがあれば、用途に合わせて追記します。どの部分を詳しく書きたいか教えてください。