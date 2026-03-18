# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB をベースにしたデータレイク、J-Quants からのデータ取得（株価・財務・市場カレンダー）、RSS ニュース収集、特徴量計算、ETL パイプライン、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的に適したモジュール群を含みます。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたスキーマ定義と冪等保存（ON CONFLICT）
- RSS からのニュース収集と記事→銘柄紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター/特徴量計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → execution のトレース）
- 環境変数 / .env の自動読み込み（プロジェクトルート検出）

設計上の方針として、本番口座や発注 API に直接アクセスしないモジュール（research / data 等）と、発注・実行に関するスキーマ／監査ログを分離しています。研究用の関数は外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装されています。

---

## 主な機能一覧

- 環境設定読み込み・検証（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可）
  - 必須環境変数チェック
- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足・財務・市場カレンダーの取得（ページネーション対応）
  - レート制御（120 req/min）
  - リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（save_*）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - init_schema(), get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(): カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 個別ジョブ run_prices_etl/run_financials_etl/run_calendar_etl
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
  - QualityIssue 型で検出結果を返す
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策、gzip 制限、XML 安全パース）
  - raw_news への冪等保存、news_symbols への銘柄紐付け
- ファクター計算（kabusys.research.factor_research）
  - モメンタム、ボラティリティ、バリュー等の計算（prices_daily / raw_financials を参照）
  - 研究用補助関数（forward returns / IC / summary）も提供
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（Zスコア正規化）

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.9+（ソース上は型アノテーションに 3.8+ 機能を使用）
2. 依存パッケージのインストール
   - 最小限:
     - duckdb
     - defusedxml
   - 例:
     pip install duckdb defusedxml
3. プロジェクトを開発モードでインストール（任意）
   - 例（プロジェクトルートで）:
     pip install -e .
   - （パッケージ化されていない場合は直接 PYTHONPATH にソースを含めて利用可能）
4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に .env / .env.local を置くと自動で読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（kabusys.config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabu ステーション API のパスワード（発注系を利用する場合）
     - SLACK_BOT_TOKEN : Slack 通知を使う場合
     - SLACK_CHANNEL_ID : Slack 通知先チャンネル
   - 任意:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視 DB などに使う SQLite パス（デフォルト: data/monitoring.db）

例 .env (参考)
```env
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は代表的な利用例です。詳細は各モジュールの docstring を参照してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使って ETL / 解析を実行
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

- RSS フィード取得・保存（ニュース収集）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 抽出対象の有効な銘柄コードセットを渡すと銘柄紐付けを行う
results = run_news_collection(conn, known_codes={"7203","6758","9984"})
print(results)
```

- ファクター計算（研究用）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
# zscore_normalize は kabusys.data.stats.zscore_normalize
```

- J-Quants から日足を直接取得（ページネーション対応）
```python
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 環境設定の参照
```python
from kabusys.config import settings

print(settings.duckdb_path)       # Path オブジェクト
print(settings.is_live)          # ブール
token = settings.jquants_refresh_token  # 必須、未設定なら ValueError
```

注意: research モジュールの関数は DuckDB 上のテーブル（prices_daily, raw_financials 等）を参照し、本番口座や発注 API にはアクセスしません。

---

## 主要モジュールと API（抜粋）

- kabusys.config
  - settings: Settings インスタンス（環境変数取得・検証）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token（トークン取得）
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, ...), run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news, run_news_collection, extract_stock_codes
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.quality
  - run_all_checks(conn, ...), QualityIssue 型

---

## ディレクトリ構成

以下はソースツリーの要約です（主要ファイルのみ抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                # 発注・実行関連（パッケージ空ディレクトリ）
    - strategy/                 # 戦略関連（パッケージ空ディレクトリ）
    - monitoring/               # 監視関連（パッケージ空ディレクトリ）
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント + 保存ユーティリティ
      - news_collector.py       # RSS 収集・保存
      - schema.py               # DuckDB スキーマ定義・初期化
      - stats.py                # 統計ユーティリティ (zscore_normalize)
      - pipeline.py             # ETL パイプライン
      - features.py             # features の再エクスポート
      - calendar_management.py  # カレンダー管理ユーティリティ
      - audit.py                # 監査ログ（発注〜約定トレース）初期化
      - etl.py                  # ETLResult の再エクスポート
      - quality.py              # 品質チェック
    - research/
      - __init__.py
      - feature_exploration.py  # 将来リターン・IC・summary 等
      - factor_research.py      # モメンタム/ボラティリティ/バリュー計算

---

## 運用上の注意点 / ベストプラクティス

- 環境変数（特にトークンやパスワード）は安全に管理してください。.env はバージョン管理に含めないことを推奨します（.gitignore へ追加）。
- J-Quants のレート制限（120 req/min）に従ってください。モジュールは内部でスロットリングを行いますが、運用バッチでの並列呼び出しは注意が必要です。
- ETL は差分更新・バックフィル方式で設計されています。初回は全期間を取得するため時間がかかる可能性があります。
- DuckDB ファイルはバックアップやロールアップの考慮が必要です。DB ファイルのロックや並列アクセスに注意してください。
- ニュース収集では SSRF や XML 攻撃対策を実装していますが、外部 RSS が信頼できない場合はソースを精査してください。
- audit（監査ログ）はトランザクション保存や UTC タイムスタンプ保存を前提にしています。発注フローを実装する際は冪等キー（order_request_id）を正しく扱ってください。

---

## 補足 / 開発者向けメモ

- config._find_project_root は .git または pyproject.toml を探索してプロジェクトルートを特定し、自動で .env をロードします。テストや CI で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- research モジュール内の統計計算（rank, calc_ic, factor_summary）は外部依存を避けるため自前実装です。大規模データでの性能は要検証です。
- ニュースの ID は正規化URL の SHA-256（先頭32文字）で生成されます。UTM 等は除去して冪等性を向上させています。
- DuckDB のバージョン差異により一部機能（ON DELETE CASCADE など）が未サポートなため、コメントに代替操作の指示があります。

---

必要であれば README に以下を追記できます:
- より詳細なサンプルコード（ETL スケジューリング・Slack 通知連携・実際の発注連携例）
- CI / テストの手順
- 開発環境の Dockerfile / Compose 例

その他、追加したい情報があれば教えてください。README を拡張して具体的な使用シナリオや運用ガイドを追記します。