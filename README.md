# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
データ収集（J-Quants）、DuckDBベースのスキーマ、ETLパイプライン、ニュース収集、ファクター計算（リサーチ用）、および発注・監査向けのスキーマを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダー取得と保存（冪等）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄抽出
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と IC / 統計サマリー
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境設定管理（.env 自動読み込み、必須環境変数の検証）

設計上、データ取得 / 保存処理は冪等であり（ON CONFLICT）、本番発注 API への直接呼び出しを行わないモジュール（data / research）と、発注・監視向けのスキーマ／雛形を用意するモジュール（execution / monitoring / audit）に分離されています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得とバリデーション
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み停止

- データ取得・保存（J-Quants）
  - レート制限（120 req/min）の遵守
  - リトライ（指数バックオフ）、401 の自動トークンリフレッシュ
  - 日足、財務、マーケットカレンダーのページネーション対応取得
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar など）

- ETL / パイプライン
  - 差分更新（最終取得日ベース）・バックフィル
  - カレンダー先読み
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- スキーマ管理（DuckDB）
  - Raw/Processed/Feature/Execution/Audit 各レイヤーのテーブル定義およびインデックス作成
  - init_schema / init_audit_schema 等の初期化関数

- ニュース収集
  - RSS フィード取得（SSRF対策、受信サイズ制限、gzip対応）
  - トラッキングパラメータ除去した URL 正規化、SHA-256 ベースの記事 ID 生成
  - raw_news / news_symbols への冪等保存
  - 銘柄コード抽出（4桁数字と既知コードセットの照合）

- リサーチ / 特徴量
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（クロスセクション正規化）

- 監査ログ
  - signal_events / order_requests / executions テーブルで戦略から約定までをトレース可能に保存
  - UTC タイムゾーン固定等のポリシーを反映

---

## セットアップ手順

前提: Python 3.10 以上を推奨（typing の union 型表記などを使用）。

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージをインストール（例）
   KabuSys の主要機能は以下のパッケージに依存します。プロジェクトに requirements.txt があればそちらを利用してください。最小限の例は:
   ```bash
   pip install duckdb defusedxml
   ```
   （HTTP クライアントは標準ライブラリ urllib を使用。追加ログ送信や Slack 連携等を行う場合は slack-sdk 等が必要になるかもしれません）

4. 環境変数の設定
   プロジェクトルートの `.env` または `.env.local` に次の必須値を設定してください（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_station_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   ```
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development/paper_trading/live、デフォルト: development）
   - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

   自動読み込みを無効化するには:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトでスキーマを初期化します:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   監査ログ用スキーマを別データベースで作る場合:
   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主な例）

- 環境設定値を参照する
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```

- 日次 ETL を実行する（DuckDB 接続を渡す）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ETL の個別ジョブを呼ぶ
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(res)
  ```

- リサーチ（ファクター計算）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2024, 1, 31)
  mom = calc_momentum(conn, t)
  vol = calc_volatility(conn, t)
  val = calc_value(conn, t)
  fwd = calc_forward_returns(conn, t)
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- J-Quants から日足取得（直接利用したい場合）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意: 上記の関数群は DuckDB の該当テーブル（prices_daily / raw_financials 等）が存在し、適切なデータが入っていることを前提とします。初期化は schema.init_schema を利用してください。

---

## 重要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注等で利用）
- SLACK_BOT_TOKEN: Slack 通知用トークン（モジュール内で利用する場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- DUCKDB_PATH: DuckDB 保存先（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（値が設定されると自動ロードをしない）

---

## ディレクトリ構成

主要ファイル・モジュールのツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - news_collector.py      -- RSS ニュース収集
    - schema.py              -- DuckDB スキーマ定義・初期化
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - features.py            -- 特徴量公開インターフェース
    - calendar_management.py -- マーケットカレンダー管理
    - audit.py               -- 監査ログ（signal/order/execution）
    - etl.py                 -- ETL ユーティリティの公開
    - quality.py             -- データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py -- forward_return / IC / summary 等
    - factor_research.py     -- momentum / volatility / value の計算
  - strategy/
    - __init__.py            -- 戦略層用モジュール（拡張想定）
  - execution/
    - __init__.py            -- 発注層用モジュール（雛形）
  - monitoring/
    - __init__.py            -- 監視・アラート（雛形）

このリポジトリはモジュール単位で拡張しやすい構成になっています。例えば strategy/ と execution/ は具体的な売買ロジックやブローカー接続を実装する箇所です。

---

## 動作上の注意事項・設計上のポイント

- J-Quants API はレート制限（120 req/min）とページネーションがあるため、jquants_client は固定間隔スロットリングとリトライを実装しています。
- 各保存処理は冪等（ON CONFLICT）により再実行しても重複しない設計です。
- ニュース収集は SSRF や XML Bomb 等の脅威への対策を施しており、受信サイズ上限や defusedxml を利用しています。
- DuckDB スキーマの初期化関数は親ディレクトリの作成まで行います。
- run_daily_etl は品質チェックを含みますが、チェックで重大な問題が見つかってもパイプラインの他部分は継続実行する設計です（呼び出し元での判断を想定）。
- 本リポジトリは本番発注（ブローカーへの送信）ロジックを直接行う実装を含まないモジュール群と、発注／監査のスキーマを提供するモジュールで構成されています。実際のブローカー接続は execution 層で実装してください。

---

## 参考 / トラブルシューティング

- 環境変数が不足している場合、config.Settings のプロパティアクセスで ValueError が投げられます。README の必須変数を確認してください。
- DuckDB 関連のエラーは schema.init_schema の実行権限やファイルパス（親ディレクトリの有無）を確認してください。init_schema は親ディレクトリを自動作成しますが、アクセス権の問題があると失敗します。
- RSS 取得時に接続が遮断される場合は、fetch_rss のログ（SSRF/サイズ/パースエラー）を参照してください。

---

以上が README の概要です。必要であれば、セットアップの自動化スクリプト（requirements.txt / Makefile / poetry 設定例）やサンプルの .env.example を追加するドキュメントも作成できます。どの部分を拡張したいか教えてください。