# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ群）

このリポジトリは、データ取得（J-Quants）、DuckDB によるデータ格納、データ品質チェック、特徴量計算（ファクター）、ニュース収集、ETL パイプライン、監査ログ等を含む日本株自動売買システムのコアコンポーネント群を提供します。戦略・発注・モニタリングの基盤として利用できるモジュールを含みます。

---

## 主な機能

- 環境変数 / 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）および必須キーの検査
  - 自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- データ取得（J-Quants API クライアント）
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）管理、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得データを DuckDB に冪等保存するユーティリティ

- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス、監査ログ用スキーマの初期化機能

- ETL パイプライン
  - 差分取得（バックフィル対応）、保存、品質チェックの一括実行（run_daily_etl）
  - ETL 結果を表す ETLResult 型

- データ品質チェック
  - 欠損、重複、スパイク（急変）、日付不整合（未来日付や非営業日データ）検出
  - 問題は QualityIssue として収集・返却

- 研究用 / ファクター計算（research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

- ニュース収集
  - RSS フィードから記事収集、前処理、DuckDB への冪等保存（raw_news, news_symbols）
  - URL 正規化（トラッキングパラメータ除去）、SSRF 対策、サイズ上限、XML 脆弱性対策

- 監査ログ（audit）
  - signal → order_request → execution までのトレーサビリティを保持するスキーマ

---

## 必要条件

- Python 3.10+
  - 型注釈で union 型（|）を使用しているため Python 3.10 以上を想定しています。
- 依存パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```
pip install duckdb defusedxml
```

（プロジェクトで配布する pyproject.toml / requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
4. 環境変数を準備
   - プロジェクトルートに `.env`（必要な変数）を配置できます。自動で `.env` → `.env.local` の順に読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須の環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

オプション:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

ヒント: .env.example を参照して .env ファイルを作成してください（リポジトリにある場合）。

---

## 使い方（クイックスタート）

以下は代表的な利用例です。詳細は各モジュールの docstring を参照してください。

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # :memory: も可
```

2) 監査DB初期化（監査ログ専用）
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行（市場カレンダー、日足、財務、品質チェック）
```
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) ファクター計算（例: Momentum）
```
from datetime import date
from kabusys.research import calc_momentum
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024, 1, 31))
# records は {date, code, mom_1m, mom_3m, mom_6m, ma200_dev} の dict リスト
```

5) 将来リターンと IC 計算
```
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024, 1, 31), horizons=[1,5])
# factor_records は別途 calc_momentum 等で得たリスト
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

6) ニュース収集ジョブ
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

---

## 環境変数の自動読み込みの挙動

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索し、以下の順で .env を読み込みます:
  1. OS 環境変数（既存値は保護される）
  2. .env （未設定キーのみセット）
  3. .env.local（既存キーを上書き可能。ただし OS 環境変数は保護）

- 自動読み込みを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

- 必須キー取得時に未設定だと ValueError が上がります（Settings クラス経由でアクセスされるプロパティが対象）。

---

## 主要モジュール（概観）

- kabusys.config
  - Settings: 環境設定の取得（tokens, DB パス, env 判定等）
- kabusys.data
  - jquants_client: J-Quants API クライアント、取得・保存ユーティリティ
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: ETL の実行（run_daily_etl 等）
  - quality: データ品質チェック
  - news_collector: RSS 取得・前処理・保存ロジック
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログスキーマの初期化
  - calendar_management: 営業日判定、カレンダーの更新ジョブ
- kabusys.research
  - factor_research: ファクター計算（momentum, volatility, value）
  - feature_exploration: 将来リターン、IC、統計サマリー等
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - 戦略・発注・監視向けの名前空間（実装を拡張するためのフォルダ）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - quality.py
      - calendar_management.py
      - audit.py
      - etl.py
      - features.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

---

## 開発・貢献メモ

- DuckDB に対する DDL は冪等（CREATE TABLE IF NOT EXISTS）で記述されています。初回は init_schema() を使って DB を作成してください。
- J-Quants API にはレート制限とリトライが組み込まれていますが、大量取得の際はモジュールの _MIN_INTERVAL_SEC 等の設定を尊重してください。
- ニュース収集では RSS の XML パース時に defusedxml を利用しているため、外部からの悪意ある XML による攻撃緩和が行われます。
- 監査ログは UTC タイムスタンプを前提としています（init_audit_schema() は TimeZone='UTC' を設定します）。

---

## 参考

- 各モジュールの詳細はソース内の docstring を参照してください。関数・クラスレベルで想定される入力・戻り値、エラー条件、設計方針が記載されています。
- 環境変数の必須項目は kabusys.config.Settings のプロパティで確認できます。

---

お問い合わせやバグ報告、機能追加の提案はリポジトリの Issue をご利用ください。