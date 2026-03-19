# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants 等の市場データを取得して DuckDB に格納し、データ品質チェック・特徴量計算・戦略研究・発注監査などの機能を提供します。パッケージはモジュール化されており、ETL パイプラインやニュース収集、リサーチ用ユーティリティを個別に利用できます。

---

## 主要な特徴（機能一覧）

- データ取得・保存
  - J-Quants API クライアント（ページネーション対応、トークン自動リフレッシュ、リトライ／レート制御）
  - 株価日足・財務データ・市場カレンダーの取得と DuckDB への冪等保存

- ETL / Data pipeline
  - 差分更新（最終取得日に基づく差分取得）・バックフィル対応
  - 日次 ETL エントリポイント（run_daily_etl）でカレンダー・価格・財務を一括処理

- スキーマ管理
  - DuckDB 用スキーマ定義と初期化（raw / processed / feature / execution / audit 層）
  - 監査ログ（signal → order_request → execution のトレース性確保）

- データ品質チェック
  - 欠損データ、スパイク（急変）、重複、日付不整合の検出
  - QualityIssue 型で問題を集約

- ニュース収集
  - RSS フィードからの記事収集、URL 正規化、SSRF 対策、gzip 制限、記事の冪等保存
  - 記事 → 銘柄コードの紐付け支援（テキストから 4 桁銘柄抽出）

- リサーチ（研究）ユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Spearman ランク相関）、ファクター統計サマリ
  - Z スコア正規化ユーティリティ再エクスポート

- その他
  - 環境変数ベースの設定管理（.env 自動読込、テスト用に無効化可能）
  - ログレベル・実行環境（development / paper_trading / live）判定

---

## 必要条件 / 依存ライブラリ

- Python 3.10+
  - （コード上での型注釈や union 型 (A | B) を利用しているため）
- 主な依存パッケージ（例）
  - duckdb
  - defusedxml

実際のプロジェクトで使う場合は pyproject.toml / requirements.txt を参照してください。

---

## 環境変数（主な設定項目）

以下はコード中で参照される主要な環境変数です（.env に設定して利用します）。

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境（development | paper_trading | live、デフォルト development）
- LOG_LEVEL             : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化

注意: パッケージはプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（CWD ではなく __file__ を基準にルートを検出）。自動ロードを無効にしたいときは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. 仮想環境作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements ファイルや pyproject があればそちらを利用）
   ```bash
   pip install duckdb defusedxml
   # さらにパッケージをインストールする場合:
   # pip install -e .
   ```

3. `.env` を作成して必要な環境変数を設定
   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` を置けば自動読込されます。

4. DuckDB スキーマ初期化（Python REPL またはスクリプト）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   # or explicit path:
   # conn = init_schema("data/kabusys.duckdb")
   ```

5. 監査用 DB（オプション）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 基本的な使い方（コード例）

- 日次 ETL を実行（最も典型的な呼び出し）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)   # 初回は init_schema、既存なら get_connection を利用
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行（既存の known_codes に基づき銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は有効な銘柄コードセット（例: {'7203','6758',...}）
  results = run_news_collection(conn, known_codes={'7203','6758'})
  print(results)  # {source_name: saved_count, ...}
  ```

- リサーチ関数（特徴量・IC など）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  momentum = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  value = calc_value(conn, target)
  forward = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
  ```

- J-Quants API を直接使う（例: 日足取得）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 主要 API の説明（抜粋）

- kabusys.config.settings
  - 環境変数から各種設定を取得する singleton。必須フィールドは _require() で ValueError を投げる。

- kabusys.data.schema.init_schema(db_path)
  - DuckDB のファイルを作成し、全テーブル・インデックスを作成して接続を返す（冪等）。

- kabusys.data.pipeline.run_daily_etl(...)
  - カレンダー取得 → 株価取得 → 財務取得 → 品質チェックの順で日次 ETL を実行。ETLResult を返す。

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存を行う（ON CONFLICT ... DO UPDATE）

- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection
  - SSRF 対策、gzip サイズ制限、URL 正規化、記事 ID は正規化 URL の SHA-256（先頭 32 文字）

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize を再エクスポート

- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - QualityIssue 型で問題を返す

---

## ディレクトリ構成（抜粋）

（パッケージルートが `src/` 配下にある構成）

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
      - features.py
      - etl.py
      - calendar_management.py
      - quality.py
      - audit.py
      - audit.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

---

## 実行環境に関する注意事項

- Python のバージョンは 3.10 以上を想定しています（型アノテーションで | を使用）。
- J-Quants API はレート制限があり（120 req/min）ライブラリ内で固定間隔スロットリングを実装しています。大量取得時は注意してください。
- DuckDB の SQL 実行により NULL や型不整合でエラーが出ることがあります。ETL・スキーマの初期化はログを確認して実行してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を基準に行われます。テストなどで無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 開発・貢献

- コードはモジュール化され、ユニットテストや CI を追加しやすい設計です。関数単位で DuckDB 接続や id_token を注入できるようになっており、モックやユニットテストが実行しやすくなっています。
- 不具合報告や機能追加提案の際は、対象機能の呼び出し例（最小再現コード）と期待値／実際の挙動を添えてください。

---

README の内容はコードベースに基づく概要・使い方の要約です。より詳しい設計仕様（DataPlatform.md / StrategyModel.md 等）や運用手順がある場合は併せて参照してください。必要であれば実行例や追加のセクション（CI、テスト、デプロイ手順等）を追記します。